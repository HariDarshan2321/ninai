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
            self.assertIn("recoverable copy", result.stdout)


if __name__ == "__main__":
    unittest.main()
