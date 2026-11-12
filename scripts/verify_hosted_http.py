#!/usr/bin/env python3
"""Synthetic localhost-only hosted MCP acceptance; no vendor model invocation."""
from __future__ import annotations

import asyncio
import argparse
import json
import os
import sys
import uuid
import time
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
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


def validate_targets(database_url: str, endpoint: str) -> None:
    local = {"localhost", "127.0.0.1", "::1"}
    target, database = urlsplit(endpoint), urlsplit(database_url)
    if target.hostname not in local or target.scheme not in {"http", "https"} or target.username or target.password:
        raise ValueError("This synthetic verifier only permits a localhost MCP endpoint")
    if database.hostname not in local or database.scheme not in {"postgresql", "postgres"}:
        raise ValueError("This synthetic verifier only permits a localhost test database")
    if any(key.lower() in {"host", "hostaddr", "service", "servicefile"} for key, _ in parse_qsl(database.query)):
        raise ValueError("Database query parameters must not override the localhost destination")


def bounded_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    values = dict(parse_qsl(parts.query))
    values["connect_timeout"] = "5"
    values["options"] = (values.get("options", "") + " -c statement_timeout=5000 -c lock_timeout=5000").strip()
    return urlunsplit(parts._replace(query=urlencode(values, quote_via=quote)))


async def finish_on_cancel(awaitable):
    """Settle an already-started DB operation before removing its fixture."""
    task = asyncio.create_task(awaitable)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


def cleanup_fixture(database_url: str, fixture: dict) -> bool:
    import psycopg
    with psycopg.connect(database_url) as db:
        for table in ("installer_downloads", "session_disclosure_logs", "session_artifacts", "sessions",
                      "workspace_capture_settings", "disclosure_logs", "memory_feedback", "idempotency_keys",
                      "memory_relations", "memory_sources", "memories", "personal_access_tokens",
                      "oauth_client_bindings", "client_scope_grants", "client_connections", "projects", "workspace_members"):
            db.execute(f"DELETE FROM {table} WHERE workspace_id=%s", (fixture["workspace"],))
        db.execute("DELETE FROM oauth_identities WHERE user_id=%s", (fixture["user"],))
        db.execute("DELETE FROM workspaces WHERE id=%s", (fixture["workspace"],))
        db.execute("DELETE FROM users WHERE id=%s", (fixture["user"],))
        return not db.execute("SELECT EXISTS(SELECT 1 FROM workspaces WHERE id=%s) OR EXISTS(SELECT 1 FROM users WHERE id=%s)", (fixture["workspace"], fixture["user"])).fetchone()[0]


