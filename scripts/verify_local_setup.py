#!/usr/bin/env python3
"""Exercise desktop setup and real local MCP transport in a disposable vault.

Run with the installed Ninai Python interpreter to check that installation.
No host login, model call, global editor configuration, or existing vault is used.
This does not verify an assistant application's tool consent or authentication.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ninai.desktop.api import DesktopApi
from ninai.store import MemoryStore


async def verify(directory: str) -> dict[str, object]:
    store = MemoryStore(Path(directory) / "ninai.sqlite3")
    api = DesktopApi(store)
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool) -> None:
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    def data(result):
        if not result["ok"]:
            raise AssertionError(result["error"])
        return result["data"]

    project = data(api.create_project("Disposable onboarding rehearsal"))["id"]
    other = data(api.create_project("Separate project"))["id"]
    memory = data(api.add_memory(
        "Keep database migrations reversible", memory_type="decision",
        source_uri="synthetic://setup/decision", project_id=project,
    ))
    require("new_project_access_off", not store.can_access_project("codex", project, "read"))
    before = len(store.list_logs())
    progress = data(api.setup_status(project, "codex"))
    require("progress_is_observational", progress["memory_saved"] and not progress["recall_verified"] and len(store.list_logs()) == before)

    async def recall(client: str, target: str):
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "ninai.server"],
            env={"NINAI_DATA_DIR": directory, "NINAI_CLIENT_ID": client},
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("recall", {
                    "query": "reversible migrations", "purpose": "disposable onboarding acceptance",
                    "project_id": target, "max_tokens": 300,
                })
                if result.isError:
                    raise AssertionError("recall returned a tool error")
                return json.loads(result.content[0].text)

    require("ungranted_read_denied", (await recall("codex", project))["facts"] == [])
    for client in ("codex", "claude-code"):
        data(api.set_project_permission(client, project, "read", True))
    require("read_does_not_grant_save_or_delete", not store.can_access_project("codex", project, "write") and not store.can_access_project("codex", project, "delete"))
    packet = await recall("codex", project)
    require("recall_returns_exact_memory_and_source", len(packet["facts"]) == 1 and packet["facts"][0]["id"] == memory["id"] and packet["facts"][0]["source_uri"] == "synthetic://setup/decision" and packet["estimated_tokens"] <= 300)
    require("real_recall_verified", data(api.setup_status(project, "codex"))["recall_verified"])
    require("other_client_not_falsely_verified", not data(api.setup_status(project, "claude-code"))["recall_verified"])
    data(api.set_project_permission("codex", project, "read", False))
    await recall("codex", other)
    require("unrelated_denial_does_not_verify_revocation", not data(api.setup_status(project, "codex"))["revocation_verified"])
    denied = await recall("codex", project)
    require("revocation_blocks_next_request", denied["facts"] == [] and denied["scopes"] == [])
    require("revocation_verified_from_real_denial", data(api.setup_status(project, "codex"))["revocation_verified"])
    require("other_client_keeps_access", len((await recall("claude-code", project))["facts"]) == 1)
    data(api.set_project_permission("codex", project, "read", True))
    require("regrant_clears_current_revocation_proof", not data(api.setup_status(project, "codex"))["revocation_verified"])
    return {"passed": True, "host_invocation": "not_run", "checks": checks}


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="ninai-setup-check-") as directory:
            report = asyncio.run(asyncio.wait_for(verify(directory), timeout=45))
        print(json.dumps(report, indent=2))
        return 0
    except (AssertionError, TimeoutError) as error:
        print(json.dumps({"passed": False, "reason": str(error) or "Setup check timed out"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
