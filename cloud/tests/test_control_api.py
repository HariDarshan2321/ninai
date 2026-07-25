from __future__ import annotations

import sys
import hashlib
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings as MCPAuthSettings
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.control_api import ControlApp, ControlIdentity, ControlService


class RecordingDB:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        self.sql = sql
        self.params = params
        return self

    def fetchone(self):
        if "SELECT w.id" in self.sql:
            return {"id": "workspace-1", "name": "Acme", "slug": "acme", "role": "owner"}
        if "RETURNING id,provider" in self.sql:
            return {"id": self.params[0], "provider": self.params[3], "client_type": self.params[4],
                    "display_name": self.params[5], "status": "active"}
        return None


@contextmanager
def recording_connection(db):
    yield db


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def overview(self, who):
        self.calls.append(("overview", who))
        return {"workspace": {"id": who.workspace_id}, "counts": {"active_memories": 1}}

    def memories(self, who, status, limit):
        self.calls.append(("memories", who, status, limit)); return [{"id": "m1", "status": status}]

    def connections(self, who): return []
    def projects(self, who): return [{"id": "p1", "name": "Shared"}]
    def create_workspace(self, who, data):
        self.calls.append(("create_workspace", who, data)); return {"id": "new-workspace", "name": data["name"]}
    def create_project(self, who, data):
        self.calls.append(("create_project", who, data)); return {"id": "p1", "name": data["name"]}
    def create_connection(self, who, data):
        self.calls.append(("create_connection", who, data)); return {"id": "c2", **data, "setup": {"auth_mode": "oauth"}}
    def test_connection(self, who, connection_id):
        self.calls.append(("test_connection", who, connection_id)); return {"id": connection_id, "metadata_json": {"connection_test": {"status": "ready"}}}
    def grants(self, who, connection_id): return [{"id": "g1", "client_connection_id": connection_id}]
    def activity(self, who, limit): return []
    def export(self, who): return {"format": "ninai-export-v1"}
    def review(self, who, memory_id, approve):
        self.calls.append(("review", who, memory_id, approve)); return {"id": memory_id, "status": "active" if approve else "deleted"}
    def create_grant(self, who, connection_id, data): return {"id": "g1", **data}
    def revoke_connection(self, who, connection_id): return connection_id == "c1"
    def revoke_grant(self, who, grant_id): return grant_id == "g1"
    def delete_workspace(self, who, confirmation): return confirmation == "acme"


class Verifier(TokenVerifier):
    async def verify_token(self, token):
        if token != "valid-token":
            return None
        return AccessToken(token=token, client_id="client-1", scopes=[],
                           claims={"user_id": "user-1", "workspace_id": "workspace-1",
                                   "email": "owner@example.test", "name": "Owner"})


