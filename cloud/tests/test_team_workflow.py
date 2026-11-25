from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import json
import subprocess
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from ninai_cloud.migrations import apply_migrations
from ninai_cloud.postgres_store import AuthorizationError
from ninai_cloud.rate_limit import RateLimitError
from ninai_cloud.team_sources import SourceAccess, SourceProof, source_fingerprint
from ninai_cloud.team_store import TeamHuman, TeamStore


DATABASE_URL = os.environ.get("NINAI_TEST_DATABASE_URL", "")
ISSUER = "https://identity.example.invalid/"
SOURCE_LINK = "https://github.com/synthetic/payments/pull/37"
TASK = {"task": "Add refund idempotency", "paths": ["billing:src/refund.py"]}


class FixtureVerifier:
    def __init__(self):
        self.denied = set()
        self.denied_resources = set()
        self.checked_resources = []
        self.pause = None

    def verify(self, request):
        start = datetime.now(timezone.utc)
        if self.pause is not None and request.binding_id:
            started, released = self.pause
            started.set()
            if not released.wait(10):
                raise RuntimeError("Fixture release order timed out")
        self.checked_resources.append(request.reference.resource_key)
        if request.user_id in self.denied or request.reference.resource_key in self.denied_resources:
            return SourceProof(request, start, SourceAccess.DENIED)
        fingerprint = source_fingerprint(request.reference.provider, request.reference.resource_key, "fixture-v1")
        return SourceProof(request, start, SourceAccess.GRANTED, fingerprint)


