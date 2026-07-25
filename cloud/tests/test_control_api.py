from __future__ import annotations

import sys
import unittest
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings as MCPAuthSettings
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.control_api import ControlApp, ControlIdentity


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def overview(self, who):
        self.calls.append(("overview", who))
        return {"workspace": {"id": who.workspace_id}, "counts": {"active_memories": 1}}

    def memories(self, who, status, limit):
        self.calls.append(("memories", who, status, limit)); return [{"id": "m1", "status": status}]

    def connections(self, who): return []
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
                           claims={"user_id": "user-1", "workspace_id": "workspace-1"})


class ControlAppTest(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.identity = ControlIdentity("user-1", "workspace-1")
        endpoint = ControlApp(self.service, Verifier()).handle
        self.client = TestClient(Starlette(routes=[
            Route("/control", endpoint, methods=["GET"]),
            Route("/api/control/{path:path}", endpoint, methods=["GET", "POST"]),
        ]))
        self.auth = {"Authorization": "Bearer valid-token"}

    def test_control_page_is_dependency_free_and_does_not_cache(self):
        response = self.client.get("/control")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ninai Control Center", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("sessionStorage", response.text)

    def test_api_requires_verified_bearer_token(self):
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            with self.subTest(headers=headers):
                response = self.client.get("/api/control/overview", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertTrue(response.headers["www-authenticate"].startswith("Bearer"))

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

    def test_unknown_route_is_json_404(self):
        response = self.client.get("/api/control/nope", headers=self.auth)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Route not found", response.json()["error"])

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
        self.assertTrue({"/health", "/control", "/api/control/{path:path}"}.issubset(paths))
        with TestClient(server.streamable_http_app()) as client:
            self.assertEqual(client.get("/health").json()["status"], "ok")
            self.assertIn("Ninai Control Center", client.get("/control").text)
            response = client.get("/api/control/overview", headers=self.auth)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["workspace"]["id"], "workspace-1")


if __name__ == "__main__":
    unittest.main()