class ControlAppTest(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.identity = ControlIdentity("user-1", "workspace-1", "owner@example.test", "Owner")
        endpoint = ControlApp(self.service, Verifier()).handle
        self.client = TestClient(Starlette(routes=[
            Route("/control", endpoint, methods=["GET"]),
            Route("/control/login", endpoint, methods=["GET"]),
            Route("/control/logout", endpoint, methods=["GET"]),
            Route("/api/control/{path:path}", endpoint, methods=["GET", "POST"]),
        ]))
        self.auth = {"Authorization": "Bearer valid-token"}

    def test_control_page_is_dependency_free_and_does_not_cache(self):
        response = self.client.get("/control")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ninai Control Center", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("sessionStorage", response.text)
        for label in ("Memories", "Permissions", "Download workspace export", "Delete workspace"):
            self.assertIn(label, response.text)

    def test_control_and_error_responses_have_security_headers(self):
        for response in (
            self.client.get("/control"),
            self.client.get("/api/control/overview"),
            self.client.get("/api/control/nope", headers=self.auth),
        ):
            with self.subTest(status=response.status_code):
                self.assertEqual(response.headers["x-content-type-options"], "nosniff")
                self.assertEqual(response.headers["x-frame-options"], "DENY")
                self.assertEqual(response.headers["referrer-policy"], "no-referrer")
                self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
                self.assertIn("camera=()", response.headers["permissions-policy"])

    def test_api_requires_verified_bearer_token(self):
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/control/overview", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertTrue(response.headers["www-authenticate"].startswith("Bearer"))

    def test_dashboard_oauth_login_uses_authorization_code_pkce(self):
        from ninai_cloud.auth import AuthSettings
        settings = AuthSettings(
            issuer="https://tenant.auth0.com/", audience="https://api.example/mcp",
            resource="https://api.example/mcp", jwks_uri="https://tenant.auth0.com/jwks",
            authorization_endpoint="https://tenant.auth0.com/authorize",
            token_endpoint="https://tenant.auth0.com/oauth/token",
            control_client_id="dashboard-client", control_base_url="https://api.example",
        )
        endpoint = ControlApp(self.service, Verifier(), settings).handle
        client = TestClient(Starlette(routes=[
            Route("/control", endpoint, methods=["GET"]),
            Route("/control/login", endpoint, methods=["GET"]),
        ]))
        self.assertIn("const oauthEnabled=true", client.get("/control").text)
        response = client.get("/control/login?screen_hint=signup", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        location = response.headers["location"]
        for expected in ("response_type=code", "code_challenge=", "code_challenge_method=S256",
                         "client_id=dashboard-client", "screen_hint=signup",
                         "redirect_uri=https%3A%2F%2Fapi.example%2Fcontrol"):
            self.assertIn(expected, location)
        self.assertIn("ninai_oauth_state=", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])

    def test_dashboard_oauth_callback_rejects_bad_state(self):
        from ninai_cloud.auth import AuthSettings
        settings = AuthSettings(
            issuer="https://tenant.auth0.com/", audience="https://api.example/mcp",
            resource="https://api.example/mcp", jwks_uri="https://tenant.auth0.com/jwks",
            authorization_endpoint="https://tenant.auth0.com/authorize",
            token_endpoint="https://tenant.auth0.com/oauth/token",
            control_client_id="dashboard-client", control_base_url="https://api.example",
        )
        endpoint = ControlApp(self.service, Verifier(), settings).handle
        client = TestClient(Starlette(routes=[Route("/control", endpoint, methods=["GET"])]))
        client.cookies.set("ninai_oauth_state", "expected")
        response = client.get("/control?code=authorization-code&state=wrong")
        self.assertEqual(response.status_code, 400)
        self.assertIn("state validation", response.json()["error"])

    def test_dashboard_oauth_callback_sets_httponly_session_cookie(self):
        from ninai_cloud.auth import AuthSettings
        settings = AuthSettings(
            issuer="https://tenant.auth0.com/", audience="https://api.example/mcp",
            resource="https://api.example/mcp", jwks_uri="https://tenant.auth0.com/jwks",
            authorization_endpoint="https://tenant.auth0.com/authorize",
            token_endpoint="https://tenant.auth0.com/oauth/token",
            control_client_id="dashboard-client", control_base_url="https://api.example",
        )
        endpoint = ControlApp(self.service, Verifier(), settings).handle
        client = TestClient(Starlette(routes=[Route("/control", endpoint, methods=["GET"])]))

        class TokenResponse:
            def raise_for_status(self): pass
            def json(self): return {"access_token": "valid-token", "expires_in": 900}
        class AsyncClient:
            def __init__(self, **_kwargs): self.data = None
            async def __aenter__(self): return self
            async def __aexit__(self, *_args): pass
            async def post(self, _url, data): self.data = data; return TokenResponse()

        client.cookies.set("ninai_oauth_state", "expected")
        client.cookies.set("ninai_pkce_verifier", "verifier")
        with patch("httpx.AsyncClient", AsyncClient):
            response = client.get("/control?code=authorization-code&state=expected",
                                  follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/control")
        cookies = response.headers.get_list("set-cookie")
        session = next(value for value in cookies if value.startswith("ninai_access_token="))
        self.assertIn("HttpOnly", session)
        self.assertIn("Secure", session)
        self.assertIn("SameSite=lax", session)

    def test_dashboard_cookie_auth_requires_origin_for_mutations(self):
        client = self.client
        client.cookies.set("ninai_access_token", "valid-token")
        self.assertEqual(client.get("/api/control/overview").status_code, 200)
        denied = client.post("/api/control/memories/m1/approve", json={})
        self.assertEqual(denied.status_code, 401)
        allowed = client.post("/api/control/memories/m1/approve", json={},
                              headers={"Origin": "http://testserver"})
        self.assertEqual(allowed.status_code, 200)

    def test_overview_uses_only_token_identity(self):
        response = self.client.get(
            "/api/control/overview?workspace_id=attacker",
            headers={**self.auth, "X-Workspace-Id": "attacker", "X-User-Id": "attacker"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workspace"]["id"], "workspace-1")
        self.assertEqual(self.service.calls[-1], ("overview", self.identity))

    def test_proposal_review_routes(self):
        response = self.client.post("/api/control/memories/m1/approve", json={}, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "active")
        self.assertEqual(self.service.calls[-1], ("review", self.identity, "m1", True))

    def test_memory_filters_are_bounded_by_service(self):
        response = self.client.get("/api/control/memories?status=proposed&limit=25", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.calls[-1], ("memories", self.identity, "proposed", "25"))

    def test_connection_grants_revocation_export_and_delete(self):
        cases = [
            ("/api/control/connections/c1/grants", {"scope_kind": "project", "scope_id": "p1"}, "id", "g1"),
            ("/api/control/connections/c1/revoke", {}, "revoked", True),
            ("/api/control/grants/g1/revoke", {}, "revoked", True),
            ("/api/control/delete-workspace", {"confirmation": "acme", "workspace_id": "attacker"}, "deleted", True),
        ]
        for path, data, field, expected in cases:
            with self.subTest(path=path):
                response = self.client.post(path, json=data, headers=self.auth)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()[field], expected)
        self.assertEqual(self.client.get("/api/control/export", headers=self.auth).json()["format"], "ninai-export-v1")
        self.assertEqual(self.client.get("/api/control/connections/c1/grants", headers=self.auth).json()["items"][0]["id"], "g1")

    def test_provisioning_routes_derive_identity_from_token_not_body(self):
        cases = [
            ("/api/control/workspaces", {"name": "Acme", "user_id": "attacker"}, "create_workspace"),
            ("/api/control/projects", {"name": "Shared", "workspace_id": "attacker"}, "create_project"),
            ("/api/control/connections", {"provider": "openai", "client_type": "codex",
             "display_name": "Codex", "workspace_id": "attacker", "user_id": "attacker"}, "create_connection"),
        ]
        for path, body, call_name in cases:
            with self.subTest(path=path):
                response = self.client.post(path, json=body, headers=self.auth)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.service.calls[-1][0], call_name)
                self.assertEqual(self.service.calls[-1][1], self.identity)
        response = self.client.post("/api/control/connections/c2/test",
                                    json={"workspace_id": "attacker"}, headers=self.auth)
        self.assertEqual(response.json()["metadata_json"]["connection_test"]["status"], "ready")
        self.assertEqual(self.service.calls[-1], ("test_connection", self.identity, "c2"))
        self.assertEqual(self.client.get("/api/control/projects", headers=self.auth).json()["items"][0]["id"], "p1")

    def test_unknown_route_is_json_404(self):
        response = self.client.get("/api/control/nope", headers=self.auth)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Route not found", response.json()["error"])

    def test_connection_pat_is_returned_once_only_in_explicit_self_hosted_mode(self):
        who = self.identity
        body = {"provider": "openai", "client_type": "codex", "display_name": "Codex",
                "oauth_client_id": "tpc_codex"}
        hosted_db = RecordingDB()
        hosted = ControlService(lambda: recording_connection(hosted_db), self_hosted=False,
                                oauth_issuer="https://tenant.auth0.com/")
        self.assertNotIn("personal_access_token", hosted.create_connection(who, body))
        self.assertFalse(any("personal_access_tokens" in sql for sql, _ in hosted_db.calls))

        self_hosted_db = RecordingDB()
        self_hosted = ControlService(lambda: recording_connection(self_hosted_db), self_hosted=True)
        result = self_hosted.create_connection(who, body)
        token = result["personal_access_token"]
        self.assertTrue(token.startswith("ninai_pat_"))
        token_insert = next(params for sql, params in self_hosted_db.calls
                            if "INSERT INTO personal_access_tokens" in sql)
        self.assertEqual(token_insert[4], hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, token_insert)

    def test_grants_require_an_explicit_coherent_permission(self):
        service = ControlService(lambda: recording_connection(RecordingDB()))
        with self.assertRaisesRegex(ValueError, "At least one permission"):
            service.create_grant(self.identity, "c1", {"scope_kind": "project", "scope_id": "p1"})
        with self.assertRaisesRegex(ValueError, "requires can_propose"):
            service.create_grant(self.identity, "c1", {"scope_kind": "project", "scope_id": "p1",
                                                        "can_auto_activate": True})

    def test_health_control_and_api_are_mounted_on_hosted_service(self):
        from ninai_cloud.mcp_server import create_mcp

        server = create_mcp(
            object(), token_verifier=Verifier(), control_service=self.service,
            auth=MCPAuthSettings(issuer_url="https://auth.example.test",
                                 resource_server_url="https://api.example.test/mcp",
                                 required_scopes=[]),
            principal_resolver=lambda: None,
        )
        paths = {route.path for route in server.streamable_http_app().routes}
        self.assertTrue({"/health", "/control", "/control/login", "/control/logout",
                         "/api/control/{path:path}"}.issubset(paths))
        with TestClient(server.streamable_http_app()) as client:
            self.assertEqual(client.get("/health").json()["status"], "ok")
            self.assertIn("Ninai Control Center", client.get("/control").text)
            response = client.get("/api/control/overview", headers=self.auth)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["workspace"]["id"], "workspace-1")


if __name__ == "__main__":
    unittest.main()