@unittest.skipUnless(DATABASE_URL, "Set an isolated test database URL")
class TeamWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from ninai_cloud.team_runtime import verify_team_runtime

        apply_migrations(DATABASE_URL)
        cls.connect = staticmethod(lambda: psycopg.connect(DATABASE_URL, row_factory=dict_row))
        cls.role = f"ninai_team_tests_{uuid4().hex}"
        with cls.connect() as db:
            db.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS").format(sql.Identifier(cls.role)))
            password = uuid4().hex
            db.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(cls.role), sql.Literal(password)))
            grants = (Path(__file__).resolve().parents[1] / "team_runtime_grants.sql").read_text()
            body = grants[grants.index("BEGIN;") + len("BEGIN;"):grants.rindex("COMMIT;")]
            db.execute(body.replace(':"team_runtime_role"', sql.Identifier(cls.role).as_string(db)))
        cls.runtime_connect = staticmethod(lambda: psycopg.connect(
            DATABASE_URL, user=cls.role, password=password, row_factory=dict_row))
        verify_team_runtime(cls.runtime_connect, cls.connect)
        with unittest.TestCase().assertRaises(RuntimeError):
            verify_team_runtime(cls.connect, cls.connect)

    @classmethod
    def tearDownClass(cls):
        from psycopg import sql

        with cls.connect() as db:
            db.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(cls.role)))
            db.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(cls.role)))

    def setUp(self):
        self.verifier = FixtureVerifier()
        self.store = TeamStore(self.runtime_connect, verifier=self.verifier)
        self.workspace = str(uuid4())
        self.owner = self._user()
        self.member = self._user()
        self.stranger = self._user()
        with self.connect() as db:
            db.execute("INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES(%s,'Team fixture',%s,%s)",
                       (self.workspace, self.workspace, self.owner.user_id))
            db.execute("INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')",
                       (self.workspace, self.owner.user_id))
        self.store.enable(self.workspace, self.owner)
        self.project = self.store.create_project(self.workspace, self.owner, name="Billing")["project_id"]
        self.store.assign_project(self.workspace, self.owner, project=self.project, user=self.owner.user_id,
                                  role="maintainer")

    def _user(self):
        user_id = str(uuid4())
        user = TeamHuman(user_id, ISSUER, f"fixture|{user_id}", int(time.time()) + 1800)
        with self.connect() as db:
            db.execute("INSERT INTO users(id,email,display_name) VALUES(%s,%s,'Team fixture')",
                       (user_id, f"{user_id}@example.invalid"))
            db.execute("INSERT INTO oauth_identities(id,issuer,subject,user_id) VALUES(%s,%s,%s,%s)",
                       (uuid4(), ISSUER, user.subject, user.user_id))
        return user

    def _invite(self):
        return self.store.invite(self.workspace, self.owner, issuer=ISSUER,
                                 subject=self.member.subject)["invitation_token"]

    def _member(self):
        self.store.accept_invite(self.workspace, self.member, token=self._invite())
        self.store.assign_project(self.workspace, self.owner, project=self.project, user=self.member.user_id)

    def _binding(self, user, client, actions=None):
        return self.store.issue_binding(self.workspace, user, project=self.project, client=client,
                                        actions=["read"] if actions is None else actions)

    def _propose(self, credential, rule="Write a refund idempotency key.", **fields):
        data = dict(topic="refund idempotency", rule=rule, paths=["billing:src"], links=[SOURCE_LINK])
        return self.store.propose(self.workspace, self.project, credential, **{**data, **fields})

    def _review(self, proposal, **fields):
        return self.store.review(self.workspace, self.project, self.owner, decision=proposal["decision_id"],
                                 version=proposal["version"], **fields)

    def _recall(self, credential):
        return self.store.context(self.workspace, self.project, credential, **TASK)

    def test_two_repository_checkouts_share_cloud_handoffs_and_approved_guidance(self):
        import httpx
        from mcp.shared.memory import create_connected_server_and_client_session
        from starlette.applications import Starlette
        from starlette.routing import Route

        from ninai_cloud.auth import AuthSettings
        from ninai_cloud.team_api import TeamApp
        from ninai_cloud.team_client import TeamClient, create_stdio_bridge
        from ninai_cloud.team_session import session_start

        self._member()
        repository = "synthetic/payments"
        self.store.connect_repository(self.workspace, self.owner, project=self.project, repository=repository)
        with self.assertRaises(AuthorizationError):
            self.store.connect_repository(self.workspace, self.owner, project=self.project, repository="other/repo")
        with self.assertRaises(AuthorizationError):
            self.store.connect_repository(self.workspace, self.member, project=self.project, repository=repository)
        self.assertEqual(self.store.overview(self.workspace, self.member)["projects"][0]["repository"], repository)

        alice = self._binding(self.owner, "claude", ["read", "propose", "read-handoffs", "publish-handoff"])
        bob = self._binding(self.member, "codex", ["read", "read-handoffs"])
        legacy = self._binding(self.member, "legacy-read", ["read"])
        origin = "https://ninai.example.invalid"
        settings = AuthSettings(ISSUER, "test", origin, ISSUER + ".well-known/jwks.json", control_client_id="dashboard")
        app = TeamApp(self.store, None, settings)
        transport = httpx.ASGITransport(Starlette(routes=[
            Route("/api/team-assistant/{tail:path}", app.handle, methods=["POST"]),
        ]))

        def client(binding, repo=repository):
            return TeamClient(origin, self.workspace, self.project, binding["token"],
                              repository=repo, transport=transport)

        async def exercise(alice_path, bob_path, unrelated_path):
            payload = {"request_key": str(uuid4()), "topic": "Refund rollout", "status": "working",
                       "summary": "Checked the retry path.", "next_step": "Confirm the queue owner."}
            async with create_connected_server_and_client_session(create_stdio_bridge(client(alice))) as session:
                published = await session.call_tool("team_publish_handoff", payload)
                self.assertFalse(published.isError, published)
                handoff_id = json.loads(published.content[0].text)["id"]
                retry = await session.call_tool("team_publish_handoff", payload)
                self.assertEqual(json.loads(retry.content[0].text)["id"], handoff_id)
                changed = await session.call_tool("team_publish_handoff", {**payload, "status": "done"})
                self.assertTrue(changed.isError)
                proposal = await session.call_tool("team_propose_decision", {
                    "topic": "refund idempotency", "rule": "Persist refund idempotency keys before calls.",
                    "paths": ["billing:src"], "links": [SOURCE_LINK],
                })
                self.assertFalse(proposal.isError, proposal)
                proposed = json.loads(proposal.content[0].text)

            def event(cwd):
                return {"hook_event_name": "SessionStart", "cwd": str(cwd)}

            async def brief(binding, cwd):
                result = await session_start(event(cwd), client(binding))
                message = result["hookSpecificOutput"]["additionalContext"]
                return json.loads(message.split("\n", 1)[1])

            self.assertIsNone(await session_start(event(unrelated_path), client(bob)))
            first = await brief(bob, bob_path)
            self.assertEqual(first["decisions"], {"outcome": "empty"})
            self.assertEqual(first["handoffs"]["items"][0]["next_step"], "Confirm the queue owner.")
            self.assertTrue(first["handoffs"]["items"][0]["source_uri"].endswith(handoff_id))
            self.assertTrue((await client(legacy).handoffs()).isError)
            self.assertTrue((await client(bob, "other/repo").handoffs()).isError)
            self.assertTrue((await client(bob).publish_handoff(**payload)).isError)

            self._review(proposed)
            current = await brief(bob, bob_path)
            self.assertEqual(current["decisions"]["current"][0]["scope_paths"], ["billing:src"])
            self.assertEqual(current["decisions"]["current"][0]["sources"][0]["uri"], SOURCE_LINK)
            self.assertEqual((await brief(alice, alice_path))["handoffs"], first["handoffs"])
            self.verifier.denied.add(self.member.user_id)
            denied_source = await brief(bob, bob_path)
            self.assertEqual(denied_source["decisions"], {"outcome": "empty"})
            self.assertEqual(denied_source["handoffs"], first["handoffs"])

            latest = await client(alice).publish_handoff(**{**payload, "request_key": str(uuid4()), "status": "done"})
            self.assertFalse(latest.isError)
            self.assertEqual([row["status"] for row in (await brief(bob, bob_path))["handoffs"]["items"]], ["done"])
            self.store.update_binding(self.workspace, self.member, project=self.project,
                                      binding=bob["binding_id"], operation="revoke")
            self.assertEqual(await brief(bob, bob_path), {
                "handoffs": {"status": "unavailable"}, "decisions": {"status": "unavailable"},
            })

        with tempfile.TemporaryDirectory() as directory:
            checkouts = []
            for name, remote in (
                ("alice", "https://github.com/Synthetic/Payments.git"),
                ("bob", "git@github.com:synthetic/payments.git"),
                ("unrelated", "https://github.com/other/repo"),
            ):
                checkout = Path(directory) / name
                subprocess.run(["git", "init", "-q", checkout], check=True)
                subprocess.run(["git", "-C", checkout, "remote", "add", "origin", remote], check=True)
                checkouts.append(checkout)
            asyncio.run(exercise(*checkouts))

    def test_create_quota_serializes_and_shares_sponsor_budget_across_bindings(self):
        self._member()
        first = self._binding(self.member, "claude", ["propose"])
        second = self._binding(self.member, "codex", ["propose"])

        def propose(token):
            try:
                return self._propose(token)["status"]
            except RateLimitError as error:
                self.assertEqual(error.retry_after, 3600)
                return "limited"

        with patch.dict("ninai_cloud.team_store.HOURLY_CREATE_LIMITS", {"propose": 1}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(propose, (first["token"], second["token"])))
            self.assertCountEqual(results, ["proposed", "limited"])
            with self.assertRaises(RateLimitError):
                self._propose(self.member)
            self.assertEqual(self._propose(self.owner)["status"], "proposed")
            self.store.update_binding(self.workspace, self.member, project=self.project,
                                      binding=first["binding_id"], operation="revoke")
            with self.assertRaises(AuthorizationError):
                self._propose(first["token"])

    def test_known_revoked_denial_is_coalesced_and_unknown_denial_does_not_audit(self):
        self._member()
        binding = self._binding(self.member, "codex")
        self.store.update_binding(self.workspace, self.member, project=self.project,
                                  binding=binding["binding_id"], operation="revoke")

        def attempt(credential):
            with self.assertRaises(AuthorizationError) as denied:
                self._recall(credential)
            return str(denied.exception)

        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(attempt, [binding["token"]] * 15 + ["x" * 43]))
        self.assertEqual(len(set(results)), 1)
        with self.connect() as db:
            events = db.execute("""
                SELECT project_id,actor_user_id,binding_id,action,reason,request_id
                FROM team_audit_events WHERE workspace_id=%s AND outcome='denied'
            """, (self.workspace,)).fetchall()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(str(event["project_id"]), self.project)
        self.assertEqual(str(event["actor_user_id"]), self.member.user_id)
        self.assertEqual(str(event["binding_id"]), binding["binding_id"])
        self.assertEqual((event["action"], event["reason"]), ("read", "policy"))
        self.assertTrue(event["request_id"])

    def test_runtime_rejects_policy_helper_and_privilege_drift(self):
        from psycopg import sql
        from ninai_cloud.team_runtime import WORKSPACE_FUNCTION, verify_team_runtime

        role = sql.Identifier(self.role).as_string()
        scope = "(workspace_id = (SELECT public.team_current_workspace()))"
        policy = "team_workspace_scope ON public.team_members"
        helper = "public.team_current_workspace()"
        altered_helper = WORKSPACE_FUNCTION.replace("ninai.team_workspace_id", "ninai.wrong_fixture_key")
        mutations = (
            (f"ALTER POLICY {policy} USING (true)",
             f"ALTER POLICY {policy} USING {scope}", "row policies"),
            (f"ALTER POLICY {policy} WITH CHECK (true)",
             f"ALTER POLICY {policy} WITH CHECK {scope}", "row policies"),
            (f"ALTER POLICY {policy} TO {role}",
             f"ALTER POLICY {policy} TO PUBLIC", "row policies"),
            (f"ALTER FUNCTION {helper} SECURITY DEFINER",
             f"ALTER FUNCTION {helper} SECURITY INVOKER", "scope function"),
            (f"ALTER FUNCTION {helper} SET search_path TO public",
             f"ALTER FUNCTION {helper} SET search_path TO pg_catalog", "scope function"),
            (altered_helper, WORKSPACE_FUNCTION, "scope function"),
            ("ALTER TABLE public.team_members NO FORCE ROW LEVEL SECURITY",
             "ALTER TABLE public.team_members FORCE ROW LEVEL SECURITY", "forced PostgreSQL RLS"),
            (f"GRANT SELECT (email) ON public.users TO {role}",
             f"REVOKE SELECT (email) ON public.users FROM {role}", "column privileges"),
            (f"GRANT UPDATE (rule) ON public.team_decision_versions TO {role}",
             f"REVOKE UPDATE (rule) ON public.team_decision_versions FROM {role}", "column privileges"),
            (f"GRANT pg_read_all_data TO {role}", f"REVOKE pg_read_all_data FROM {role}", "unprivileged PostgreSQL login"),
            (f"ALTER ROLE {role} BYPASSRLS", f"ALTER ROLE {role} NOBYPASSRLS", "unprivileged PostgreSQL login"),
        )
        for modify, restore, expected_error in mutations:
            with self.subTest(modify=modify):
                with self.connect() as db:
                    db.execute(modify)
                try:
                    with self.assertRaisesRegex(RuntimeError, expected_error):
                        verify_team_runtime(self.runtime_connect, self.connect)
                finally:
                    with self.connect() as db:
                        db.execute(restore)
        verify_team_runtime(self.runtime_connect, self.connect)

    def test_runtime_requires_the_same_database_and_distinct_login(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from ninai_cloud.team_runtime import verify_team_runtime

        db_name = f"ninai_other_{uuid4().hex}"
        with psycopg.connect(DATABASE_URL, autocommit=True) as db:
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            try:
                def other_connect():
                    return psycopg.connect(DATABASE_URL, dbname=db_name, row_factory=dict_row)

                with self.assertRaisesRegex(RuntimeError, "same PostgreSQL database"):
                    verify_team_runtime(self.runtime_connect, other_connect)
                with self.assertRaisesRegex(RuntimeError, "separate logins"):
                    verify_team_runtime(self.runtime_connect, self.runtime_connect)
            finally:
                db.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(db_name)))

    def test_fresh_provider_proof_uses_the_process_clock(self):
        proposal = self._propose(self.owner)
        binding = self._binding(self.owner, "codex")
        database_clock = self.store._clock

        def lagging_database_clock(db):
            return database_clock(db) - timedelta(seconds=30)

        with patch.object(self.store, "_clock", side_effect=lagging_database_clock):
            self.assertEqual(len(self.store.proposals(self.workspace, self.project, self.owner)["items"]), 1)
            self._review(proposal)
            self.assertEqual(self._recall(binding["token"]).outcome, "packet")
            self.assertEqual(len(self.store.export_project(self.workspace, self.project, self.owner)["items"]), 1)
            self.assertTrue(self.store.export_project_audit(self.workspace, self.project, self.owner)["items"])

    def test_mixed_assistants_share_exact_current_version_and_conflict(self):
        self._member()
        claude = self._binding(self.member, "claude")
        codex = self._binding(self.member, "codex", ["read", "view-history"])
        proposal = self._propose(self.owner)
        self.assertEqual(self._recall(claude["token"]).outcome, "empty")
        self.assertEqual(self.store.proposals(self.workspace, self.project, self.owner)["items"][0]["status"],
                         "proposed")
        self._review(proposal)
        first = self._recall(claude["token"]).payload
        self.assertEqual(first, self._recall(codex["token"]).payload)
        version = first["current"][0]
        self.assertEqual(version["version_id"], f"{proposal['decision_id']}@1")
        self.assertEqual(version["sources"][0]["uri"], SOURCE_LINK)
        self.assertEqual(version["rationale_status"], "undocumented")

        edited = self._propose(self.owner, "Persist the refund idempotency key before sending.",
                               decision=proposal["decision_id"])
        self.assertEqual(edited["version"], 2)
        self._review(edited, replaces=proposal["decision_id"], replaces_version=proposal["version"])
        claude_current = self._recall(claude["token"]).payload
        codex_current = self._recall(codex["token"]).payload
        self.assertEqual(claude_current["current"][0]["version"], 2)
        self.assertNotIn("lineage", claude_current)
        self.assertEqual(len(codex_current["lineage"]), 1)

        conflict = self._propose(self.owner, "Never write refund idempotency keys.")
        self._review(conflict)
        result = self._recall(claude["token"])
        self.assertEqual(result.outcome, "conflict")
        self.assertEqual(len(result.payload["conflicting"]), 2)
        self.assertNotIn("current", result.payload)

    def test_invitation_project_and_binding_boundaries(self):
        invite = self._invite()
        with self.assertRaises(AuthorizationError):
            self.store.accept_invite(self.workspace, self.stranger, token=invite)
        self.store.accept_invite(self.workspace, self.member, token=invite)
        with self.assertRaises(AuthorizationError):
            self.store.accept_invite(self.workspace, self.member, token=invite)
        with self.connect() as db:
            self.assertIsNone(db.execute("SELECT role FROM workspace_members WHERE workspace_id=%s AND user_id=%s",
                                         (self.workspace, self.member.user_id)).fetchone())
        with self.assertRaises(AuthorizationError):
            self._binding(self.member, "codex")
        group = self.store.create_group(self.workspace, self.owner, name="Payments")["group_id"]
        self.store.group_edge(self.workspace, self.owner, group=group, subject=self.project,
                              kind="project", active=True)
        self.store.group_edge(self.workspace, self.owner, group=group, subject=self.member.user_id,
                              kind="member", active=True)
        binding = self._binding(self.member, "codex", ["read"])
        self.assertEqual(self._recall(binding["token"]).outcome, "empty")
        with self.assertRaises(AuthorizationError):
            self._propose(binding["token"])
        with self.assertRaises(AuthorizationError):
            self.store.context(self.workspace, str(uuid4()), binding["token"], **TASK)
        with self.assertRaises(AuthorizationError):
            self.store.context(str(uuid4()), self.project, binding["token"], **TASK)
        self.store.update_binding(self.workspace, self.member, project=self.project,
                                  binding=binding["binding_id"], operation="revoke")
        with self.assertRaises(AuthorizationError):
            self._recall(binding["token"])
        with self.assertRaises(AuthorizationError):
            self._recall(self._binding(self.member, "codex", [])["token"])

    def test_source_nondisclosure_and_offboarding_during_proof(self):
        self._member()
        first_claude = self._binding(self.owner, "claude")
        second_claude = self._binding(self.member, "claude")
        empty = self._recall(second_claude["token"]).serialized
        self._review(self._propose(self.owner, visibility="private"))
        self.assertEqual(self._recall(second_claude["token"]).serialized, empty)
        self._review(self._propose(self.owner))
        member_packet = self._recall(second_claude["token"])
        owner_packet = self._recall(first_claude["token"])
        self.assertEqual(member_packet.outcome, "packet")
        self.assertEqual(owner_packet.outcome, "packet")
        self.verifier.denied.add(self.member.user_id)
        self.assertEqual(self._recall(second_claude["token"]).serialized, empty)
        self.assertEqual(self._recall(first_claude["token"]).serialized, owner_packet.serialized)

        self.verifier.denied.clear()
        self.assertEqual(self._recall(second_claude["token"]).serialized, member_packet.serialized)
        outstanding = self._invite()

        started, released = self.verifier.pause = Event(), Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._recall, second_claude["token"])
            try:
                self.assertTrue(started.wait(5))
                self.store.change_member(self.workspace, self.owner, user=self.member.user_id, role="remove")
            finally:
                released.set()
            with self.assertRaises(AuthorizationError):
                future.result(timeout=5)
        self.verifier.pause = None
        with self.assertRaises(AuthorizationError):
            self.store.overview(self.workspace, self.member)
        with self.assertRaises(AuthorizationError):
            self.store.accept_invite(self.workspace, self.member, token=outstanding)
        self.store.accept_invite(self.workspace, self.member, token=self._invite())
        with self.assertRaises(AuthorizationError):
            self._recall(second_claude["token"])
        self.assertFalse(any(project["access"] for project in self.store.overview(self.workspace, self.member)["projects"]))
        self.assertEqual(self._recall(first_claude["token"]).outcome, "packet")

    def _seed_approved_versions(self, pull_numbers, *, path):
        """Bulk seed through the runtime role while respecting lifecycle and source immutability."""
        with self.runtime_connect() as db:
            db.execute("SELECT set_config('ninai.team_workspace_id', %s, true)", (self.workspace,))
            actor = self.store._human(db, self.workspace, self.owner)
            for number in pull_numbers:
                key = f"synthetic/payments/pull/{number}"
                url = f"https://github.com/{key}"
                fingerprint = source_fingerprint("github", key, "fixture-v1")
                decision, source = uuid4(), uuid4()
                scope = (self.workspace, self.project, decision)
                db.execute("""
                    INSERT INTO team_decisions(workspace_id,project_id,id,created_by_user_id,visibility,topic)
                    VALUES(%s,%s,%s,%s,'team','refund idempotency')
                """, (*scope, self.owner.user_id))
                db.execute("""
                    INSERT INTO team_decision_versions(workspace_id,project_id,decision_id,version,
                        rule,scope_paths,proposed_by_user_id)
                    VALUES(%s,%s,%s,1,'A different rule.',%s,%s)
                """, (*scope, [path], self.owner.user_id))
                db.execute("""
                    INSERT INTO team_decision_sources(workspace_id,project_id,decision_id,version,id,
                        provider,resource_key,source_url)
                    VALUES(%s,%s,%s,1,%s,'github',%s,%s)
                """, (*scope, source, key, url))
                self.store._record_state(db, *scope, 1, "proposed", actor)
                db.execute("""
                    INSERT INTO team_source_pins(workspace_id,project_id,decision_id,version,source_id,fingerprint)
                    VALUES(%s,%s,%s,1,%s,%s)
                """, (*scope, source, fingerprint))
                self.store._record_state(db, *scope, 1, "approved", actor)

    def test_irrelevant_and_source_denied_volume_does_not_change_projection(self):
        self._member()
        binding = self._binding(self.member, "claude", ["read", "view-history"])
        current = self._propose(self.owner)
        self._review(current)
        baseline = self._recall(binding["token"]).serialized
        baseline_export = self.store.export_project(self.workspace, self.project, self.owner)
        self._seed_approved_versions(range(100, 170), path="billing:src")
        self.verifier.denied_resources.update(f"synthetic/payments/pull/{number}" for number in range(100, 170))
        self.assertEqual(self._recall(binding["token"]).serialized, baseline)
        self.assertEqual(self.store.export_project(self.workspace, self.project, self.owner), baseline_export)

        self._seed_approved_versions(range(200, 460), path="stock:src")
        pending_url = "https://github.com/synthetic/payments/pull/999"
        self._propose(self.owner, decision=current["decision_id"], links=[pending_url])
        self.verifier.checked_resources.clear()
        self.assertEqual(self._recall(binding["token"]).serialized, baseline)
        self.assertEqual(len(self.verifier.checked_resources), 71)
        self.assertNotIn("synthetic/payments/pull/999", self.verifier.checked_resources)

    def test_project_member_inspects_only_own_proposals(self):
        self._member()
        theirs = self._propose(self.member)
        mine = self._propose(self.owner)
        member_items = self.store.proposals(self.workspace, self.project, self.member)["items"]
        self.assertEqual([str(row["decision_id"]) for row in member_items], [theirs["decision_id"]])
        owner_items = self.store.proposals(self.workspace, self.project, self.owner)["items"]
        self.assertEqual({str(row["decision_id"]) for row in owner_items},
                         {theirs["decision_id"], mine["decision_id"]})
        with self.assertRaises(AuthorizationError):
            self.store.review(self.workspace, self.project, self.member, decision=theirs["decision_id"],
                              version=theirs["version"])

    def test_rotation_and_workspace_deletion_fence_pending_release(self):
        from ninai_cloud.control_api import ControlIdentity, ControlService

        self._member()
        binding = self._binding(self.member, "claude")
        proposal = self._propose(self.owner)
        self._review(proposal)
        self.assertEqual(self._recall(binding["token"]).outcome, "packet")

        def deny_pending(token, change):
            started, released = self.verifier.pause = Event(), Event()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self._recall, token)
                try:
                    self.assertTrue(started.wait(5))
                    result = change()
                finally:
                    released.set()
                    self.verifier.pause = None
                with self.assertRaises(AuthorizationError):
                    future.result(timeout=5)
            return result

        replacement = deny_pending(binding["token"], lambda: self.store.update_binding(
            self.workspace, self.member, project=self.project, binding=binding["binding_id"], operation="rotate"))
        self.assertEqual(self._recall(replacement["token"]).outcome, "packet")
        identity = ControlIdentity(self.owner.user_id, self.workspace)
        self.assertTrue(deny_pending(replacement["token"], lambda: ControlService(self.connect).delete_workspace(
            identity, confirmation=self.workspace)))
        with self.assertRaises(AuthorizationError):
            self._recall(replacement["token"])

    def test_workspace_admin_can_revoke_without_project_access(self):
        self._member()
        binding = self._binding(self.member, "codex")
        self.store.assign_project(self.workspace, self.owner, project=self.project, user=self.owner.user_id,
                                  role="remove")
        with self.assertRaises(AuthorizationError):
            self.store.update_binding(self.workspace, self.owner, project=self.project,
                                      binding=binding["binding_id"], operation="rotate")
        self.store.update_binding(self.workspace, self.owner, project=self.project,
                                  binding=binding["binding_id"], operation="revoke")
        with self.assertRaises(AuthorizationError):
            self._recall(binding["token"])

    def test_archive_disables_project_and_revokes_its_bindings(self):
        self._member()
        binding = self._binding(self.member, "claude")
        self._review(self._propose(self.owner))
        self.assertEqual(self._recall(binding["token"]).outcome, "packet")
        with self.assertRaises(AuthorizationError):
            self.store.archive_project(self.workspace, self.member, project=self.project)
        self.store.assign_project(self.workspace, self.owner, project=self.project, user=self.owner.user_id,
                                  role="remove")
        self.store.archive_project(self.workspace, self.owner, project=self.project)
        self.assertEqual(self.store.overview(self.workspace, self.member)["projects"], [])
        with self.assertRaises(AuthorizationError):
            self._recall(binding["token"])
        with self.assertRaises(AuthorizationError):
            self._binding(self.member, "claude")
        with self.connect() as db:
            self.assertIsNotNone(db.execute("SELECT revoked_at FROM team_bindings WHERE id=%s",
                                            (binding["binding_id"],)).fetchone()["revoked_at"])

    def test_project_audit_excludes_hidden_decisions_and_packet_outcomes(self):
        self._member()
        binding = self._binding(self.member, "claude")
        visible = self._propose(self.owner)
        self._review(visible)
        packet = self._recall(binding["token"])
        verified_source = packet.payload["current"][0]["sources"][0]["id"]

        def export():
            return self.store.export_project_audit(self.workspace, self.project, self.owner)["items"]

        baseline = export()
        baseline_read = next(item for item in baseline if item["action"] == "read")
        self.assertEqual(str(baseline_read["binding_id"]), binding["binding_id"])
        self.assertEqual(baseline_read["outcome"], "released")
        self.assertEqual(baseline_read["source_status"], {verified_source: "verified"})
        private = self._propose(self.member, visibility="private",
                                links=["https://github.com/synthetic/payments/pull/404"])
        hidden = self._propose(self.owner, rule="A conflicting example.",
                               links=["https://github.com/synthetic/payments/pull/123"])
        self._review(hidden)
        self.verifier.denied_resources.add("synthetic/payments/pull/123")
        with self.store._tenant(self.workspace, lock=True) as db:
            # Enough newer hidden records to displace the entire baseline
            # if a limit is applied before source authorization.
            db.execute("""
                WITH hidden_events AS (
                    INSERT INTO team_audit_events(workspace_id, project_id, actor_user_id,
                                                  request_id, action, outcome, reason)
                    SELECT %s,%s,%s,gen_random_uuid()::text,'read','packet','synthetic hidden reason'
                    FROM generate_series(1,110) RETURNING workspace_id, id, project_id
                )
                INSERT INTO team_audit_items(workspace_id,event_id,project_id,decision_id,version)
                SELECT workspace_id,id,project_id,%s,%s FROM hidden_events
            """, (self.workspace, self.project, self.member.user_id, hidden["decision_id"], hidden["version"]))
        self.assertEqual(export(), baseline)

        self.verifier.denied_resources.clear()
        self.assertEqual(self._recall(binding["token"]).outcome, "conflict")
        self.verifier.denied_resources.add("synthetic/payments/pull/123")
        projected = export()
        self.assertEqual({str(item["decision_id"]) for item in projected}, {visible["decision_id"]})
        self.assertEqual([item["outcome"] for item in projected if item["action"] == "read"],
                         ["released", "released"])
        for marker in (private["decision_id"], hidden["decision_id"], SOURCE_LINK, "synthetic hidden reason"):
            self.assertNotIn(marker, repr(projected))
        self.verifier.denied.add(self.owner.user_id)
        self.assertEqual(export(), [])

    def test_project_audit_requires_admin_and_rechecks_project_access_at_release(self):
        self._member()
        self._review(self._propose(self.owner))
        for workspace, credential in ((self.workspace, self.member), (str(uuid4()), self.owner),
                                      (self.workspace, self._binding(self.member, "claude")["token"])):
            with self.assertRaises(AuthorizationError):
                self.store.export_project_audit(workspace, self.project, credential)

        started, released = Event(), Event()
        verify = self.verifier.verify

        def blocked_verify(request):
            started.set()
            if not released.wait(5):
                raise RuntimeError("Fixture export did not release the verifier")
            return verify(request)

        with patch.object(self.verifier, "verify", blocked_verify), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.store.export_project_audit, self.workspace, self.project, self.owner)
            try:
                self.assertTrue(started.wait(5))
                self.store.assign_project(self.workspace, self.owner, project=self.project,
                                          user=self.owner.user_id, role="remove")
            finally:
                released.set()
            with self.assertRaises(AuthorizationError):
                future.result(timeout=5)
        with self.connect() as db:
            self.assertIsNone(db.execute("""
                SELECT 1 FROM team_audit_events
                WHERE workspace_id=%s AND project_id=%s AND action='export-project-audit'
            """, (self.workspace, self.project)).fetchone())
