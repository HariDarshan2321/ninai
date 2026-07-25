from __future__ import annotations
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ninai_cloud.mcp_server import HostedMCPTools, MAX_RECALL_TOKENS
from ninai_cloud.postgres_store import HostedMemory, Principal
from mcp.server.auth.settings import AuthSettings as MCPAuthSettings

NOW = datetime.now(timezone.utc)


def memory(number: int, content: str = "Nova uses PostgreSQL") -> HostedMemory:
    return HostedMemory(id=f"memory-{number}", workspace_id="workspace", project_id="project",
        memory_type="decision", scope_kind="project", scope_id="project", content=content,
        status="active", source_uri=f"claude://session/{number}", importance=0.8, confidence=1.0,
        created_at=NOW, updated_at=NOW)


class FakeStore:
    def __init__(self) -> None:
        self.memories = [memory(1)]
        self.disclosures: list[dict] = []
        self.creates: list[dict] = []
    def search(self, principal, query, *, limit=20): return self.memories[:limit]
    def get_memory(self, principal, memory_id): return next((x for x in self.memories if x.id == memory_id), None)
    def record_disclosure(self, principal, **event): self.disclosures.append(event); return "log"
    def create_memory(self, principal, **values): self.creates.append(values); return memory(len(self.creates), values["content"])


class HostedMCPToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = FakeStore()
        self.tools = HostedMCPTools(self.store, lambda: Principal("user", "workspace", "client"))
    def test_search_is_source_backed_and_disclosed(self) -> None:
        result = self.tools.search("PostgreSQL", "continue project work", limit=999)
        self.assertEqual(result["results"][0]["source"]["uri"], "claude://session/1")
        self.assertEqual(self.store.disclosures[0]["tool_name"], "search")
        self.assertEqual(self.store.disclosures[0]["returned_memory_ids"], ["memory-1"])
    def test_fetch_not_found_is_still_disclosed(self) -> None:
        self.assertFalse(self.tools.fetch("missing", "verify")["found"])
        self.assertEqual(self.store.disclosures[0]["returned_memory_ids"], [])
    def test_recall_respects_item_and_token_limits(self) -> None:
        self.store.memories = [memory(i, "x" * 260) for i in range(20)]
        result = self.tools.recall("x", "test bounds", max_items=999, max_tokens=99999)
        self.assertLessEqual(result["count"], 12)
        self.assertLessEqual(result["estimated_tokens"], MAX_RECALL_TOKENS)
        self.assertEqual(result["max_tokens"], MAX_RECALL_TOKENS)
    def test_write_modes_are_distinct_and_source_backed(self) -> None:
        values = dict(content="Nova uses PostgreSQL", memory_type="decision", scope_kind="project",
                      scope_id="project", source_uri="codex://session/1", idempotency_key="request-1")
        self.tools.propose_memory(**values)
        self.tools.remember(**{**values, "idempotency_key": "request-2"})
        self.assertFalse(self.store.creates[0]["activate"])
        self.assertTrue(self.store.creates[1]["activate"])
        self.assertEqual(self.store.creates[1]["source_uri"], "codex://session/1")
    def test_request_text_limits(self) -> None:
        with self.assertRaisesRegex(ValueError, "query must be at most"):
            self.tools.search("x" * 1001, "purpose")
        with self.assertRaisesRegex(ValueError, "purpose is required"):
            self.tools.recall("query", "   ")

    def test_server_registers_expected_tools_and_http_routes(self) -> None:
        import asyncio
        from ninai_cloud.mcp_server import create_mcp
        class Verifier:
            async def verify_token(self, token): return None
        auth = MCPAuthSettings(issuer_url="https://auth.example.test",
                               resource_server_url="https://api.example.test/mcp", required_scopes=[])
        server = create_mcp(self.store, token_verifier=Verifier(), auth=auth,
                            principal_resolver=lambda: Principal("user", "workspace", "client"))
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools},
                         {"search", "fetch", "recall", "propose_memory", "remember"})
        paths = {route.path for route in server.streamable_http_app().routes}
        self.assertIn("/health", paths)
        self.assertIn("/mcp", paths)
        self.assertIn("/.well-known/oauth-protected-resource/mcp", paths)

        from starlette.testclient import TestClient
        with TestClient(server.streamable_http_app()) as client:
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")
            unauthorized = client.post("/mcp", json={})
            self.assertEqual(unauthorized.status_code, 401)
            self.assertIn("resource_metadata=", unauthorized.headers["www-authenticate"])


if __name__ == "__main__": unittest.main()