async def run(database_url: str, endpoint: str) -> dict:
    validate_targets(database_url, endpoint)
    database_url = bounded_database_url(database_url)
    fixture = None
    checks = {}
    report = {"passed": False, "host_invocation": "not_run", "checks": checks, "cleanup_verified": False}

    async def create_fixture():
        nonlocal fixture
        fixture = await asyncio.to_thread(bootstrap, database_url, email=f"http-{uuid.uuid4().hex}@ninai.invalid",
                                          workspace_name="HTTP acceptance", project_name="Synthetic")

    async def call(client: str, tool: str, arguments: dict):
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + fixture["tokens"][client]}, timeout=httpx.Timeout(15, connect=5)) as http_client, streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments)
                if result.isError:
                    raise AssertionError(f"{tool} returned a tool error")
                return result.structuredContent or json.loads(result.content[0].text)

    try:
        await finish_on_cancel(create_fixture())
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + fixture["tokens"]["claude"]}, timeout=httpx.Timeout(15, connect=5)) as http_client, streamable_http_client(endpoint, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                checks["initialize_and_list_tools"] = {"remember", "search", "recall"} <= {tool.name for tool in tools.tools}
        marker = "Synthetic HTTP launch colour is amber for " + fixture["workspace"]
        source = "test://localhost/http-acceptance/" + fixture["workspace"]
        saved = await call("claude", "remember", {
            "content": marker, "memory_type": "decision", "scope_kind": "project",
            "scope_id": fixture["project"], "project_id": fixture["project"],
            "source_uri": source, "idempotency_key": uuid.uuid4().hex,
        })
        checks["write_succeeded"] = saved.get("ok", False)
        recalled = await call("codex", "recall", {"query": "HTTP launch colour amber", "purpose": "synthetic acceptance", "project_id": fixture["project"]})
        facts = recalled.get("facts", [])
        memory_id = saved.get("memory", {}).get("id")
        checks["peer_recall_with_source"] = bool(memory_id) and len(facts) == 1 and facts[0].get("id") == memory_id and facts[0].get("content") == marker and facts[0].get("source_uri") == source and facts[0].get("project_id") == fixture["project"]
        store = PostgresStore(database_url)
        checks["revoke_client"] = await finish_on_cancel(asyncio.to_thread(store.revoke_client, fixture["workspace"], fixture["codex_client"], fixture["user"]))
        try:
            await call("codex", "search", {"query": "amber", "purpose": "revocation test"})
            checks["revoked_http_request_denied"] = False
        except Exception as error:
            if not unauthorized(error):
                raise
            checks["revoked_http_request_denied"] = True
        allowed = await call("claude", "search", {"query": "amber", "purpose": "peer continuity"})
        results = allowed.get("results", [])
        checks["other_client_continues"] = len(results) == 1 and results[0].get("id") == memory_id and results[0].get("content") == marker and results[0].get("source_uri") == source
        report["passed"] = all(checks.values())
    finally:
        if fixture is not None:
            report["cleanup_verified"] = await finish_on_cancel(asyncio.to_thread(cleanup_fixture, database_url, fixture))
            if not report["cleanup_verified"]:
                raise AssertionError("Synthetic fixture cleanup failed")
    return report


async def run_many(database_url: str, endpoint: str, *, concurrency: int = 1, rounds: int = 1, timeout_seconds: float = 60) -> dict:
    validate_targets(database_url, endpoint)
    if not 1 <= concurrency <= 8 or not 1 <= rounds <= 3 or not 1 <= timeout_seconds <= 120:
        raise ValueError("Use concurrency 1..8, rounds 1..3 and timeout-seconds 1..120")
    started = time.monotonic()
    reports = []

    async def exercise():
        for _ in range(rounds):
            tasks = [asyncio.create_task(run(database_url, endpoint)) for _ in range(concurrency)]
            try:
                reports.extend(await asyncio.gather(*tasks))
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

    await asyncio.wait_for(exercise(), timeout=timeout_seconds)
    return {
        "passed": all(report["passed"] and report["cleanup_verified"] for report in reports),
        "host_invocation": "not_run", "boundary": "Synthetic localhost HTTP/SQL regression, not a production capacity benchmark",
        "concurrency": concurrency, "rounds": rounds, "completed_runs": len(reports),
        "checks_passed": sum(sum(report["checks"].values()) for report in reports),
        "fixtures_cleaned": sum(report["cleanup_verified"] for report in reports),
        "elapsed_seconds": round(time.monotonic() - started, 3), "runs": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=60, help="Overall async workload limit; in-flight DB cleanup is settled before exit")
    args = parser.parse_args()
    try:
        report = asyncio.run(run_many(os.environ["NINAI_TEST_DATABASE_URL"], os.environ.get("NINAI_TEST_MCP_URL", "http://127.0.0.1:58039/mcp"),
                                      concurrency=args.concurrency, rounds=args.rounds, timeout_seconds=args.timeout_seconds))
        if args.concurrency == args.rounds == 1:
            report = report["runs"][0]
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1
    except Exception as error:
        # Exception text can include connection details; never print it here.
        print(json.dumps({"passed": False, "error_type": type(error).__name__, "reason": "Localhost acceptance failed or timed out; no credentials are printed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
