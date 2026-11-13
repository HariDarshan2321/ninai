from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("restore_comparison", ROOT / "scripts/compare_postgres_restore.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RestoreComparisonTests(unittest.TestCase):
    source = "postgresql://operator:secret@localhost:5432/source"
    restore = "postgresql://operator:other@localhost:5432/restore"

    def test_fingerprints_bind_target_not_password(self):
        self.assertEqual(MODULE.target_fingerprint(self.source), MODULE.target_fingerprint(self.source.replace("secret", "rotated")))
        self.assertNotEqual(MODULE.target_fingerprint(self.source), MODULE.target_fingerprint(self.restore))

    def test_rejects_connection_overrides_and_implicit_targets(self):
        for url in ("", "dbname=prod", "postgresql:///prod", self.source + "?host=prod", self.source + "#x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                MODULE.target_fingerprint(url)

    def test_confirmation_is_required_and_must_match(self):
        fingerprints = [MODULE.target_fingerprint(url) for url in (self.source, self.restore)]
        for confirmation, isolated in (("", True), (fingerprints[1], False)):
            with self.assertRaises(ValueError):
                MODULE.check_targets(self.source, self.restore, fingerprints[0], confirmation, isolated)
        self.assertEqual(MODULE.check_targets(self.source, self.restore, *fingerprints, True), tuple(fingerprints))

    def test_same_database_different_role_is_rejected(self):
        other = self.source.replace("operator", "reader")
        with self.assertRaises(ValueError):
            MODULE.check_targets(self.source, other, MODULE.target_fingerprint(self.source), MODULE.target_fingerprint(other), True)

    def test_equal_counts_changed_digest_fails(self):
        source = {"valid": True, "tables": {"memories": {"rows": 2, "digest": "a"}}}
        restore = {"valid": True, "tables": {"memories": {"rows": 2, "digest": "b"}}}
        report = MODULE.compare_reports(source, restore)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["mismatched_tables"], ["memories"])

    def test_identical_invalid_snapshots_cannot_pass(self):
        invalid = {"valid": False, "tables": {}}
        self.assertEqual(MODULE.compare_reports(invalid, invalid)["status"], "failed")

    def test_exception_output_does_not_leak_secrets(self):
        with patch("sys.argv", ["compare", "--fingerprint-env", "BAD"]), patch.dict(os.environ, {"BAD": "postgresql://user:PRIVATE_SECRET@host/db?x=y"}), patch("builtins.print") as output:
            self.assertEqual(MODULE.main(), 2)
        self.assertNotIn("PRIVATE_SECRET", str(output.call_args))


@unittest.skipUnless(os.environ.get("NINAI_RESTORE_REHEARSAL_PG_BIN"), "explicit local PostgreSQL binaries required")
class SyntheticDumpRestoreTests(unittest.TestCase):
    """Creates and removes only a fresh temporary loopback PostgreSQL cluster."""

    def test_real_dump_restore_detects_changes_and_enforces_read_only(self):
        import psycopg
        from ninai_cloud.migrations import apply_migrations

        spec = importlib.util.spec_from_file_location("cross_provider_fixture", ROOT / "scripts/verify_cross_provider.py")
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        pg_bin = Path(os.environ["NINAI_RESTORE_REHEARSAL_PG_BIN"]).resolve()
        self.assertTrue(pg_bin.is_absolute())
        with tempfile.TemporaryDirectory(prefix="ninai-restore-rehearsal-") as directory:
            base = Path(directory)
            with socket.socket() as port_socket:
                port_socket.bind(("127.0.0.1", 0))
                port = port_socket.getsockname()[1]
            def run(binary, *args):
                return subprocess.run([str(pg_bin / binary), *map(str, args)], check=True,
                                      capture_output=True, text=True, timeout=60)
            run("initdb", "-D", base / "data", "-A", "trust", "-U", "rehearsal", "--no-locale", "--encoding=UTF8")
            run("pg_ctl", "-D", base / "data", "-l", base / "postgres.log", "-o", f"-h 127.0.0.1 -p {port} -k {directory}", "-w", "start")
            try:
                origin = f"postgresql://rehearsal@127.0.0.1:{port}"
                with psycopg.connect(origin + "/postgres", autocommit=True) as admin:
                    admin.execute("CREATE DATABASE synthetic_source")
                    admin.execute("CREATE DATABASE synthetic_restore")
                source_url, restore_url = origin + "/synthetic_source", origin + "/synthetic_restore"
                apply_migrations(source_url)
                self.assertTrue(fixture.run_verification(source_url, cleanup=False)["passed"])
                run("pg_dump", "--dbname", source_url, "--format=custom", "--no-owner", "--no-acl", "--file", base / "synthetic.dump")
                run("pg_restore", "--dbname", restore_url, "--exit-on-error", "--no-owner", "--no-acl", base / "synthetic.dump")
                def compare():
                    with psycopg.connect(source_url) as source, psycopg.connect(restore_url) as restore:
                        self.assertNotEqual(MODULE.begin_snapshot(source, 10), MODULE.begin_snapshot(restore, 10))
                        report = MODULE.compare_reports(MODULE.inspect(source, "ephemeral-test-salt", MODULE.time.monotonic()+60), MODULE.inspect(restore, "ephemeral-test-salt", MODULE.time.monotonic()+60))
                        source.rollback()
                        restore.rollback()
                        return report
                self.assertEqual(compare()["status"], "ok")
                with psycopg.connect(restore_url) as restored:
                    MODULE.begin_snapshot(restored, 10)
                    with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
                        restored.execute("DELETE FROM public.memories")
                    restored.rollback()
                with psycopg.connect(restore_url) as restored:
                    restored.execute("UPDATE public.memories SET content='synthetic changed text'")
                changed = compare()
                self.assertEqual(changed["status"], "failed")
                self.assertEqual(changed["mismatched_tables"], ["memories"])
                self.assertNotIn("synthetic changed text", json.dumps(changed))
                with psycopg.connect(restore_url) as restored:
                    restored.execute("UPDATE public.memory_sources SET source_uri=''")
                self.assertGreater(compare()["restore"]["invariant_violations"]["memory_provenance_missing"], 0)
                with psycopg.connect(restore_url) as restored:
                    restored.execute("DROP INDEX public.users_signup_idx")
                self.assertFalse(compare()["schema_match"])
                with psycopg.connect(restore_url) as restored:
                    restored.execute("ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY")
                with self.assertRaises(ValueError):
                    compare()
            finally:
                run("pg_ctl", "-D", base / "data", "-m", "immediate", "-w", "stop")


if __name__ == "__main__":
    unittest.main()
