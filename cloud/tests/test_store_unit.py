from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.migrations import migration_files
from ninai_cloud.postgres_store import (AuthorizationError, PostgresStore, Principal,
                                        _contains_secret, _looks_conflicting, _normalize,
                                        _request_hash)


class _Result:
    def __init__(self, row=None): self.row = row
    def fetchone(self): return self.row


class _ScopeDb:
    def __init__(self, *, project=True, member=True):
        self.project, self.member, self.calls = project, member, []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        if "FROM projects" in sql:
            return _Result({"exists": 1} if self.project else None)
        if "FROM workspace_members" in sql:
            return _Result({"exists": 1} if self.member else None)
        return _Result()


class HostedStoreUnitTest(unittest.TestCase):
    def test_normalization_and_hash_are_deterministic(self) -> None:
        self.assertEqual(_normalize("  Project\n Nova   decision "), "Project Nova decision")
        self.assertEqual(_request_hash({"b": 2, "a": 1}), _request_hash({"a": 1, "b": 2}))
        self.assertTrue(_contains_secret("Authorization: Bearer abcdefghijklmnopqrstuvwxyz"))

    def test_create_validates_before_opening_database(self) -> None:
        store = PostgresStore("unused", connect=lambda: self.fail("database opened"))
        with self.assertRaisesRegex(ValueError, "between 1 and 4,000"):
            store.create_memory(
                object(), content=" ", memory_type="fact", scope_kind="project",
                scope_id="x", source_uri="test://source", idempotency_key="key",
            )

    def test_core_migration_has_tenant_indexes_and_constraints(self) -> None:
        files = migration_files()
        self.assertEqual([path.name for path in files], [
            "0001_hosted_core.sql", "0002_personal_access_tokens.sql",
            "0003_memory_lifecycle.sql", "0004_oauth_identity_mapping.sql",
            "0005_tenant_integrity.sql",
        ])
        sql = files[0].read_text(encoding="utf-8")
        for table in (
            "users", "workspaces", "workspace_members", "projects", "client_connections",
            "client_scope_grants", "memories", "memory_sources", "memory_relations",
            "disclosure_logs", "memory_feedback", "idempotency_keys",
        ):
            self.assertIn(f"CREATE TABLE {table}", sql)
        self.assertIn("memories_workspace_search_idx", sql)
        self.assertIn("PRIMARY KEY(workspace_id,client_connection_id,idempotency_key)", sql)
        pat_sql = files[1].read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE personal_access_tokens", pat_sql)
        self.assertIn("token_hash char(64) NOT NULL UNIQUE", pat_sql)
        self.assertNotIn("token text", pat_sql.lower())
        self.assertIn("expires_at timestamptz NOT NULL", pat_sql)
        self.assertIn("revoked_at timestamptz", pat_sql)
        lifecycle_sql = files[2].read_text(encoding="utf-8")
        self.assertIn("'conflicted'", lifecycle_sql)
        self.assertIn("'rejected'", lifecycle_sql)
        self.assertIn("freshness_policy", lifecycle_sql)
        integrity_sql = files[4].read_text(encoding="utf-8")
        self.assertIn("FOREIGN KEY (workspace_id, client_connection_id, user_id)", integrity_sql)

    def test_scope_targets_cannot_escape_or_mix_projects(self) -> None:
        workspace = "11111111-1111-4111-8111-111111111111"
        project = "22222222-2222-4222-8222-222222222222"
        other = "33333333-3333-4333-8333-333333333333"
        principal = Principal("44444444-4444-4444-8444-444444444444", workspace, "client")
        db = _ScopeDb()

        self.assertEqual(
            PostgresStore._validate_scope_target(db, principal, "project", project, None),
            project,
        )
        with self.assertRaisesRegex(AuthorizationError, "project_id must match"):
            PostgresStore._validate_scope_target(db, principal, "project", project, other)
        with self.assertRaisesRegex(AuthorizationError, "authenticated workspace"):
            PostgresStore._validate_scope_target(db, principal, "workspace", other, None)
        with self.assertRaisesRegex(ValueError, "must be UUIDs"):
            PostgresStore._validate_scope_target(db, principal, "project", "not-a-uuid", None)

    def test_project_and_user_scopes_must_exist_in_workspace(self) -> None:
        workspace = "11111111-1111-4111-8111-111111111111"
        target = "22222222-2222-4222-8222-222222222222"
        principal = Principal("44444444-4444-4444-8444-444444444444", workspace, "client")
        with self.assertRaisesRegex(AuthorizationError, "Project scope is unavailable"):
            PostgresStore._validate_scope_target(
                _ScopeDb(project=False), principal, "project", target, None
            )
        with self.assertRaisesRegex(AuthorizationError, "active member"):
            PostgresStore._validate_scope_target(
                _ScopeDb(member=False), principal, "user", target, None
            )

    def test_conflict_signal_is_conservative(self) -> None:
        self.assertTrue(_looks_conflicting("Nova uses PostgreSQL for production", "Nova uses SQLite for production"))
        self.assertFalse(_looks_conflicting("Nova uses PostgreSQL", "The website is blue"))
        self.assertFalse(_looks_conflicting("same exact claim", "same exact claim"))


if __name__ == "__main__":
    unittest.main()
