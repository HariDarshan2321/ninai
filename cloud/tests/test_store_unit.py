from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.migrations import migration_files
from ninai_cloud.postgres_store import PostgresStore, _contains_secret, _normalize, _request_hash


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
        self.assertEqual([path.name for path in files],
                         ["0001_hosted_core.sql", "0002_personal_access_tokens.sql"])
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


if __name__ == "__main__":
    unittest.main()
