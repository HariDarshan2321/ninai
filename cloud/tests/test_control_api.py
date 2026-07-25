from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path

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


class ControlAppTest(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.identity = ControlIdentity("user-1", "workspace-1")
        self.app = ControlApp(self.service, lambda env: self.identity)

    def request(self, path, method="GET", body=None, query=""):
        raw = json.dumps(body).encode() if body is not None else b""
        captured = {}
        env = {"PATH_INFO": path, "REQUEST_METHOD": method, "QUERY_STRING": query,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        result = b"".join(self.app(env, lambda status, headers: captured.update(status=status, headers=headers)))
        return captured["status"], captured["headers"], result

    def test_control_page_is_dependency_free_and_does_not_cache(self):
        status, headers, body = self.request("/control")
        self.assertEqual(status, "200 OK")
        self.assertIn(b"Ninai Control Center", body)
        self.assertIn(("Cache-Control", "no-store"), headers)

    def test_overview_uses_resolved_identity(self):
        status, _, body = self.request("/api/control/overview")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["workspace"]["id"], "workspace-1")
        self.assertEqual(self.service.calls[-1], ("overview", self.identity))

    def test_proposal_review_routes(self):
        status, _, body = self.request("/api/control/memories/m1/approve", "POST", {})
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["status"], "active")
        self.assertEqual(self.service.calls[-1], ("review", self.identity, "m1", True))

    def test_memory_filters_are_bounded_by_service(self):
        status, _, _ = self.request("/api/control/memories", query="status=proposed&limit=25")
        self.assertEqual(status, "200 OK")
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
                status, _, body = self.request(path, "POST", data)
                self.assertEqual(status, "200 OK")
                self.assertEqual(json.loads(body)[field], expected)
        status, _, body = self.request("/api/control/export")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["format"], "ninai-export-v1")
        status, _, body = self.request("/api/control/connections/c1/grants")
        self.assertEqual(status, "200 OK")
        self.assertEqual(json.loads(body)["items"][0]["id"], "g1")

    def test_unknown_route_is_json_404(self):
        status, _, body = self.request("/api/control/nope")
        self.assertEqual(status, "404 Not Found")
        self.assertIn("Route not found", json.loads(body)["error"])


if __name__ == "__main__":
    unittest.main()
