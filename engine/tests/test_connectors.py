from __future__ import annotations

import json
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ninai.connectors import configuration, configure, config_path, installed, status
from ninai.store import MemoryStore


class EditorConnectorsTest(unittest.TestCase):
    def test_generated_editor_configs_start_real_mcp_with_live_permissions(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        executable = Path(sys.executable).with_name("ninai-mcp.exe" if os.name == "nt" else "ninai-mcp")
        if not executable.exists():
            self.skipTest("Install the engine entry points before transport integration tests")

        async def journey(client, directory):
            with patch.dict(os.environ, {"NINAI_DATA_DIR": directory}):
                config = configuration(client, str(executable))
            entry = config["servers" if client == "vscode" else "mcpServers"]["ninai-local"]
            store = MemoryStore(Path(directory) / "ninai.sqlite3")
            project = store.ensure_project(name="Synthetic client", binding_key="synthetic://client", cwd_or_repo=directory)
            params = StdioServerParameters(command=entry["command"], env=entry["env"])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertIn("recall", [tool.name for tool in tools.tools])
                    async def call(name, arguments):
                        result = await session.call_tool(name, arguments)
                        return json.loads(result.content[0].text)
                    arguments = {"content": "Use reversible migrations", "source_uri": "test://editor", "project_id": project["id"]}
                    self.assertFalse((await call("remember", arguments))["stored"])
                    store.grant_project(client, project["id"], "write")
                    store.grant_project(client, project["id"], "read")
                    saved = await call("remember", arguments)
                    self.assertTrue(saved["stored"])
                    query = {"query": "reversible migrations", "purpose": "connector transport test", "project_id": project["id"]}
                    recalled = await call("recall", query)
                    self.assertIn(saved["id"], [fact["id"] for fact in recalled["facts"]])
                    self.assertEqual(recalled["facts"][0]["source_uri"], "test://editor")
                    store.revoke_project(client, project["id"], "read")
                    self.assertEqual((await call("recall", query))["facts"], [])

        for client in ("cursor", "vscode"):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as directory:
                asyncio.run(journey(client, directory))

    def test_merge_idempotence_backup_and_owned_removal(self):
        for client, key in (("cursor", "mcpServers"), ("vscode", "servers")):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "mcp.json"
                original = json.dumps({key: {"other": {"command": "keep"}}, "inputs": [{"id": "keep"}]})
                path.write_text(original)
                path.chmod(0o600)
                with patch.dict(os.environ, {"NINAI_DATA_DIR": directory}):
                    self.assertTrue(configure(client, "/test/ninai-mcp", target=path))
                    data = json.loads(path.read_text())
                    entry = data[key]["ninai-local"]
                    self.assertEqual(entry["env"], {"NINAI_CLIENT_ID": client, "NINAI_DATA_DIR": str(Path(directory).resolve())})
                    if client == "vscode":
                        self.assertEqual(entry["type"], "stdio")
                    self.assertFalse(configure(client, "/test/ninai-mcp", target=path))
                self.assertEqual(path.with_name("mcp.json.ninai-backup").read_text(), original)
                self.assertFalse(configure(client, "/another/ninai-mcp", target=path, remove=True))
                self.assertTrue(configure(client, "/test/ninai-mcp", target=path, remove=True))
                restored = json.loads(path.read_text())
                self.assertEqual(restored[key], {"other": {"command": "keep"}})
                self.assertEqual(restored["inputs"], [{"id": "keep"}])

    def test_invalid_json_schema_conflicts_and_symlinks_preserved(self):
        for content in ('// keep my comment\n{}', '[]', '{"servers":[]}', '{"servers":{"ninai-local":{"command":"other"}}}'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "mcp.json"
                path.write_text(content)
                with self.assertRaises(ValueError):
                    configure("vscode", "/test/ninai-mcp", target=path)
                self.assertEqual(path.read_text(), content)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            target.write_text('{}')
            link = Path(directory) / "mcp.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                configure("cursor", "/test/ninai-mcp", target=link)
            self.assertEqual(target.read_text(), '{}')

    def test_preview_does_not_change_config_or_create_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mcp.json"
            result = subprocess.run([sys.executable, "-m", "ninai.connectors", "cursor", "--command", "/test/ninai-mcp", "--config", str(path)], capture_output=True, text=True, check=True)
            self.assertIn("ninai-local", json.loads(result.stdout)["mcpServers"])
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_status_says_configured_not_connected_and_detects_app_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "Applications/Cursor.app").mkdir(parents=True)
            with patch("ninai.connectors.Path.home", return_value=home), patch("ninai.connectors.shutil.which", return_value=None):
                self.assertTrue(installed("cursor"))
                configure("cursor", "/test/ninai-mcp")
                result = status("cursor")
                self.assertEqual(result["status"], "configured")
                self.assertNotIn("connected", result)


if __name__ == "__main__":
    unittest.main()
