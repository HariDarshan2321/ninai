from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ninai.store import MemoryStore


class RuntimeEndToEndTest(unittest.TestCase):
    def test_mcp_permissions_revocation_and_claude_hook(self) -> None:
        asyncio.run(self._run_scenario())

    async def _run_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            store = MemoryStore(data_dir / "ninai.sqlite3")
            store.grant("claude-code", "project")
            store.grant_action("claude-code", "project", "write")
            environment = os.environ.copy()
            environment["NINAI_CLIENT_ID"] = "claude-code"
            environment["NINAI_DATA_DIR"] = str(data_dir)
            environment["PATH"] = os.pathsep.join(
                [str(Path(sys.executable).parent), environment.get("PATH", "")]
            )

            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "ninai.server"],
                env=environment,
            )
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertTrue(
                        {"remember", "recall", "explain", "forget", "status"}
                        <= {tool.name for tool in tools.tools}
                    )

                    remembered = await self._call_json(
                        session,
                        "remember",
                        {
                            "content": "Finish the Ninai MCP release checklist before launch",
                            "memory_type": "commitment",
                            "scope": "project",
                            "source_uri": "linear://NIN-42",
                        },
                    )
                    self.assertTrue(remembered["stored"])

                    recalled = await self._call_json(
                        session,
                        "recall",
                        {
                            "query": "Ninai MCP release launch",
                            "purpose": "release planning",
                            "max_tokens": 300,
                        },
                    )
                    self.assertEqual(recalled["facts"][0]["source_uri"], "linear://NIN-42")
                    self.assertLessEqual(recalled["estimated_tokens"], 300)

                    store.revoke("claude-code", "project")
                    denied = await self._call_json(
                        session,
                        "recall",
                        {
                            "query": "Ninai MCP release launch",
                            "purpose": "verify revocation",
                        },
                    )
                    self.assertEqual(denied["scopes"], [])
                    self.assertEqual(denied["facts"], [])

                    self._run_claude_hook(environment)
                    store.grant("claude-code", "project")
                    hook_memory = store.get_by_source_uri("claude-hook://session-e2e/tool-e2e")
                    store.grant_project("claude-code", str(hook_memory["project_id"]))
                    captured = await self._call_json(
                        session,
                        "recall",
                        {
                            "query": "NIN-77 merged launch",
                            "purpose": "verify PostToolUse capture",
                            "project_id": hook_memory["project_id"],
                        },
                    )
                    hook_fact = next(
                        fact
                        for fact in captured["facts"]
                        if fact["source_uri"] == "claude-hook://session-e2e/tool-e2e"
                    )
                    self.assertIn("NIN-77", hook_fact["content"])

            logs = store.list_logs()
            self.assertEqual(len(logs), 3)
            self.assertEqual(logs[1]["memory_ids"], [])

    def test_mcp_project_isolation_and_separate_write_delete_grants(self) -> None:
        asyncio.run(self._run_project_scenario())

    async def _run_project_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            store = MemoryStore(data_dir / "ninai.sqlite3")
            first = store.ensure_project(name="First", binding_key="test:first", cwd_or_repo="/synthetic/first")
            second = store.ensure_project(name="Second", binding_key="test:second", cwd_or_repo="/synthetic/second")
            first_id, second_id = str(first["id"]), str(second["id"])
            private = store.remember("Synthetic second project launch decision", project_id=second_id)
            store.grant("claude-code", "project")
            environment = {**os.environ, "NINAI_CLIENT_ID": "claude-code", "NINAI_DATA_DIR": str(data_dir)}
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "ninai.server"], env=environment)
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    for project_id in (None, first_id, second_id):
                        args = {"query": "project launch decision", "purpose": "check broad grant isolation"}
                        if project_id is not None:
                            args["project_id"] = project_id
                        self.assertEqual((await self._call_json(session, "recall", args))["facts"], [])
                    self.assertEqual((await self._call_json(session, "list_projects", {}))["projects"], [])
                    arguments = {"content": "Synthetic first project launch decision", "project_id": first_id}
                    denied = await self._call_json(session, "remember", arguments)
                    self.assertFalse(denied["stored"])
                    store.grant_project("claude-code", first_id, "read")
                    accessible = (await self._call_json(session, "list_projects", {}))["projects"]
                    self.assertEqual(accessible, [{"id": first_id, "name": "First", "actions": ["read"]}])
                    self.assertFalse((await self._call_json(session, "remember", arguments))["stored"])
                    store.grant_project("claude-code", first_id, "write")
                    saved = await self._call_json(session, "remember", arguments)
                    self.assertTrue(saved["stored"])
                    recall_args = {"query": "project launch decision", "purpose": "verify project handoff", "project_id": first_id}
                    packet = await self._call_json(session, "recall", recall_args)
                    self.assertEqual([fact["id"] for fact in packet["facts"]], [saved["id"]])
                    self.assertEqual((await self._call_json(session, "explain", {"memory_id": private.id}))["error"], "Memory not found")
                    self.assertFalse((await self._call_json(session, "forget", {"memory_id": saved["id"]}))["forgotten"])
                    store.revoke_project("claude-code", first_id)
                    self.assertEqual((await self._call_json(session, "list_projects", {}))["projects"], [])
                    self.assertEqual((await self._call_json(session, "recall", recall_args))["facts"], [])

    async def _call_json(
        self,
        session: ClientSession,
        tool: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        result = await session.call_tool(tool, arguments)
        self.assertFalse(result.isError)
        self.assertEqual(len(result.content), 1)
        return json.loads(result.content[0].text)

    def _run_claude_hook(self, environment: dict[str, str]) -> None:
        hook = Path(__file__).resolve().parents[2] / ".claude/hooks/ninai_post_tool_use.py"
        event = {
            "cwd": environment["NINAI_DATA_DIR"],
            "session_id": "session-e2e",
            "tool_use_id": "tool-e2e",
            "tool_name": "mcp__github__merge_pull_request",
            "tool_input": {"pull_request": "NIN-77"},
            "tool_response": {"status": "merged", "milestone": "launch"},
        }
        completed = subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=10,
            env=environment,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
