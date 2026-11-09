from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ninai.store import MemoryStore
from ninai.session_capture import _project_identity


class CliProjectPermissionsTest(unittest.TestCase):
    def test_project_creation_grants_and_revocation_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "NINAI_DATA_DIR": directory}

            def run(*arguments: str) -> str:
                completed = subprocess.run(
                    [sys.executable, "-m", "ninai.cli", *arguments],
                    env=environment, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return completed.stdout

            project = json.loads(run("project", "create", "Synthetic CLI project", "--path", str(Path(directory) / "project")))
            project_id = project["id"]
            _, binding, _ = _project_identity(str(Path(directory) / "project"))
            self.assertEqual(project["binding_key"], binding)
            run("remember", "Synthetic CLI decision", "--project", project_id)
            query = ("recall", "Synthetic CLI decision", "--client", "test-assistant", "--project", project_id)
            self.assertEqual(json.loads(run(*query))["facts"], [])
            run("project", "grant", "test-assistant", project_id)
            self.assertEqual(len(json.loads(run(*query))["facts"]), 1)
            store = MemoryStore(Path(directory) / "ninai.sqlite3")
            with self.assertRaises(PermissionError):
                store.remember("Read cannot write", project_id=project_id, client_id="test-assistant")
            run("project", "grant", "test-assistant", project_id, "--capability", "write")
            store.remember("Explicit write succeeds", project_id=project_id, client_id="test-assistant")
            run("project", "revoke", "test-assistant", project_id)
            self.assertEqual(json.loads(run(*query))["facts"], [])
            run("project", "revoke", "test-assistant", project_id, "--capability", "write")
            with self.assertRaises(PermissionError):
                store.remember("Revoked write denied", project_id=project_id, client_id="test-assistant")


if __name__ == "__main__":
    unittest.main()
