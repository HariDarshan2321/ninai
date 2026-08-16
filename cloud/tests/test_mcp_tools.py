from __future__ import annotations
import sys
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ninai_cloud.mcp_server import (HostedMCPTools, MAX_RECALL_TOKENS,
                                    RateLimitError, SlidingWindowRateLimiter)
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


class ReadyStore(FakeStore):
    @contextmanager
    def _connection(self):
        class Database:
            def execute(self, statement):
                if statement != "SELECT 1":
                    raise AssertionError(statement)
                return self

            def fetchone(self):
                return (1,)

        yield Database()


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

    def test_read_and_write_rates_are_limited_per_client(self) -> None:
        now = [10.0]
        read = SlidingWindowRateLimiter(2, clock=lambda: now[0])
        write = SlidingWindowRateLimiter(1, clock=lambda: now[0])
        tools = HostedMCPTools(self.store, lambda: Principal("user", "workspace", "client"),
                               read_limiter=read, write_limiter=write)
        tools.search("one", "test")
        tools.fetch("missing", "test")
        with self.assertRaisesRegex(RateLimitError, "rate limit"):
            tools.search("three", "test")
        values = dict(content="bounded", memory_type="fact", scope_kind="project",
                      scope_id="project", source_uri="test://source", idempotency_key="one")
        tools.propose_memory(**values)
        with self.assertRaises(RateLimitError):
            tools.propose_memory(**{**values, "idempotency_key": "two"})
        now[0] += 61
        tools.search("new window", "test")
        tools.propose_memory(**{**values, "idempotency_key": "three"})

    def test_rate_limits_are_isolated_by_client(self) -> None:
        current = [Principal("user", "workspace", "client-a")]
        limiter = SlidingWindowRateLimiter(1)
        tools = HostedMCPTools(self.store, lambda: current[0], read_limiter=limiter)
        tools.search("one", "test")
        current[0] = Principal("user", "workspace", "client-b")
        tools.search("one", "test")

    def test_write_payload_fields_are_bounded_before_store_call(self) -> None:
        base = dict(content="bounded", memory_type="fact", scope_kind="project",
                    scope_id="project", source_uri="test://source", idempotency_key="one")
        for field, value in (("content", "x" * 4001), ("source_uri", "x" * 1001),
                             ("idempotency_key", "x" * 201), ("scope_id", "x" * 101)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.tools.propose_memory(**{**base, field: value})
        for field, value in (("importance", float("nan")), ("confidence", 1.01)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.tools.propose_memory(**{**base, field: value})
        self.assertEqual(self.store.creates, [])

    def test_server_registers_expected_tools_and_http_routes(self) -> None:
        import asyncio
        from ninai_cloud.mcp_server import create_mcp
        class Verifier:
            async def verify_token(self, token): return None
        auth = MCPAuthSettings(issuer_url="https://auth.example.test",
                               resource_server_url="https://api.example.test/mcp", required_scopes=[])
        server = create_mcp(self.store, token_verifier=Verifier(), auth=auth,
                            principal_resolver=lambda: Principal("user", "workspace", "client"),
                            max_request_body_bytes=128)
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools},
                         {"search", "fetch", "recall", "propose_memory", "remember",
                          "capture_session_start", "capture_session_checkpoint",
                          "capture_session_end", "session_context"})
        descriptions = {tool.name: tool.description for tool in tools}
        self.assertIn("before asking for clarification", descriptions["search"])
        self.assertIn("depends on known prior project work", descriptions["recall"])
        self.assertIn("After the current conversation establishes", descriptions["propose_memory"])
        paths = {route.path for route in server.streamable_http_app().routes}
        self.assertIn("/health", paths)
        self.assertIn("/ready", paths)
        self.assertIn("/mcp", paths)
        self.assertIn("/.well-known/oauth-protected-resource/mcp", paths)

        from starlette.testclient import TestClient
        with TestClient(server.streamable_http_app()) as client:
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")
            readiness = client.get("/ready")
            self.assertEqual(readiness.status_code, 503)
            self.assertEqual(readiness.json()["status"], "unavailable")
            self.assertNotIn("error", readiness.text.lower())
            unauthorized = client.post("/mcp", json={})
            self.assertEqual(unauthorized.status_code, 401)
            self.assertIn("resource_metadata=", unauthorized.headers["www-authenticate"])
            oversized = client.post("/mcp", content=b"x" * 129,
                                    headers={"content-type": "application/json"})
            self.assertEqual(oversized.status_code, 413)
            self.assertEqual(oversized.json()["error"]["code"], "payload_too_large")

    def test_readiness_checks_the_database(self) -> None:
        from starlette.testclient import TestClient
        from ninai_cloud.mcp_server import create_mcp

        class Verifier:
            async def verify_token(self, token): return None

        server = create_mcp(
            ReadyStore(),
            token_verifier=Verifier(),
            auth=MCPAuthSettings(
                issuer_url="https://auth.example.test",
                resource_server_url="https://api.example.test/mcp",
                required_scopes=[],
            ),
            principal_resolver=lambda: Principal("user", "workspace", "client"),
        )
        with TestClient(server.streamable_http_app()) as client:
            response = client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__": unittest.main()
