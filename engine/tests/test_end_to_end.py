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
                    captured = await self._call_json(
                        session,
                        "recall",
                        {
                            "query": "NIN-77 merged launch",
                            "purpose": "verify PostToolUse capture",
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
