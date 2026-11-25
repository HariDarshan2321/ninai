from __future__ import annotations

import os
from uuid import uuid4
import unittest

from ninai_cloud.migrations import apply_migrations


DATABASE_URL = os.environ.get("NINAI_TEST_DATABASE_URL", "")


@unittest.skipUnless(DATABASE_URL, "NINAI_TEST_DATABASE_URL is not configured")
class TeamSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import psycopg

        cls.psycopg = psycopg
        apply_migrations(DATABASE_URL)

    def setUp(self) -> None:
        self.db = self.psycopg.connect(DATABASE_URL)
        self.addCleanup(self.db.close)
        self.user, self.workspace, self.project = self.seed_workspace()
        self.other_user, self.other_workspace, self.other_project = self.seed_workspace()
        self.set_tenant(self.workspace)

    def set_tenant(self, workspace) -> None:
        self.db.execute("SELECT set_config('ninai.team_workspace_id', %s, true)", (str(workspace),))

    def seed_workspace(self):
        user, workspace, project = (uuid4() for _ in range(3))
        self.db.execute("INSERT INTO users(id,email,display_name) VALUES (%s,%s,'Team test')",
                        (user, f"{user}@example.invalid"))
        self.db.execute("INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES (%s,'Team test',%s,%s)",
                        (workspace, str(workspace), user))
        self.set_tenant(workspace)
        self.db.execute("INSERT INTO team_workspaces(workspace_id) VALUES (%s)", (workspace,))
        self.db.execute("INSERT INTO team_members(workspace_id,user_id,role) VALUES (%s,%s,'owner')",
                        (workspace, user))
        self.db.execute("INSERT INTO team_projects(id,workspace_id,name,slug) VALUES (%s,%s,'Team test','team')",
                        (project, workspace))
        return user, workspace, project

    def test_runtime_role_scope_denies_missing_and_other_tenant(self) -> None:
        from psycopg import sql

        role = sql.Identifier(f"ninai_team_test_{uuid4().hex}")
        try:
            with self.db.transaction():
                self.db.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS").format(role))
        except self.psycopg.errors.InsufficientPrivilege:
            self.skipTest("isolated test database role cannot create a test runtime role")
        self.db.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(role))
        self.db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        self.db.execute(sql.SQL("GRANT SELECT, INSERT ON team_members TO {}").format(role))
        self.db.execute(sql.SQL("SET LOCAL ROLE {}").format(role))

        self.assertTrue(self.db.execute("SELECT row_security_active('team_members')").fetchone()[0])
        self.set_tenant("")
        self.assertEqual(self.db.execute("SELECT user_id FROM team_members").fetchall(), [])
        self.set_tenant(self.workspace)
        self.assertEqual(self.db.execute("SELECT user_id FROM team_members").fetchall(), [(self.user,)])
        with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), self.db.transaction():
            self.db.execute("INSERT INTO team_members(workspace_id,user_id,role) VALUES (%s,%s,'member')",
                            (self.other_workspace, self.user))
        self.set_tenant(self.other_workspace)
        self.assertEqual(self.db.execute("SELECT user_id FROM team_members").fetchall(), [(self.other_user,)])

    def test_team_membership_and_project_references_are_independent(self) -> None:
        self.db.execute("INSERT INTO workspace_members(workspace_id,user_id,role) VALUES (%s,%s,'admin')",
                        (self.workspace, self.other_user))
        legacy_project = uuid4()
        self.db.execute("INSERT INTO projects(id,workspace_id,name,slug) VALUES (%s,%s,'Legacy test','legacy')",
                        (legacy_project, self.workspace))
        insert = "INSERT INTO team_project_members(workspace_id,project_id,user_id,role) VALUES (%s,%s,%s,'member')"
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation), self.db.transaction():
            self.db.execute(insert, (self.workspace, self.project, self.other_user))
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation), self.db.transaction():
            self.db.execute(insert, (self.workspace, self.other_project, self.user))
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation), self.db.transaction():
            self.db.execute(insert, (self.workspace, legacy_project, self.user))
        self.db.execute(insert, (self.workspace, self.project, self.user))
        self.assertEqual(self.db.execute("SELECT role FROM team_project_members WHERE workspace_id=%s",
                                         (self.workspace,)).fetchall(), [("member",)])

    def create_decision(self, topic="release"):
        return self.db.execute("""INSERT INTO team_decisions(workspace_id,project_id,created_by_user_id,visibility,topic)
            VALUES (%s,%s,%s,'team',%s) RETURNING id""", (self.workspace, self.project, self.user, topic)).fetchone()[0]

    def add_version(self, decision, version=1):
        self.db.execute("""INSERT INTO team_decision_versions
            (workspace_id,project_id,decision_id,version,rule,proposed_by_user_id)
            VALUES (%s,%s,%s,%s,'Use a rollback step',%s)""",
                        (self.workspace, self.project, decision, version, self.user))

    def add_source(self, decision, version=1, key="fixture/team/pull/1"):
        return self.db.execute("""INSERT INTO team_decision_sources
            (workspace_id,project_id,decision_id,version,provider,resource_key,source_url)
            VALUES (%s,%s,%s,%s,'github',%s,%s) RETURNING id""",
            (self.workspace, self.project, decision, version, key, f"https://github.example.invalid/{key}")).fetchone()[0]

    def pin(self, decision, source, version=1):
        self.db.execute("""INSERT INTO team_source_pins(workspace_id,project_id,decision_id,version,source_id,fingerprint)
            VALUES (%s,%s,%s,%s,%s,%s)""", (self.workspace, self.project, decision, version, source, "a" * 64))

    def transition(self, decision, state, version=1):
        return self.db.execute("""INSERT INTO team_decision_events
            (workspace_id,project_id,decision_id,version,state,actor_user_id)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING sequence""",
            (self.workspace, self.project, decision, version, state, self.user)).fetchone()[0]

    def test_lifecycle_and_evidence_are_append_only(self) -> None:
        decision = self.create_decision()
        self.add_version(decision)
        source = self.add_source(decision)
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.transition(decision, "approved")
        proposed = self.transition(decision, "proposed")
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.transition(decision, "approved")
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.add_source(decision, key="fixture/team/pull/2")
        self.pin(decision, source)
        approved = self.transition(decision, "approved")
        self.assertGreater(approved, proposed)
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute("UPDATE team_decision_versions SET rule='Changed after review' WHERE decision_id=%s",
                            (decision,))
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute("UPDATE team_source_pins SET fingerprint=%s WHERE source_id=%s", ("b" * 64, source))
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute("UPDATE team_decision_events SET state='revoked' WHERE decision_id=%s", (decision,))
        self.transition(decision, "revoked")
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.transition(decision, "approved")

    def test_supersession_requires_order_and_same_topic(self) -> None:
        first = self.create_decision()
        second = self.create_decision()
        other_topic = self.create_decision("payments")
        for decision in (first, second, other_topic):
            self.add_version(decision)
            source = self.add_source(decision)
            self.transition(decision, "proposed")
            self.pin(decision, source)
        edge = """INSERT INTO team_supersessions
            (workspace_id,project_id,decision_id,version,replaces_decision_id,replaces_version)
            VALUES (%s,%s,%s,1,%s,1)"""
        self.transition(second, "approved")
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute(edge, (self.workspace, self.project, first, second))
        self.transition(first, "approved")
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute(edge, (self.workspace, self.project, other_topic, first))
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.transition(first, "replaced")

    def test_supersession_edge_cannot_commit_without_both_transitions(self) -> None:
        first = self.create_decision()
        second = self.create_decision()
        for decision in (first, second):
            self.add_version(decision)
            source = self.add_source(decision)
            self.transition(decision, "proposed")
            self.pin(decision, source)
        self.transition(first, "approved")
        edge = """INSERT INTO team_supersessions
            (workspace_id,project_id,decision_id,version,replaces_decision_id,replaces_version)
            VALUES (%s,%s,%s,1,%s,1)"""
        with self.assertRaises(self.psycopg.errors.CheckViolation), self.db.transaction():
            self.db.execute(edge, (self.workspace, self.project, second, first))
            self.db.execute("SET CONSTRAINTS team_supersession_commit IMMEDIATE")
        self.db.execute(edge, (self.workspace, self.project, second, first))
        self.transition(first, "replaced")
        self.transition(second, "approved")
        self.db.execute("SET CONSTRAINTS team_supersession_commit IMMEDIATE")
