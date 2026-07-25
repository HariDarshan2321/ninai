from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.migrations import apply_migrations
from ninai_cloud.postgres_store import AuthorizationError, IdempotencyConflict, PostgresStore, Principal


DATABASE_URL = os.environ.get("NINAI_TEST_DATABASE_URL", "")


@unittest.skipUnless(DATABASE_URL, "NINAI_TEST_DATABASE_URL is not configured")
class PostgresLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import psycopg
        from psycopg.rows import dict_row

        cls.psycopg = psycopg
        cls.dict_row = dict_row
        apply_migrations(DATABASE_URL)

    def setUp(self) -> None:
        self.user = str(uuid.uuid4())
        self.workspace = str(uuid.uuid4())
        self.project = str(uuid.uuid4())
        self.client = str(uuid.uuid4())
        self.principal = Principal(self.user, self.workspace, self.client)
        with self.psycopg.connect(DATABASE_URL) as db:
            db.execute("INSERT INTO users(id,email,display_name) VALUES(%s,%s,'Test')", (self.user, f"{self.user}@test.invalid"))
            db.execute("INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES(%s,'Test',%s,%s)", (self.workspace, self.workspace, self.user))
            db.execute("INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')", (self.workspace, self.user))
            db.execute("INSERT INTO projects(id,workspace_id,name,slug) VALUES(%s,%s,'Nova','nova')", (self.project, self.workspace))
            db.execute("""INSERT INTO client_connections(id,workspace_id,user_id,provider,client_type,display_name)
                          VALUES(%s,%s,%s,'openai','codex','Codex')""", (self.client, self.workspace, self.user))
            db.execute("""INSERT INTO client_scope_grants(id,workspace_id,client_connection_id,scope_kind,scope_id,
                          can_read,can_propose,can_auto_activate,created_by_user_id)
                          VALUES(%s,%s,%s,'project',%s,true,true,true,%s)""",
                       (str(uuid.uuid4()), self.workspace, self.client, self.project, self.user))
        self.store = PostgresStore(DATABASE_URL)

    def tearDown(self) -> None:
        with self.psycopg.connect(DATABASE_URL) as db:
            for table in ("disclosure_logs", "idempotency_keys", "memory_relations", "memory_sources", "memories",
                          "client_scope_grants", "client_connections", "projects", "workspace_members", "workspaces", "users"):
                db.execute(f"DELETE FROM {table} WHERE workspace_id=%s" if table not in {"users", "workspaces"} else
                           ("DELETE FROM workspaces WHERE id=%s" if table == "workspaces" else "DELETE FROM users WHERE id=%s"),
                           (self.workspace if table != "users" else self.user,))

    def test_lifecycle_idempotency_disclosure_and_revocation(self) -> None:
        args = dict(content="Nova uses PostgreSQL", memory_type="decision", scope_kind="project",
                    scope_id=self.project, project_id=self.project, source_uri="claude://session/1",
                    idempotency_key="request-1", activate=True)
        created = self.store.create_memory(self.principal, **args)
        repeated = self.store.create_memory(self.principal, **args)
        self.assertEqual(created.id, repeated.id)
        with self.assertRaises(IdempotencyConflict):
            self.store.create_memory(self.principal, **{**args, "content": "Different"})
        self.assertEqual(self.store.get_memory(self.principal, created.id).source_uri, "claude://session/1")
        self.assertEqual([m.id for m in self.store.search(self.principal, "PostgreSQL")], [created.id])
        self.store.record_disclosure(self.principal, tool_name="search", query="PostgreSQL", purpose="test",
                                     returned_memory_ids=[created.id])
        self.assertTrue(self.store.revoke_client(self.workspace, self.client, self.user))
        with self.assertRaises(AuthorizationError):
            self.store.get_memory(self.principal, created.id)

    def test_foreign_workspace_and_scope_are_not_visible(self) -> None:
        foreign = Principal(self.user, str(uuid.uuid4()), self.client)
        with self.assertRaises(AuthorizationError):
            self.store.search(foreign, "anything")


if __name__ == "__main__":
    unittest.main()
