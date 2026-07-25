from __future__ import annotations

import hashlib
import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.bootstrap import bootstrap


DATABASE_URL = os.environ.get("NINAI_TEST_DATABASE_URL", "")


@unittest.skipUnless(DATABASE_URL, "NINAI_TEST_DATABASE_URL is not configured")
class BootstrapIntegrationTest(unittest.TestCase):
    def test_creates_distinct_clients_grants_and_hash_only_tokens(self) -> None:
        import psycopg
        result = bootstrap(
            DATABASE_URL, email=f"bootstrap-{uuid.uuid4()}@test.invalid",
            workspace_name="PAT Test", project_name="Shared Test", expires_days=1,
        )
        self.addCleanup(self._cleanup, result["workspace"], result["user"])
        self.assertNotEqual(result["tokens"]["claude"], result["tokens"]["codex"])
        with psycopg.connect(DATABASE_URL) as db:
            clients = db.execute(
                "SELECT provider,client_type FROM client_connections WHERE workspace_id=%s ORDER BY provider",
                (result["workspace"],),
            ).fetchall()
            self.assertEqual(clients, [("anthropic", "claude-code"), ("openai", "codex")])
            grants = db.execute(
                "SELECT count(*) FROM client_scope_grants WHERE workspace_id=%s AND scope_id=%s "
                "AND can_read AND can_propose AND can_auto_activate",
                (result["workspace"], result["project"]),
            ).fetchone()[0]
            self.assertEqual(grants, 2)
            hashes = {row[0] for row in db.execute(
                "SELECT token_hash FROM personal_access_tokens WHERE workspace_id=%s",
                (result["workspace"],),
            ).fetchall()}
        self.assertEqual(hashes, {
            hashlib.sha256(result["tokens"]["claude"].encode()).hexdigest(),
            hashlib.sha256(result["tokens"]["codex"].encode()).hexdigest(),
        })
        self.assertTrue(all(raw not in hashes for raw in result["tokens"].values()))

    @staticmethod
    def _cleanup(workspace_id: str, user_id: str) -> None:
        import psycopg
        with psycopg.connect(DATABASE_URL) as db:
            for table in ("personal_access_tokens", "client_scope_grants", "client_connections", "projects"):
                db.execute(f"DELETE FROM {table} WHERE workspace_id=%s", (workspace_id,))
            db.execute("DELETE FROM workspace_members WHERE workspace_id=%s", (workspace_id,))
            db.execute("DELETE FROM workspaces WHERE id=%s", (workspace_id,))
            db.execute("DELETE FROM users WHERE id=%s", (user_id,))


if __name__ == "__main__":
    unittest.main()
