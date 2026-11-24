from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("restore_comparison", ROOT / "scripts/compare_postgres_restore.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TEAM_ISSUER = "https://restore-identity.example.invalid/"
TEAM_SOURCE = "https://github.com/restore/demo/pull/1"
REVOKED_TEAM_TOKEN = "b" * 43  # Synthetic fixture only.


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
                    admin.execute("CREATE DATABASE synthetic_runtime")
                source_url, restore_url = origin + "/synthetic_source", origin + "/synthetic_restore"
                apply_migrations(source_url)
                self.assertTrue(fixture.run_verification(source_url, cleanup=False, run_id="restore-rehearsal")["passed"])
                self.seed_team_snapshot(psycopg, source_url, fixture._ids("restore-rehearsal"))
                run("pg_dump", "--dbname", source_url, "--format=custom", "--no-owner", "--no-acl", "--file", base / "synthetic.dump")
                run("pg_restore", "--dbname", restore_url, "--exit-on-error", "--no-owner", "--no-acl", base / "synthetic.dump")
                def compare():
                    with psycopg.connect(source_url) as source, psycopg.connect(restore_url) as restore:
                        self.assertNotEqual(MODULE.begin_snapshot(source, 10), MODULE.begin_snapshot(restore, 10))
                        report = MODULE.compare_reports(MODULE.inspect(source, "ephemeral-test-salt", MODULE.time.monotonic()+60), MODULE.inspect(restore, "ephemeral-test-salt", MODULE.time.monotonic()+60))
                        source.rollback()
                        restore.rollback()
                        return report
                initial = compare()
                self.assertEqual(initial["status"], "ok")
                for table, count in (("team_projects", 1), ("team_decision_versions", 2), ("team_supersessions", 1),
                                     ("team_source_pins", 2), ("team_bindings", 1)):
                    self.assertEqual(initial["restore"]["tables"][table]["rows"], count)
                self.assert_filtered_snapshot_is_rejected(psycopg, source_url)
                run("pg_restore", "--dbname", origin + "/synthetic_runtime", "--exit-on-error", "--no-owner", "--no-acl", base / "synthetic.dump")
                self.assert_restored_service_behaviour(fixture, origin + "/synthetic_runtime")
                self.assert_restored_team_behaviour(psycopg, origin + "/synthetic_runtime", fixture._ids("restore-rehearsal"))
                with psycopg.connect(restore_url) as restored:
                    restored.execute("ALTER TABLE public.team_members NO FORCE ROW LEVEL SECURITY")
                with self.assertRaises(ValueError):
                    compare()
                with psycopg.connect(restore_url) as restored:
                    restored.execute("ALTER TABLE public.team_members FORCE ROW LEVEL SECURITY")
                    restored.execute("UPDATE public.team_bindings SET revoked_at=NULL")
                self.assertEqual(compare()["mismatched_tables"], ["team_bindings"])
                with psycopg.connect(restore_url) as restored:
                    restored.execute("SELECT setval('public.team_decision_events_sequence_seq',1)")
                self.assertGreater(compare()["restore"]["invariant_violations"]["team_decision_events_sequence_behind"], 0)
                run("pg_restore", "--dbname", restore_url, "--clean", "--exit-on-error", "--no-owner", "--no-acl", base / "synthetic.dump")
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

    def assert_filtered_snapshot_is_rejected(self, psycopg, source_url):
        with psycopg.connect(source_url) as db:
            db.execute("CREATE ROLE limited_restore_reader NOLOGIN NOSUPERUSER NOBYPASSRLS")
            db.execute("GRANT USAGE ON SCHEMA public TO limited_restore_reader")
            db.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO limited_restore_reader")
        with psycopg.connect(source_url, autocommit=True) as db:
            db.execute("SET ROLE limited_restore_reader")
            db.autocommit = False
            MODULE.begin_snapshot(db, 10)
            with self.assertRaisesRegex(ValueError, "complete snapshot role"):
                MODULE.inspect(db, "ephemeral-test-salt", MODULE.time.monotonic() + 60)

    @staticmethod
    def seed_team_snapshot(psycopg, source_url, ids):
        from ninai_cloud.team_sources import source_fingerprint
        from ninai_cloud.team_store import digest

        workspace, project, owner = (ids[key] for key in ("workspace", "shared-project", "user"))
        member, decision, binding = uuid4(), uuid4(), uuid4()
        with psycopg.connect(source_url) as db:
            db.execute("SELECT set_config('ninai.team_workspace_id',%s,true)", (workspace,))
            db.execute("INSERT INTO users(id,email,display_name) VALUES(%s,%s,'Removed member')",
                       (member, f"{member}@example.invalid"))
            db.execute("INSERT INTO oauth_identities(id,issuer,subject,user_id) VALUES(%s,%s,'fixture-owner',%s)",
                       (uuid4(), TEAM_ISSUER, owner))
            db.execute("INSERT INTO team_workspaces(workspace_id) VALUES(%s)", (workspace,))
            db.execute("""INSERT INTO team_members(workspace_id,user_id,role,revoked_at)
                VALUES(%s,%s,'owner',NULL),(%s,%s,'member',now())""", (workspace, owner, workspace, member))
            db.execute("""INSERT INTO team_projects(workspace_id,id,name,slug)
                VALUES(%s,%s,'Team restore test','team-restore-test')""", (workspace, project))
            db.execute("""INSERT INTO team_project_members(workspace_id,project_id,user_id,role)
                VALUES(%s,%s,%s,'maintainer')""", (workspace, project, owner))
            db.execute("""INSERT INTO team_bindings(workspace_id,project_id,id,sponsor_user_id,kind,
                client_registration,token_hash,expires_at,revoked_at)
                VALUES(%s,%s,%s,%s,'human','synthetic-codex',%s,now()+interval '1 hour',now())""",
                (workspace, project, binding, member, digest(REVOKED_TEAM_TOKEN)))
            db.execute("""INSERT INTO team_binding_actions(workspace_id,project_id,binding_id,action,revoked_at)
                VALUES(%s,%s,%s,'read',now())""", (workspace, project, binding))
            db.execute("""INSERT INTO team_decisions(workspace_id,project_id,id,created_by_user_id,visibility,topic)
                VALUES(%s,%s,%s,%s,'team','restore-drill')""", (workspace, project, decision, owner))
            for version in (1, 2):
                version_key = (workspace, project, decision, version)
                db.execute("""INSERT INTO team_decision_versions
                    (workspace_id,project_id,decision_id,version,rule,proposed_by_user_id)
                    VALUES(%s,%s,%s,%s,'Synthetic restore decision',%s)""", (*version_key, owner))
                source = db.execute("""INSERT INTO team_decision_sources
                    (workspace_id,project_id,decision_id,version,provider,resource_key,source_url)
                    VALUES(%s,%s,%s,%s,'github','restore/demo/pull/1',%s) RETURNING id""",
                    (*version_key, TEAM_SOURCE)).fetchone()[0]
                state = """INSERT INTO team_decision_events(workspace_id,project_id,decision_id,version,state,actor_user_id)
                    VALUES(%s,%s,%s,%s,%s,%s)"""
                db.execute(state, (*version_key, "proposed", owner))
                db.execute("""INSERT INTO team_source_pins(workspace_id,project_id,decision_id,version,source_id,fingerprint)
                    VALUES(%s,%s,%s,%s,%s,%s)""",
                    (*version_key, source, source_fingerprint("github", "restore/demo/pull/1", "fixture-v1")))
                if version == 2:
                    db.execute("""INSERT INTO team_supersessions(workspace_id,project_id,decision_id,version,
                        replaces_decision_id,replaces_version) VALUES(%s,%s,%s,%s,%s,1)""", (*version_key, decision))
                    db.execute(state, (workspace, project, decision, 1, "replaced", owner))
                db.execute(state, (*version_key, "approved", owner))

    def assert_restored_service_behaviour(self, fixture, restored_url):
        from ninai_cloud.postgres_store import AuthorizationError, PostgresStore, Principal

        ids = fixture._ids("restore-rehearsal")
        store = PostgresStore(restored_url)
        granted = Principal(ids["user"], ids["workspace"], ids["claude-client"])
        revoked = Principal(ids["user"], ids["workspace"], ids["codex-client"])
        shared = store.search(granted, "shared continuity")
        self.assertEqual([m.source_uri for m in shared], ["claude-code://session/acceptance/turn-1"])
        private = store.search(granted, "zephyr")
        self.assertEqual([m.scope_id for m in private], [ids["private-project"]])
        with self.assertRaises(AuthorizationError):
            store.search(revoked, "shared continuity")

    def assert_restored_team_behaviour(self, psycopg, restored_url, ids):
        from psycopg.rows import dict_row

        from ninai_cloud.postgres_store import AuthorizationError
        from ninai_cloud.team_runtime import verify_team_runtime
        from ninai_cloud.team_sources import SourceAccess, SourceProof, source_fingerprint
        from ninai_cloud.team_store import TeamHuman, TeamStore

        def operator():
            return psycopg.connect(restored_url, row_factory=dict_row)

        def runtime():
            return psycopg.connect(restored_url, user="restore_team_runtime", row_factory=dict_row)

        class SyntheticVerifier:
            def verify(self, request):
                fingerprint = source_fingerprint(request.reference.provider, request.reference.resource_key, "fixture-v1")
                return SourceProof(request, datetime.now(timezone.utc), SourceAccess.GRANTED, fingerprint)

        with operator() as db:
            db.execute("CREATE ROLE restore_team_runtime LOGIN NOSUPERUSER NOBYPASSRLS")
            grants = (ROOT / "cloud" / "team_runtime_grants.sql").read_text()
            body = grants[grants.index("BEGIN;") + len("BEGIN;"):grants.rindex("COMMIT;")]
            db.execute(body.replace(':"team_runtime_role"', "restore_team_runtime"))
        verify_team_runtime(runtime, operator)
        workspace, project = ids["workspace"], ids["shared-project"]
        owner = TeamHuman(ids["user"], TEAM_ISSUER, "fixture-owner", int(time.time()) + 60)
        store = TeamStore(runtime, verifier=SyntheticVerifier())
        packet = store.context(workspace, project, owner, task="restore drill")
        self.assertEqual(packet.payload["current"][0]["version"], 2)
        self.assertEqual(packet.payload["current"][0]["sources"][0]["uri"], TEAM_SOURCE)
        self.assertTrue(packet.payload["lineage"][0]["replaces"].endswith("@1"))
        with self.assertRaises(AuthorizationError):
            store.context(workspace, project, REVOKED_TEAM_TOKEN, task="restore drill")

        with operator() as db:
            db.execute("UPDATE team_workspaces SET quarantined_at=clock_timestamp() WHERE workspace_id=%s", (workspace,))
        for operation in (
            lambda: store.context(workspace, project, owner, task="restore drill"),
            lambda: store.export_project(workspace, project, owner),
            lambda: store.issue_binding(workspace, owner, project=project, client="claude", actions=["read"]),
        ):
            with self.assertRaises(AuthorizationError):
                operation()


if __name__ == "__main__":
    unittest.main()
