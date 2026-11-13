from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ninai import cli
from ninai import integration_skill as skill


class ContinuitySkillTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ninai-skill-test-")
        self.addCleanup(temporary.cleanup)
        # /var is a system symlink on macOS; test using the real temp path.
        self.home = Path(temporary.name).resolve()
        self.root = self.home / ".agents/skills"
        self.destination = self.root / skill.SKILL_NAME
        env = patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        home = patch("pathlib.Path.home", return_value=self.home)
        home.start()
        self.addCleanup(home.stop)

    def old_install(self):
        with patch.object(skill, "SKILL_VERSION", "0"), patch.object(skill, "_bundled_skill", return_value=b"old managed instructions\n"):
            skill.install_continuity_skill()
        return self.snapshot()

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.destination.iterdir() if p.is_file()}

    def test_bundle_exactly_matches_plugin(self):
        plugin = Path(__file__).resolve().parents[2] / "plugins/ninai/skills/project-continuity/SKILL.md"
        self.assertEqual(skill._bundled_skill(), plugin.read_bytes())

    def test_default_install_is_offline_and_preserves_config_without_vault(self):
        config = self.home / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text("# keep this config\n")
        with patch("socket.create_connection", side_effect=AssertionError("no network")):
            result = skill.install_continuity_skill()
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["path"], str(self.destination))
        content = (self.destination / "SKILL.md").read_bytes()
        self.assertEqual(content, skill._bundled_skill())
        marker = json.loads((self.destination / skill.MARKER_NAME).read_text())
        self.assertEqual(marker["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(marker["version"], skill.SKILL_VERSION)
        self.assertEqual(config.read_text(), "# keep this config\n")
        self.assertFalse((self.home / ".ninai").exists())
        self.assertEqual(set(self.snapshot()), {"SKILL.md", skill.MARKER_NAME})

    def test_selected_root_does_not_write_default(self):
        root = self.home / "selected-skills"
        result = skill.install_continuity_skill(target_root=root)
        self.assertEqual(result["path"], str(root / skill.SKILL_NAME))
        self.assertFalse(self.root.exists())

    def test_repeated_install_is_noop_preserving_mtime(self):
        skill.install_continuity_skill()
        note = self.destination / "user-note.txt"
        note.write_text("keep me")
        previous = self.snapshot()
        mtime = (self.destination / "SKILL.md").stat().st_mtime_ns
        with patch.object(skill.os, "replace", side_effect=AssertionError("no replacement expected")):
            self.assertEqual(skill.install_continuity_skill()["status"], "unchanged")
        self.assertEqual(self.snapshot(), previous)
        self.assertEqual((self.destination / "SKILL.md").stat().st_mtime_ns, mtime)

    def test_update_owned_unmodified_version_preserves_unrelated_files(self):
        self.old_install()
        (self.destination / "user-note.txt").write_text("keep me")
        result = skill.install_continuity_skill()
        self.assertEqual(result["status"], "updated")
        self.assertEqual((self.destination / "SKILL.md").read_bytes(), skill._bundled_skill())
        self.assertEqual((self.destination / "user-note.txt").read_text(), "keep me")
        self.assertEqual(skill.install_continuity_skill()["status"], "unchanged")

    def test_newer_owned_version_is_not_downgraded(self):
        with patch.object(skill, "SKILL_VERSION", "2"), patch.object(skill, "_bundled_skill", return_value=b"newer managed instructions"):
            skill.install_continuity_skill()
        previous = self.snapshot()
        with self.assertRaisesRegex(ValueError, "refusing to downgrade"):
            skill.install_continuity_skill()
        self.assertEqual(self.snapshot(), previous)

    def test_unrecognized_owned_version_requires_manual_review(self):
        skill.install_continuity_skill()
        marker = self.destination / skill.MARKER_NAME
        metadata = json.loads(marker.read_text())
        for version in ["future", "1.2", "-1", "1" * 20]:
            with self.subTest(version=version):
                metadata["version"] = version
                marker.write_text(json.dumps(metadata))
                previous = self.snapshot()
                with self.assertRaisesRegex(ValueError, "Unrecognized installed skill version"):
                    skill.install_continuity_skill()
                self.assertEqual(self.snapshot(), previous)

    def test_modified_owned_skill_is_not_overwritten(self):
        self.old_install()
        (self.destination / "SKILL.md").write_text("user edited instructions")
        previous = self.snapshot()
        with self.assertRaisesRegex(ValueError, "edited"):
            skill.install_continuity_skill()
        self.assertEqual(self.snapshot(), previous)

    def test_existing_unowned_identical_skill_is_not_adopted(self):
        self.destination.mkdir(parents=True)
        (self.destination / "SKILL.md").write_bytes(skill._bundled_skill())
        previous = self.snapshot()
        with self.assertRaisesRegex(ValueError, "not managed"):
            skill.install_continuity_skill()
        self.assertEqual(self.snapshot(), previous)

    def test_invalid_markers_fail_closed(self):
        skill.install_continuity_skill()
        marker = self.destination / skill.MARKER_NAME
        for text in ["not json", "[]", '{"owner":"someone-else"}', '{"owner":"ninai.project-continuity","schema":1,"version":"1","sha256":"wrong"}']:
            with self.subTest(text=text):
                marker.write_text(text)
                previous = self.snapshot()
                with self.assertRaisesRegex(ValueError, "ownership marker"):
                    skill.install_continuity_skill()
                self.assertEqual(self.snapshot(), previous)

    def test_root_and_ancestor_symlinks_are_refused(self):
        outside = self.home / "outside"
        outside.mkdir()
        link = self.home / "link"
        link.symlink_to(outside, target_is_directory=True)
        for root in [link, link / "skills"]:
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, "symlink"):
                skill.install_continuity_skill(target_root=root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_destination_symlinks_including_broken_are_refused(self):
        self.root.mkdir(parents=True)
        for name in ["existing", "missing"]:
            outside = self.home / name
            if name == "existing":
                outside.mkdir()
            self.destination.symlink_to(outside, target_is_directory=True)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "symlink"):
                skill.install_continuity_skill()
            self.destination.unlink()
        self.assertEqual(list((self.home / "existing").iterdir()), [])

    def test_skill_and_marker_symlinks_are_refused(self):
        skill.install_continuity_skill()
        for name in ["SKILL.md", skill.MARKER_NAME]:
            owned = self.destination / name
            content = owned.read_bytes()
            outside = self.home / (name + ".outside")
            outside.write_bytes(content)
            owned.unlink()
            owned.symlink_to(outside)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "symlink"):
                skill.install_continuity_skill()
            self.assertEqual(outside.read_bytes(), content)
            owned.unlink()
            owned.write_bytes(content)

    def test_atomic_replace_failure_preserves_old_files_and_cleans_staging(self):
        previous = self.old_install()
        with patch.object(skill.os, "replace", side_effect=OSError("synthetic failure")):
            with self.assertRaisesRegex(OSError, "synthetic failure"):
                skill.install_continuity_skill()
        self.assertEqual(self.snapshot(), previous)
        self.assertEqual(list(self.destination.glob(".ninai-skill-*")), [])

    def test_interrupted_two_file_commit_refuses_retry(self):
        self.old_install()
        replace = os.replace
        def fail_marker(source, destination):
            if Path(destination).name == skill.MARKER_NAME:
                raise OSError("synthetic interruption")
            return replace(source, destination)
        with patch.object(skill.os, "replace", side_effect=fail_marker):
            with self.assertRaisesRegex(OSError, "interruption"):
                skill.install_continuity_skill()
        previous = self.snapshot()
        self.assertEqual(previous["SKILL.md"], skill._bundled_skill())
        with self.assertRaisesRegex(ValueError, "edited"):
            skill.install_continuity_skill()
        self.assertEqual(self.snapshot(), previous)
        self.assertEqual(list(self.destination.glob(".ninai-skill-*")), [])

    def test_unsupported_clients_make_no_changes(self):
        for client in ["claude", "gemini", "CODEX", "../codex"]:
            with self.subTest(client=client), self.assertRaisesRegex(ValueError, "Codex only"):
                skill.install_continuity_skill(client)
        self.assertFalse(self.root.exists())

    def test_cli_installs_before_initializing_store(self):
        output = io.StringIO()
        with patch("sys.argv", ["ninai", "integration-skill", "install", "--client", "codex"]), patch.object(cli, "MemoryStore") as store, redirect_stdout(output):
            cli.main()
        store.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["status"], "installed")
        self.assertEqual((self.destination / "SKILL.md").read_bytes(), skill._bundled_skill())
        self.assertFalse((self.home / ".ninai").exists())

    def test_cli_conflict_exits_without_store_or_overwrite(self):
        self.destination.mkdir(parents=True)
        (self.destination / "SKILL.md").write_text("user instructions")
        errors = io.StringIO()
        with patch("sys.argv", ["ninai", "integration-skill", "install", "--client", "codex"]), patch.object(cli, "MemoryStore") as store, redirect_stderr(errors):
            with self.assertRaises(SystemExit) as stopped:
                cli.main()
        self.assertEqual(stopped.exception.code, 1)
        self.assertIn("not managed", errors.getvalue())
        store.assert_not_called()
        self.assertEqual((self.destination / "SKILL.md").read_text(), "user instructions")


if __name__ == "__main__":
    unittest.main()
