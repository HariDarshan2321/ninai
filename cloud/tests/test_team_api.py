from __future__ import annotations

import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from mcp.server.auth.provider import AccessToken
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from ninai_cloud.auth import AuthSettings
from ninai_cloud.control_api import SESSION_COOKIE
from ninai_cloud.postgres_store import AuthorizationError
from ninai_cloud.rate_limit import SlidingWindowRateLimiter
from ninai_cloud.team_api import TeamApp
from ninai_cloud.team_packet import TaskPacket


ORIGIN = "https://team.example.invalid"
ISSUER = "https://identity.example.invalid/"


class Verifier:
    def __init__(self, user):
        self.user = user

    async def verify_token(self, token):
        if token not in {"browser-token", "other-audience"}:
            return None
        return AccessToken(token=token, client_id="dashboard" if token == "browser-token" else "assistant",
                           scopes=[], subject="fixture|browser", claims={"user_id": self.user},
                           expires_at=int(time.time()) + 60)


class Store:
    def __init__(self):
        self.seen = []

    def context(self, workspace, project, actor, *, task):
        self.seen.append((workspace, project, actor, task))
        wire = b'{"outcome":"empty"}'
        return TaskPacket("empty", None if task == "tiny" else {"outcome": "empty"},
                          None if task == "tiny" else wire, (), ("budget-exhausted",) if task == "tiny" else ())

    def can_create_team(self, actor):
        return False

    def enable(self, workspace, actor):
        self.seen.append((workspace, actor))
        return {"workspace_id": workspace}

    def issue_binding(self, workspace, actor, *, project, client, actions):
        self.seen.append((workspace, project, actor, client, actions))
        return {"issued": True}

    def update_binding(self, workspace, actor, *, project, binding, operation):
        self.seen.append((workspace, project, actor, binding, operation))
        return {"updated": True}

    def export_project_audit(self, workspace, project, actor):
        self.seen.append((workspace, project, actor))
        return {"items": []}

    def group_edge(self, workspace, actor):
        raise AssertionError("unexpected group edge")


