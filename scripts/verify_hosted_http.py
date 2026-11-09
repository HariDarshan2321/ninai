#!/usr/bin/env python3
"""Synthetic localhost-only hosted MCP acceptance; no vendor model invocation."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud" / "src"))

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from ninai_cloud.bootstrap import bootstrap
from ninai_cloud.postgres_store import PostgresStore


def unauthorized(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 401
    return any(unauthorized(child) for child in getattr(error, "exceptions", ()))


async def run(database_url: str, endpoint: str) -> dict:
    if urlsplit(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This synthetic verifier only permits a localhost MCP endpoint")
    if urlsplit(database_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This synthetic verifier only permits a localhost test database")
    fixture = bootstrap(database_url, email=f"http-{uuid.uuid4().hex}@ninai.invalid",
                        workspace_name="HTTP acceptance", project_name="Synthetic")
    checks = {}

    async def call(client: str, tool: str, arguments: dict):
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + fixture["tokens"][client]}) as http_client, streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                if result.isError:
                    raise AssertionError(f"{tool} returned a tool error")
                return result.structuredContent or json.loads(result.content[0].text)

    try:
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + fixture["tokens"]["claude"]}) as http_client, streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                checks["initialize_and_list_tools"] = {"remember", "search", "recall"} <= {tool.name for tool in tools.tools}
        marker = "Synthetic HTTP launch colour is amber"
        saved = await call("claude", "remember", {
            "content": marker, "memory_type": "decision", "scope_kind": "project",
            "scope_id": fixture["project"], "project_id": fixture["project"],
            "source_uri": "test://localhost/http-acceptance", "idempotency_key": uuid.uuid4().hex,
        })
        checks["write_succeeded"] = saved.get("ok", False)
        recalled = await call("codex", "recall", {"query": "HTTP launch colour amber", "purpose": "synthetic acceptance", "project_id": fixture["project"]})
        checks["peer_recall_with_source"] = marker in json.dumps(recalled) and "test://localhost/http-acceptance" in json.dumps(recalled)
        store = PostgresStore(database_url)
        checks["revoke_client"] = store.revoke_client(fixture["workspace"], fixture["codex_client"], fixture["user"])
        try:
            await call("codex", "search", {"query": "amber", "purpose": "revocation test"})
            checks["revoked_http_request_denied"] = False
        except Exception as error:
            if not unauthorized(error):
                raise
            checks["revoked_http_request_denied"] = True
        allowed = await call("claude", "search", {"query": "amber", "purpose": "peer continuity"})
        checks["other_client_continues"] = marker in json.dumps(allowed)
        return {"passed": all(checks.values()), "host_invocation": "not_run", "checks": checks}
    finally:
        import psycopg
        with psycopg.connect(database_url) as db:
            for table in ("disclosure_logs", "idempotency_keys", "memory_relations", "memory_sources", "memories", "personal_access_tokens", "client_scope_grants", "client_connections", "projects", "workspace_members"):
                db.execute(f"DELETE FROM {table} WHERE workspace_id=%s", (fixture["workspace"],))
            db.execute("DELETE FROM workspaces WHERE id=%s", (fixture["workspace"],))
            db.execute("DELETE FROM users WHERE id=%s", (fixture["user"],))


if __name__ == "__main__":
    report = asyncio.run(run(os.environ["NINAI_TEST_DATABASE_URL"], os.environ.get("NINAI_TEST_MCP_URL", "http://127.0.0.1:58039/mcp")))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
