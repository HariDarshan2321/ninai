from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sqlite3
import shlex
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class InstallerScriptsTest(unittest.TestCase):
    def write_build_stubs(self, directory: Path) -> None:
        """Fake package/build tools; run the complete real installer orchestration."""
        directory.mkdir()
        bootstrap = directory / "python-bootstrap"
        bootstrap.write_text(f"#!{sys.executable}\n" + """import os,sys,shutil
from pathlib import Path
args=sys.argv[1:]
if args[:2] == ['-m','venv']:
    target=Path(args[2])/'bin'; target.mkdir(parents=True)
    shutil.copy2(__file__,target/'python')
    (target/'ninai').write_text('#!/bin/sh\\n[ -z \"${TEST_COMMAND_LOG:-}\" ] || echo \"$*\" >> \"$TEST_COMMAND_LOG\"\\nexit 0\\n'); (target/'ninai').chmod(0o755)
    (target/'pyinstaller').write_text('#!/bin/sh\\nmkdir -p "$NINAI_INSTALL_DIR/Ninai.app"\\n'); (target/'pyinstaller').chmod(0o755)
    (target/'pyi-makespec').write_text('#!/bin/sh\\nmkdir -p "$NINAI_INSTALL_DIR/.app-build/spec"\\necho "app = BUNDLE(None)" > "$NINAI_INSTALL_DIR/.app-build/spec/Ninai.spec"\\n'); (target/'pyi-makespec').chmod(0o755)
elif args[:2] == ['-m','pip']:
    pass
elif args[:1] == ['-c'] and 'ninai-app-icon.svg' in args[1]:
    print('/synthetic/icon.svg')
elif args[:1] == ['-c'] and 'ninai.desktop.app' in args[1]:
    print('/synthetic/app.py')
else:
    os.execv(os.environ['TEST_REAL_PYTHON'],[os.environ['TEST_REAL_PYTHON'],*args])
""")
        bootstrap.chmod(0o755)
        for name, body in {
            "uname": "printf 'Darwin\\n'",
            "xcrun": "if [ \"$1\" = --find ]; then echo /synthetic/swiftc; else for output do :; done; printf '#!/bin/sh\\nexit 0\\n' > \"$output\"; chmod 755 \"$output\"; fi",
            "sips": "exit 0", "iconutil": "exit 0", "xattr": "exit 0", "codesign": "exit 0", "open": "exit 0",
        }.items():
            path = directory / name
            path.write_text("#!/bin/sh\n" + body + "\n")
            path.chmod(0o755)

    def installer_function(self, name: str) -> str:
        source = (ROOT / "scripts" / "install-local").read_text()
        start = source.index(f"\n{name}() {{") + 1
        return source[start:source.index("\n}\n", start) + 3]

    def test_recovery_snapshot_includes_committed_wal_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            source = data / "ninai.sqlite3"
            db = sqlite3.connect(source)
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("CREATE TABLE payload(content TEXT)")
                db.execute("INSERT INTO payload VALUES('committed memory and source')")
                db.commit()
                db.execute("INSERT INTO payload VALUES('not yet committed')")
                command = 'python_cmd="$TEST_PYTHON"\n' + self.installer_function("create_recovery_snapshot") + '\ncreate_recovery_snapshot\n'
                result = subprocess.run(["bash", "-c", command], env={**os.environ, "NINAI_DATA_DIR": str(data), "TEST_PYTHON": sys.executable}, capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stderr)
                copies = list((data / "recovery").glob("*.sqlite3"))
                self.assertEqual(len(copies), 1)
                self.assertEqual(copies[0].stat().st_mode & 0o777, 0o600)
                with sqlite3.connect(copies[0]) as snapshot:
                    self.assertEqual(snapshot.execute("SELECT content FROM payload").fetchall(), [("committed memory and source",)])
                    self.assertEqual(snapshot.execute("PRAGMA quick_check").fetchone(), ("ok",))
                self.assertEqual(db.execute("SELECT count(*) FROM payload").fetchone(), (2,))
            finally:
                db.close()

    def test_recovery_snapshot_rejects_corruption_and_symlink_destination(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as temporary:
                data = Path(temporary)
                (data / "ninai.sqlite3").write_bytes(b"not a valid database")
                if symlink:
                    target = data / "unrelated"
                    target.mkdir()
                    (data / "recovery").symlink_to(target)
                command = 'python_cmd="$TEST_PYTHON"\n' + self.installer_function("create_recovery_snapshot") + '\ncreate_recovery_snapshot\n'
                result = subprocess.run(["bash", "-c", command], env={**os.environ, "NINAI_DATA_DIR": str(data), "TEST_PYTHON": sys.executable}, capture_output=True, text=True, timeout=40)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((data / "ninai.sqlite3").read_bytes(), b"not a valid database")
                self.assertEqual(list((data / "recovery").glob("*.sqlite3")), [])

    def test_failed_connector_restores_prior_settings_and_installation(self) -> None:
        for client, stage in ((client, stage) for client in ("claude", "codex") for stage in ("add", "hooks", "fresh")):
            with self.subTest(client=client, stage=stage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home = root / "home"
                home.mkdir()
                install = root / "installation"
                if stage != "fresh":
                    install.mkdir()
                    (install / "version").write_text("previous working app")
                    (install / "venv/bin").mkdir(parents=True)
                    (install / "venv/bin/ninai").write_text("#!/bin/sh\nexit 0\n")
                    (install / "venv/bin/ninai").chmod(0o755)
                config = home / (".claude.json" if client == "claude" else ".codex/config.toml")
                config.parent.mkdir(parents=True, exist_ok=True)
                if stage != "fresh":
                    config.write_text("original connection and unrelated settings\n")
                hooks = home / (".claude/settings.json" if client == "claude" else ".codex/hooks.json")
                hooks.parent.mkdir(parents=True, exist_ok=True)
                original_hooks = '{"hooks": []}\n' if stage == "hooks" else '{"hooks": {}, "keep": true}\n'
                if stage != "fresh":
                    hooks.write_text(original_hooks)
                binary = root / "bin"
                self.write_build_stubs(binary)
                cli = binary / client
                cli.write_text(f"#!{sys.executable}\n" + """import os,sys
from pathlib import Path
p=Path(os.environ['TEST_CONFIG'])
if 'remove' in sys.argv:
    p.write_text('removed previous entry')
elif 'add' in sys.argv:
    p.write_text('partially written failed entry')
    if os.environ['TEST_FAILURE_STAGE'] != 'hooks': sys.exit(9)
""")
                cli.chmod(0o755)
                environment = {**os.environ, "HOME": str(home), "TEST_CONFIG": str(config),
                               "NINAI_INSTALL_DIR": str(install), "NINAI_PYTHON": str(binary / "python-bootstrap"),
                               "TEST_FAILURE_STAGE": stage, "TEST_COMMAND_LOG": str(root / "calls.log"),
                               "TEST_REAL_PYTHON": sys.executable,
                               "PATH": str(binary) + ":/usr/bin:/bin"}
                environment.pop("CLAUDE_CONFIG_DIR", None)
                environment.pop("CODEX_HOME", None)
                result = subprocess.run(["bash", str(ROOT / "scripts/install-local"), "--client", "claude-code" if client == "claude" else "codex", "--session-capture", "off"], env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1 if stage == "hooks" else 9, result.stderr)
                self.assertNotIn("capture ", (root / "calls.log").read_text())
                if stage == "fresh":
                    self.assertFalse(config.exists())
                    self.assertFalse(hooks.exists())
                    self.assertFalse(install.exists())
                else:
                    self.assertEqual(config.read_text(), "original connection and unrelated settings\n")
                    self.assertEqual(hooks.read_text(), original_hooks)
                    self.assertEqual((install / "version").read_text(), "previous working app")
                self.assertEqual(list(root.glob("installation.previous.*")), [])
                self.assertEqual(list(root.glob(".ninai-settings-backup.*")), [])
                self.assertIn("Setup did not finish", result.stderr)

    def test_hook_merge_is_atomic_preserves_unrelated_and_carries_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "settings.json"
            executable = root / "installation with spaces" / "venv/bin/ninai"
            executable.parent.mkdir(parents=True)
            executable.write_text(f"#!{sys.executable}\nimport os,json,sys\nprint(json.dumps({{'data':os.environ.get('NINAI_DATA_DIR'),'args':sys.argv[1:]}}))\n")
            executable.chmod(0o755)
            target.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": "/usr/bin/keep-hook"},
                {"type": "command", "command": shlex.join([str(executable), "session-hook", "--provider", "claude-code"])},
            ]}]}, "keep": "original"}))
            target.chmod(0o640)
            environment = {**os.environ, "TEST_PYTHON": sys.executable, "TEST_TARGET": str(target),
                           "TEST_INSTALL": str(executable.parents[2]), "NINAI_DATA_DIR": str(root / "separate vault")}
            script = 'set -euo pipefail\npython_cmd="$TEST_PYTHON"\ninstall_dir="$TEST_INSTALL"\n' + self.installer_function("merge_hooks") + '\nmerge_hooks "$TEST_TARGET" claude-code yes\n'
            for _ in range(2):
                subprocess.run(["bash", "-c", script], env=environment, capture_output=True, text=True, check=True)
            data = json.loads(target.read_text())
            self.assertEqual(data["keep"], "original")
            commands = [item["command"] for group in data["hooks"]["SessionStart"] for item in group["hooks"]]
            self.assertIn("/usr/bin/keep-hook", commands)
            self.assertEqual(len(commands), 2)
            command = next(value for value in commands if value != "/usr/bin/keep-hook")
            result = subprocess.run(["bash", "-c", command], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), {"data": environment["NINAI_DATA_DIR"], "args": ["session-hook", "--provider", "claude-code"]})
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            for malformed in ('[]', '{"hooks":[]}', '{"hooks":{"SessionStart":{}}}'):
                target.write_text(malformed)
                result = subprocess.run(["bash", "-c", script], env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), malformed)

    def test_installer_refuses_unrelated_or_overlapping_directories_without_changes(self) -> None:
        for kind in ("unrelated", "inside-data", "contains-data", "symlink", "relative-data", "database-symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home = root / "home"
                home.mkdir()
                application = root / "application"
                application.mkdir()
                marker = application / "keep-me"
                marker.write_text("original unrelated file")
                if kind != "unrelated":
                    (application / "venv/bin").mkdir(parents=True)
                    executable = application / "venv/bin/ninai"
                    executable.write_text("#!/bin/sh\nexit 0\n")
                    executable.chmod(0o755)
                data = application / "data" if kind == "contains-data" else root
                if kind == "relative-data":
                    data = Path("relative-vault")
                if kind == "database-symlink":
                    data = root / "safe-looking-memory-folder"
                    data.mkdir()
                    (data / "ninai.sqlite3").symlink_to(marker)
                target = application
                if kind == "symlink":
                    target = root / "app-link"
                    target.symlink_to(application, target_is_directory=True)
                binary = root / "bin"
                self.write_build_stubs(binary)
                environment = {**os.environ, "HOME": str(home), "NINAI_INSTALL_DIR": str(target), "NINAI_DATA_DIR": str(data),
                               "NINAI_PYTHON": str(binary / "python-bootstrap"), "TEST_REAL_PYTHON": sys.executable,
                               "PATH": str(binary) + ":/usr/bin:/bin"}
                result = subprocess.run(["bash", str(ROOT / "scripts/install-local"), "--client", "none", "--session-capture", "off"], env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(marker.read_text(), "original unrelated file")
                self.assertEqual(list(root.glob("application.previous.*")), [])
                self.assertEqual(list(root.glob(".ninai-settings-backup.*")), [])

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
        self.assertNotIn('permission grant', installer)
        self.assertNotIn('mcp remove ninai-cloud', installer)
        self.assertIn('connect_editor', installer)
        self.assertIn('"NINAI_CLIENT_ID": "gemini"', installer)
        self.assertIn('"trust": False', installer)
        self.assertIn('servers["ninai-local"]', installer)
        self.assertNotIn('session-hook --provider gemini', installer)

    def test_uninstall_matches_quoted_owned_hooks_and_preserves_other_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            install = home / "installation with spaces"
            (install / "venv/bin").mkdir(parents=True)
            os.symlink(sys.executable, install / "venv/bin/python")
            data = home / "data"
            data.mkdir()
            (data / "ninai.sqlite3").write_text("synthetic data")
            executable = str(install / "venv/bin/ninai")
            own = shlex.join(["env", "NINAI_DATA_DIR=" + str(data), executable, "session-hook", "--provider", "codex"])
            keep = [shlex.join(["env", "NINAI_DATA_DIR=" + str(data), "/usr/bin/other", "session-hook"]),
                    shlex.join([executable + "-other", "session-hook"]),
                    shlex.join([executable, "search", "something"]), "unterminated 'quote"]
            config_dir = home / "custom-codex"
            config_dir.mkdir()
            target = config_dir / "hooks.json"
            target.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command": command} for command in [own, *keep]
            ]}]}}))
            environment = {**os.environ, "HOME": str(home), "NINAI_INSTALL_DIR": str(install),
                           "NINAI_DATA_DIR": str(data), "CODEX_HOME": str(config_dir), "PATH": "/usr/bin:/bin"}
            subprocess.run(["bash", str(ROOT / "scripts/uninstall-local")], env=environment, capture_output=True, text=True, check=True)
            commands = [item["command"] for group in json.loads(target.read_text())["hooks"]["SessionStart"] for item in group["hooks"]]
            self.assertEqual(commands, keep)

    def test_uninstall_preserves_other_installations_and_removes_only_owned_cli_entries(self) -> None:
        for owned_client in ("claude", "codex"):
            with self.subTest(owned_client=owned_client), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                install = home / ".ninai-app"
                (install / "venv/bin").mkdir(parents=True)
                os.symlink(sys.executable, install / "venv/bin/python")
                data = home / "data"
                data.mkdir()
                owned = str(install / "venv/bin/ninai-mcp")
                other = str(home / "other-installation/venv/bin/ninai-mcp")
                (home / ".claude.json").write_text(json.dumps({"mcpServers": {
                    "ninai-local": {"command": other}, "ninai": {"command": owned if owned_client == "claude" else other},
                    "ninai-cloud": {"command": "/usr/bin/keep-cloud"},
                }}))
                (home / ".codex").mkdir()
                codex = home / ".codex/config.toml"
                codex.write_text('[mcp_servers.ninai-local]\ncommand = ' + json.dumps(owned if owned_client == "codex" else other) + '\n')
                (home / ".gemini").mkdir()
                gemini = home / ".gemini/settings.json"
                original_gemini = json.dumps({"mcpServers": {"ninai-local": {"command": other}, "keep-me": {"command": "other"}}})
                gemini.write_text(original_gemini)
                binary = home / "bin"
                binary.mkdir()
                log = home / "calls.jsonl"
                for client in ("claude", "codex"):
                    cli = binary / client
                    cli.write_text(f"#!{sys.executable}\n" + "import os,sys,json\nfrom pathlib import Path\np=Path(os.environ['TEST_CALL_LOG'])\nwith p.open('a') as f: f.write(json.dumps([Path(sys.argv[0]).name,*sys.argv[1:]])+'\\n')\n")
                    cli.chmod(0o755)
                environment = {**os.environ, "HOME": str(home), "NINAI_INSTALL_DIR": str(install),
                               "NINAI_DATA_DIR": str(data), "TEST_CALL_LOG": str(log), "PATH": str(binary) + ":/usr/bin:/bin"}
                environment.pop("CLAUDE_CONFIG_DIR", None)
                environment.pop("CODEX_HOME", None)
                subprocess.run(["bash", str(ROOT / "scripts/uninstall-local")], env=environment, capture_output=True, text=True, check=True)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(calls, [["claude", "mcp", "remove", "ninai", "--scope", "user"]] if owned_client == "claude" else [["codex", "mcp", "remove", "ninai-local"]])
                self.assertEqual(gemini.read_text(), original_gemini)
                if owned_client == "claude":
                    self.assertIn(other, codex.read_text())

    def test_windows_preview_installer_is_user_scoped_and_connects_supported_clients(self) -> None:
        installer = (ROOT / "scripts" / "install-windows.ps1").read_text()
        self.assertIn('$env:LOCALAPPDATA\\Ninai', installer)
        self.assertIn('InstallDir must be inside LOCALAPPDATA', installer)
        self.assertNotIn('permission grant', installer)
        self.assertIn('Connect-Editor', installer)
        self.assertIn('trust = $false', installer)
        self.assertNotIn('Start-Process powershell -Verb RunAs', installer)


if __name__ == "__main__":
    unittest.main()