class TeamTransportTests(unittest.TestCase):
    def setUp(self):
        self.workspace, self.project, self.user = (str(uuid4()) for _ in range(3))
        self.store = Store()
        self.team = TeamApp(self.store, Verifier(self.user),
                            AuthSettings(ISSUER, "team", ORIGIN + "/mcp", ISSUER + "keys",
                                         control_client_id="dashboard"))
        self.client = TestClient(Starlette(routes=[
            Route("/control/team", self.team.page),
            Route("/api/team/{path:path}", self.team.handle, methods=["GET", "POST"]),
            Route("/api/team-assistant/{path:path}", self.team.handle, methods=["POST"]),
        ]), base_url=ORIGIN)
        self.addCleanup(self.client.close)
        self.assistant = f"/api/team-assistant/{self.workspace}/projects/{self.project}"
        self.human = f"/api/team/{self.workspace}"
        self.browser = {"Authorization": "Bearer browser-token"}

    def test_helper_installer_accepts_only_an_exact_render_revision(self):
        with patch.dict("os.environ", {"RENDER_GIT_COMMIT": "a" * 40}):
            page = self.client.get("/control/team", headers=self.browser)
        self.assertEqual(page.status_code, 200)
        self.assertIn(f'data-revision="{"a" * 40}"', page.text)
        self.assertIn("uv sync --locked --no-dev", page.text)

        with patch.dict("os.environ", {"RENDER_GIT_COMMIT": '\" onload=unexpected'}):
            page = self.client.get("/control/team")
        self.assertEqual(page.status_code, 401)
        self.assertIn('data-revision=""', page.text)
        self.assertNotIn("onload=unexpected", page.text)

    def test_assistant_packet_is_served_as_exact_bytes(self):
        answer = self.client.post(self.assistant + "/context", json={"task": "refund"},
                                  headers={"Authorization": "Bearer limited-team-credential"})
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.content, b'{"outcome":"empty"}')
        self.assertEqual(answer.headers["Cache-Control"], "no-store")
        tiny = self.client.post(self.assistant + "/context", json={"task": "tiny"}, headers=self.browser)
        self.assertEqual(tiny.status_code, 204)
        self.assertEqual(tiny.content, b"")
        self.assertEqual(tiny.headers["X-Ninai-Signals"], "budget-exhausted")

    def test_browser_binding_routes_take_project_from_path(self):
        route = f"{self.human}/projects/{self.project}"
        detail = {"client": "codex", "actions": ["read"]}
        issued = self.client.post(route + "/binding", json=detail, headers=self.browser)
        self.assertEqual(issued.json(), {"issued": True})
        self.assertEqual(self.store.seen[0][:2], (self.workspace, self.project))
        binding = str(uuid4())
        for action in ("rotate", "revoke"):
            updated = self.client.post(route + f"/{action}-binding", json={"binding": binding},
                                       headers=self.browser)
            self.assertEqual(updated.json(), {"updated": True})
            self.assertEqual(self.store.seen[-1][-2:], (binding, action))
        forged = self.client.post(route + "/binding", json={**detail, "project": str(uuid4())}, headers=self.browser)
        self.assertEqual(forged.status_code, 400)

    def test_dashboard_cookies_need_origin_and_explicit_identity(self):
        self.client.cookies.set(SESSION_COOKIE, "browser-token")
        self.assertEqual(self.client.post(self.human + "/enable", json={}).status_code, 403)
        self.assertEqual(self.client.post(self.human + "/enable", json={},
                                         headers={"Origin": "https://elsewhere.example.invalid"}).status_code, 403)
        ok = self.client.post(self.human + "/enable", json={}, headers={"Origin": ORIGIN})
        self.assertEqual(ok.json(), {"workspace_id": self.workspace})
        self.assertEqual(self.store.seen[0][1].user_id, self.user)
        self.assertEqual(self.client.get("/api/team/identity").json(),
                         {"user_id": self.user, "issuer": ISSUER, "subject": "fixture|browser",
                          "can_create_team": False})

    def test_audit_export_requires_the_dashboard_audience(self):
        route = f"{self.human}/projects/{self.project}/audit-export"
        self.assertEqual(self.client.post(self.assistant + "/audit-export", json={}, headers=self.browser).status_code,
                         404)
        self.assertEqual(self.client.post(route, json={},
                                         headers={"Authorization": "Bearer other-audience"}).status_code, 403)
        self.assertEqual(self.store.seen, [])
        result = self.client.post(route, json={}, headers=self.browser)
        self.assertEqual(result.json(), {"items": []})
        self.assertEqual(result.headers["Cache-Control"], "no-store")
        self.assertEqual(self.store.seen[0][:2], (self.workspace, self.project))

    def test_forged_identity_and_cross_audience_fail(self):
        self.assertEqual(self.client.post(self.human + "/enable", json={"user_id": self.user},
                                          headers=self.browser).status_code, 400)
        self.assertEqual(self.client.post(self.human + "/enable", json={},
                    headers={"Authorization": "Bearer other-audience"}).status_code, 403)
        self.assertEqual(self.client.post(self.assistant + "/approve", json={},
                                         headers=self.browser).status_code, 404)
        self.assertEqual(self.client.post(self.assistant + "/context",
                                          json={"task": "refund", "workspace": self.workspace},
                                          headers=self.browser).status_code, 400)
        self.assertEqual(self.store.seen, [])

    def test_assistant_quota_follows_credential_across_paths_and_resets(self):
        now = [10]
        self.team._assistant_reads = SlidingWindowRateLimiter(1, clock=lambda: now[0], maximum_keys=2)

        def denied(workspace, project, actor, *, task):
            self.store.seen.append(actor)
            if actor in {"revoked-fixture", "unknown-fixture"}:
                raise AuthorizationError("policy denied")
            return {"ok": True}

        self.store.context = denied

        def recall(credential, path=None):
            return self.client.post((path or self.assistant) + "/context", json={"task": "refund"},
                                    headers={"Authorization": f"Bearer {credential}"})

        wrong_route = f"/api/team-assistant/{uuid4()}/projects/{uuid4()}"
        revoked = recall("revoked-fixture")
        unknown = recall("unknown-fixture")
        self.assertEqual((revoked.status_code, revoked.content), (unknown.status_code, unknown.content))
        self.assertEqual(revoked.status_code, 403)
        limited = recall("revoked-fixture", wrong_route)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.headers["Retry-After"], "60")
        self.assertEqual(limited.headers["Cache-Control"], "no-store")
        self.assertEqual(recall("new-fixture").status_code, 429)
        self.assertEqual(self.store.seen, ["revoked-fixture", "unknown-fixture"])
        now[0] += 60
        self.assertEqual(recall("new-fixture").status_code, 200)

    def test_verified_human_read_and_access_changes_have_independent_limits(self):
        self.team._human_writes = SlidingWindowRateLimiter(1)
        self.store.change_member = lambda workspace, actor, *, user, role: {"updated": True}
        self.assertEqual(self.client.post(self.human + "/enable", json={}, headers=self.browser).status_code, 200)
        self.assertEqual(self.client.post(self.human + "/enable", json={}, headers=self.browser).status_code, 429)
        self.assertEqual(self.client.get("/api/team/identity", headers=self.browser).status_code, 200)
        response = self.client.post(self.human + "/member", json={"user": self.user, "role": "remove"},
                                    headers=self.browser)
        self.assertEqual(response.status_code, 200)

    def test_proof_capacity_leaves_access_changes_available(self):
        self.store.change_member = lambda workspace, actor, *, user, role: {"updated": True}
        with self.team._proof_slots, self.team._proof_slots, self.team._proof_slots, self.team._proof_slots:
            limited = self.client.post(self.assistant + "/context", json={"task": "refund"}, headers=self.browser)
            self.assertEqual(limited.status_code, 429)
            self.assertEqual(limited.headers["Retry-After"], "1")
            self.assertEqual(self.store.seen, [])
            response = self.client.post(self.human + "/member", json={"user": self.user, "role": "remove"},
                                        headers=self.browser)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(self.assistant + "/context", json={"task": "refund"},
                                          headers=self.browser).status_code, 200)

    def test_limited_peer_cannot_exhaust_global_budget_or_choose_forwarded_address(self):
        self.team._peers = SlidingWindowRateLimiter(1)
        self.team._ingress = SlidingWindowRateLimiter(2)
        first = self.client.get("/api/team/identity", headers=self.browser)
        self.assertEqual(first.status_code, 200)
        for forwarded in ("192.0.2.10", "192.0.2.20", "192.0.2.30"):
            limited = self.client.get("/api/team/identity", headers={**self.browser, "X-Forwarded-For": forwarded})
            self.assertEqual(limited.status_code, 429)
        with TestClient(self.client.app, base_url=ORIGIN, client=("192.0.2.100", 50000)) as separate_peer:
            self.assertEqual(separate_peer.get("/api/team/identity", headers=self.browser).status_code, 200)
