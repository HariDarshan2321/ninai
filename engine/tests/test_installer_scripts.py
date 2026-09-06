from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class InstallerScriptsTest(unittest.TestCase):
    def test_uninstall_removes_only_ninai_and_moves_data_to_trash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            install = home / ".ninai-app"
            data = home / ".ninai"
            (install / "venv" / "bin").mkdir(parents=True)
            os.symlink(sys.executable, install / "venv" / "bin" / "python")
            data.mkdir()
            (data / "ninai.sqlite3").write_text("test vault")
            claude_settings = home / ".claude" / "settings.json"
            claude_settings.parent.mkdir()
            claude_settings.write_text(json.dumps({"hooks": {"SessionStart": [
                {"matcher": "", "hooks": [
                    {"type": "command", "command": str(install / "venv/bin/ninai") + " session-hook --provider claude-code"},
                    {"type": "command", "command": "/usr/bin/other-hook"},
                ]}
            ]}}))
            gemini_settings = home / ".gemini" / "settings.json"
            gemini_settings.parent.mkdir()
            gemini_settings.write_text(json.dumps({"mcpServers": {
                "ninai-local": {"command": str(install / "venv/bin/ninai-mcp")},
                "keep-me": {"command": "/usr/bin/other-mcp"},
            }}))

            env = {**os.environ, "HOME": str(home), "NINAI_INSTALL_DIR": str(install),
                   "NINAI_DATA_DIR": str(data), "PATH": "/usr/bin:/bin"}
            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "uninstall-local")],
                env=env, text=True, capture_output=True, check=True,
            )

            self.assertFalse(install.exists())
            self.assertFalse(data.exists())
            trashed = list((home / ".Trash").glob("Ninai-uninstall-*"))
            self.assertEqual(len(trashed), 1)
            self.assertTrue((trashed[0] / "ninai-app").is_dir())
            self.assertTrue((trashed[0] / "ninai-data" / "ninai.sqlite3").is_file())
            remaining = claude_settings.read_text()
            self.assertNotIn("session-hook", remaining)
            self.assertIn("/usr/bin/other-hook", remaining)
            gemini_config = json.loads(gemini_settings.read_text())
            self.assertNotIn("ninai-local", gemini_config["mcpServers"])
            self.assertEqual(gemini_config["mcpServers"]["keep-me"]["command"], "/usr/bin/other-mcp")
            self.assertIn("recoverable copy", result.stdout)

    def test_installer_configures_gemini_as_an_untrusted_scoped_mcp_client(self) -> None:
        installer = (ROOT / "scripts" / "install-local").read_text()
        self.assertIn('permission grant gemini project', installer)
        self.assertIn('"NINAI_CLIENT_ID": "gemini"', installer)
        self.assertIn('"trust": False', installer)
        self.assertIn('servers["ninai-local"]', installer)
        self.assertNotIn('session-hook --provider gemini', installer)


if __name__ == "__main__":
    unittest.main()
