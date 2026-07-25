from __future__ import annotations

import os
import sys
import unittest
import uuid
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.migrations import apply_migrations
from ninai_cloud.auth import AuthSettings, AuthenticationError, PATTokenVerifier, PrincipalResolver
from ninai_cloud.control_api import ControlIdentity, ControlService
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
            db.execute("DELETE FROM oauth_identities WHERE user_id=%s", (self.user,))
            for table in ("disclosure_logs", "idempotency_keys", "memory_relations", "memory_sources", "memories",
                          "personal_access_tokens",
                          "oauth_client_bindings", "client_scope_grants", "client_connections",
                          "projects", "workspace_members", "workspaces", "users"):
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
        self.assertEqual(
            [m.id for m in self.store.search(self.principal, "Which database does Nova use and why?")],
            [created.id],
        )
        self.store.record_disclosure(self.principal, tool_name="search", query="PostgreSQL", purpose="test",
                                     returned_memory_ids=[created.id])
        self.assertTrue(self.store.revoke_client(self.workspace, self.client, self.user))
        with self.assertRaises(AuthorizationError):
            self.store.get_memory(self.principal, created.id)

    def test_foreign_workspace_and_scope_are_not_visible(self) -> None:
        foreign = Principal(self.user, str(uuid.uuid4()), self.client)
        with self.assertRaises(AuthorizationError):
            self.store.search(foreign, "anything")

    def test_duplicate_aggregates_sources_and_expiry_is_surfaced(self) -> None:
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        common = dict(content="Nova uses PostgreSQL", memory_type="decision", scope_kind="project",
                      scope_id=self.project, project_id=self.project, activate=True,
                      valid_until=expires, freshness_policy="verify_weekly")
        first = self.store.create_memory(
            self.principal, **common, source_uri="claude://session/one", idempotency_key="duplicate-1")
        second = self.store.create_memory(
            self.principal, **common, source_uri="codex://session/two", idempotency_key="duplicate-2")
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.freshness_policy, "verify_weekly")
        self.assertEqual(second.valid_until, expires)
        self.assertFalse(second.is_expired)
        with self.psycopg.connect(DATABASE_URL, row_factory=self.__class__.dict_row) as db:
            sources = db.execute(
                "SELECT source_uri FROM memory_sources WHERE workspace_id=%s AND memory_id=%s ORDER BY source_uri",
                (self.workspace, first.id),
            ).fetchall()
        self.assertEqual([row["source_uri"] for row in sources],
                         ["claude://session/one", "codex://session/two"])

    def test_conflict_rejection_and_supersession_are_excluded_from_recall(self) -> None:
        first = self.store.create_memory(
            self.principal, content="Nova uses PostgreSQL for production", memory_type="decision",
            scope_kind="project", scope_id=self.project, project_id=self.project,
            source_uri="claude://decision/one", idempotency_key="conflict-1", activate=True)
        competing = self.store.create_memory(
            self.principal, content="Nova uses SQLite for production", memory_type="decision",
            scope_kind="project", scope_id=self.project, project_id=self.project,
            source_uri="codex://decision/two", idempotency_key="conflict-2", activate=True)
        self.assertEqual(competing.status, "conflicted")
        self.assertIsNotNone(competing.conflict_group_id)
        self.assertIsNone(self.store.get_memory(self.principal, first.id))
        self.assertEqual(self.store.search(self.principal, "Nova production"), [])

        rejected = self.store.transition(self.principal, competing.id, "rejected")
        self.assertEqual(rejected.status, "rejected")
        replacement = self.store.create_memory(
            self.principal, content="Nova production database is PostgreSQL 18", memory_type="fact",
            scope_kind="project", scope_id=self.project, project_id=self.project,
            source_uri="user://review/three", idempotency_key="replacement", activate=True)
        self.assertTrue(self.store.supersede(self.principal, first.id, replacement.id))
        fetched = self.store.get_memory(self.principal, replacement.id)
        self.assertEqual(fetched.supersedes_memory_id, first.id)
        with self.psycopg.connect(DATABASE_URL, row_factory=self.__class__.dict_row) as db:
            old = db.execute("SELECT status FROM memories WHERE id=%s", (first.id,)).fetchone()
            old_sources = db.execute("SELECT source_uri FROM memory_sources WHERE memory_id=%s", (first.id,)).fetchall()
        self.assertEqual(old["status"], "superseded")
        self.assertEqual([row["source_uri"] for row in old_sources], ["claude://decision/one"])

    def test_expired_memory_is_not_recalled(self) -> None:
        memory = self.store.create_memory(
            self.principal, content="Temporary launch flag is enabled", memory_type="event",
            scope_kind="project", scope_id=self.project, project_id=self.project,
            source_uri="codex://session/expiry", idempotency_key="expiry", activate=True,
            valid_until=datetime.now(timezone.utc) + timedelta(minutes=5))
        with self.psycopg.connect(DATABASE_URL) as db:
            db.execute("UPDATE memories SET valid_until=now()-interval '1 second' WHERE id=%s", (memory.id,))
        self.assertIsNone(self.store.get_memory(self.principal, memory.id))
        self.assertEqual(self.store.search(self.principal, "launch flag"), [])

    def test_pat_is_hashed_expires_and_observes_live_revocation(self) -> None:
        raw = "ninai_pat_" + uuid.uuid4().hex
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with self.psycopg.connect(DATABASE_URL) as db:
            db.execute("""INSERT INTO personal_access_tokens
                (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
                VALUES(%s,%s,%s,%s,%s,'Codex test',%s)""",
                (str(uuid.uuid4()), self.workspace, self.user, self.client, digest,
                 datetime.now(timezone.utc) + timedelta(minutes=5)))
        verifier = PATTokenVerifier(self.store._connection, "https://ninai.test/mcp")
        access = asyncio.run(verifier.verify_token(raw))
        self.assertIsNotNone(access)
        self.assertEqual(access.client_connection_id, self.client)
        with self.psycopg.connect(DATABASE_URL) as db:
            stored = db.execute("SELECT token_hash,last_used_at FROM personal_access_tokens WHERE token_hash=%s",
                                (digest,)).fetchone()
            self.assertEqual(stored[0], digest)
            self.assertIsNotNone(stored[1])
            db.execute("UPDATE personal_access_tokens SET revoked_at=now() WHERE token_hash=%s", (digest,))
        self.assertIsNone(asyncio.run(verifier.verify_token(raw)))

        expired_raw = "ninai_pat_" + uuid.uuid4().hex
        with self.psycopg.connect(DATABASE_URL) as db:
            db.execute("""INSERT INTO personal_access_tokens
                (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
                VALUES(%s,%s,%s,%s,%s,'Expired',%s)""",
                (str(uuid.uuid4()), self.workspace, self.user, self.client,
                 hashlib.sha256(expired_raw.encode()).hexdigest(),
                 datetime.now(timezone.utc) - timedelta(seconds=1)))
        self.assertIsNone(asyncio.run(verifier.verify_token(expired_raw)))

    def test_control_provisions_project_connection_grant_and_setup_metadata(self) -> None:
        control = ControlService(self.store._connection, self_hosted=True,
                                 public_mcp_url="http://localhost:8000/mcp")
        identity = ControlIdentity(self.user, self.workspace)
        project = control.create_project(identity, {"name": "Provisioned", "description": "Shared"})
        connection = control.create_connection(identity, {
            "provider": "anthropic", "client_type": "claude-code", "display_name": "Claude Code 2",
            # These must never override the verified identity.
            "workspace_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()),
        })
        raw = connection.pop("personal_access_token")
        grant = control.create_grant(identity, connection["id"], {
            "scope_kind": "project", "scope_id": project["id"],
            "can_read": True, "can_propose": True, "can_auto_activate": False,
        })
        tested = control.test_connection(identity, connection["id"])
        self.assertEqual(grant["scope_id"], project["id"])
        self.assertEqual(tested["metadata_json"]["connection_test"]["status"], "ready")
        with self.psycopg.connect(DATABASE_URL) as db:
            row = db.execute("""SELECT c.workspace_id,c.user_id,t.token_hash FROM client_connections c
                JOIN personal_access_tokens t ON t.client_connection_id=c.id AND t.workspace_id=c.workspace_id
                WHERE c.id=%s""", (connection["id"],)).fetchone()
        self.assertEqual(str(row[0]), self.workspace)
        self.assertEqual(str(row[1]), self.user)
        self.assertEqual(row[2], hashlib.sha256(raw.encode()).hexdigest())

    def test_authenticated_subject_can_create_workspace_without_body_identity(self) -> None:
        control = ControlService(self.store._connection)
        created = control.create_workspace(
            ControlIdentity(self.user, None, f"{self.user}@test.invalid", "Verified Owner"),
            {"name": "Second Workspace", "user_id": str(uuid.uuid4()),
             "workspace_id": str(uuid.uuid4())},
        )
        try:
            with self.psycopg.connect(DATABASE_URL) as db:
                row = db.execute("""SELECT w.owner_user_id,m.user_id,m.role FROM workspaces w
                    JOIN workspace_members m ON m.workspace_id=w.id WHERE w.id=%s""",
                    (created["id"],)).fetchone()
            self.assertEqual(str(row[0]), self.user)
            self.assertEqual(str(row[1]), self.user)
            self.assertEqual(row[2], "owner")
        finally:
            with self.psycopg.connect(DATABASE_URL) as db:
                db.execute("DELETE FROM workspace_members WHERE workspace_id=%s", (created["id"],))
                db.execute("DELETE FROM workspaces WHERE id=%s", (created["id"],))

    def test_auth0_subject_and_dynamic_client_map_to_internal_uuids(self) -> None:
        settings = AuthSettings(
            issuer="https://tenant.auth0.com/", audience="https://ninai.test/mcp",
            resource="https://ninai.test/mcp",
            jwks_uri="https://tenant.auth0.com/.well-known/jwks.json",
        )
        subject = "auth0|external-not-a-uuid"
        with self.psycopg.connect(DATABASE_URL) as db:
            db.execute("""INSERT INTO oauth_identities(id,issuer,subject,user_id,email)
                VALUES(%s,%s,%s,%s,%s)""", (str(uuid.uuid4()), settings.issuer,
                subject, self.user, f"{self.user}@test.invalid"))
        control = ControlService(self.store._connection, oauth_issuer=settings.issuer)
        connection = control.create_connection(ControlIdentity(self.user, self.workspace), {
            "provider": "openai", "client_type": "codex", "display_name": "Codex DCR",
            "oauth_client_id": "tpc_auth0_dynamic_client",
        })
        claims = {"sub": subject, "client_id": "tpc_auth0_dynamic_client",
                  settings.workspace_claim: self.workspace}
        principal = PrincipalResolver(self.store._connection, settings).resolve(claims)
        self.assertEqual(principal.user_id, self.user)
        self.assertEqual(principal.workspace_id, self.workspace)
        self.assertEqual(principal.client_connection_id, str(connection["id"]))
        self.assertTrue(control.revoke_connection(ControlIdentity(self.user, self.workspace),
                                                  connection["id"]))
        with self.assertRaisesRegex(AuthenticationError, "revoked"):
            PrincipalResolver(self.store._connection, settings).resolve(claims)


if __name__ == "__main__":
    unittest.main()
