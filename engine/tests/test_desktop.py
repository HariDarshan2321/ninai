from __future__ import annotations

import subprocess
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ninai.desktop.api import DesktopApi, _cli_connection_status, _gemini_connection_status
from ninai.store import MemoryStore


class DesktopApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / "vault.sqlite3")
        self.api = DesktopApi(self.store)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_meta_reports_reference_data(self) -> None:
        res = self.api.meta()
        self.assertTrue(res["ok"])
        self.assertIn("project", res["data"]["scopes"])
        self.assertIn("commitment", res["data"]["memory_types"])
        self.assertIn("restricted", res["data"]["sensitivities"])
        self.assertTrue(res["data"]["vault_path"])

    def test_desktop_assets_keep_brand_and_first_run_guidance(self) -> None:
        web = Path(__file__).resolve().parents[1] / "src" / "ninai" / "desktop" / "web"
        css = (web / "app.css").read_text(encoding="utf-8").lower()
        script = (web / "app.js").read_text(encoding="utf-8")
        markup = (web / "index.html").read_text(encoding="utf-8")
        for color in ("#0b302b", "#f4efe5", "#ff6846", "#dcef7b"):
            self.assertIn(color, css)
        self.assertIn("Your first private handoff", script)
        self.assertIn("Review connected assistants", script)
        self.assertIn("Check connections again", script)
        self.assertIn("Needs attention", script)
        self.assertIn("What should your assistants remember?", markup)
        self.assertIn('<details class="advanced-fields"', markup)
        self.assertIn("This label does not grant access.", markup)

    def test_add_get_and_search_memory(self) -> None:
        added = self.api.add_memory(
            "Send Priya the launch deck", memory_type="commitment", scope="project"
        )
        self.assertTrue(added["ok"])
        memory_id = added["data"]["id"]

        got = self.api.get_memory(memory_id)
        self.assertTrue(got["ok"])
        self.assertEqual(got["data"]["content"], "Send Priya the launch deck")

        found = self.api.search("priya")
        self.assertTrue(found["ok"])
        self.assertIn(memory_id, {m["id"] for m in found["data"]})

    def test_add_memory_rejects_secret(self) -> None:
        res = self.api.add_memory("token AKIAIOSFODNN7EXAMPLE", scope="project")
        self.assertFalse(res["ok"])
        self.assertIn("secret", res["error"].lower())

    def test_update_and_delete_memory(self) -> None:
        memory_id = self.api.add_memory("draft note", scope="project")["data"]["id"]
        updated = self.api.update_memory(
            memory_id, {"content": "final note", "sensitivity": "restricted"}
        )
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["data"]["content"], "final note")
        self.assertEqual(updated["data"]["sensitivity"], "restricted")

        deleted = self.api.delete_memory(memory_id)
        self.assertTrue(deleted["ok"])
        self.assertTrue(deleted["data"]["forgotten"])
        self.assertFalse(self.api.get_memory(memory_id)["ok"])

    def test_update_missing_memory_is_error(self) -> None:
        res = self.api.update_memory("nope", {"content": "x"})
        self.assertFalse(res["ok"])

    def test_permissions_roundtrip(self) -> None:
        clients = self.api.list_clients()
        self.assertIn("claude-code", clients["data"])

        before = self.api.get_permissions("claude-code")["data"]
        self.assertFalse(before["project"])

        self.api.set_permission("claude-code", "project", True)
        after = self.api.get_permissions("claude-code")["data"]
        self.assertTrue(after["project"])

        self.api.set_permission("claude-code", "project", False)
        self.assertFalse(self.api.get_permissions("claude-code")["data"]["project"])

    def test_explicit_editor_setup_never_grants_memory(self) -> None:
        with (
            patch("ninai.desktop.api.Path.is_file", return_value=True),
            patch("ninai.desktop.api.configure_editor") as configure,
            patch("ninai.desktop.api.editor_status", return_value={"installed": True, "configured": True, "status": "configured"}),
        ):
            self.assertTrue(self.api.connect_assistant("cursor")["ok"])
            configure.assert_called_once()
        self.assertEqual(self.store.allowed_scopes("cursor"), set())
        self.assertEqual(self.store.project_permissions("cursor"), [])
        self.assertFalse(self.api.connect_assistant("other")["ok"])

    def test_setup_progress_observes_only_selected_project_and_client(self) -> None:
        project = self.api.create_project("Walkthrough")["data"]["id"]
        other = self.api.create_project("Other project")["data"]["id"]
        self.api.add_memory("Keep migrations reversible", project_id=project)
        self.store.grant_project("codex", project, "read")
        before = len(self.store.list_logs())
        status = self.api.setup_status(project, "codex")["data"]
        self.assertTrue(status["memory_saved"])
        self.assertFalse(status["recall_verified"])
        self.assertEqual(len(self.store.list_logs()), before)
        self.store.recall("reversible", client_id="codex", project_id=project, purpose="real setup check")
        self.assertTrue(self.api.setup_status(project, "codex")["data"]["recall_verified"])
        self.assertFalse(self.api.setup_status(project, "cursor")["data"]["recall_verified"])
        self.store.revoke_project("codex", project, "read")
        self.store.recall("reversible", client_id="codex", project_id=other, purpose="unrelated denial")
        self.assertFalse(self.api.setup_status(project, "codex")["data"]["revocation_verified"])
        self.store.recall("reversible", client_id="codex", project_id=project, purpose="verify revocation")
        self.assertTrue(self.api.setup_status(project, "codex")["data"]["revocation_verified"])
        self.store.grant_project("codex", project, "read")
        self.assertFalse(self.api.setup_status(project, "codex")["data"]["revocation_verified"])

    def test_assistant_statuses_distinguish_connected_missing_and_repair(self) -> None:
        with (
            patch("ninai.desktop.api._cli_connection_status", side_effect=[(True, True), (True, False)]),
            patch("ninai.desktop.api._gemini_connection_status", return_value=(False, False)),
        ):
            statuses = self.api.assistant_statuses()["data"]
        by_id = {item["id"]: item for item in statuses}
        self.assertEqual(by_id["claude-code"]["status"], "configured")
        self.assertEqual(by_id["codex"]["status"], "needs_attention")
        self.assertEqual(by_id["gemini"]["status"], "not_installed")
        self.assertIn("rerun the ninai installer", by_id["codex"]["message"].lower())

    def test_setup_verification_survives_long_history_and_requires_fresh_revocation(self) -> None:
        project = self.api.create_project("Long-lived project")["data"]["id"]
        self.api.add_memory("Keep migrations reversible", project_id=project)
        self.store.grant_project("codex", project, "read")
        self.store.recall("reversible", client_id="codex", project_id=project, purpose="first success")
        self.store.revoke_project("codex", project, "read")
        for _ in range(110):
            self.store.recall("reversible", client_id="codex", project_id=project, purpose="denied")
        status = self.api.setup_status(project, "codex")["data"]
        self.assertTrue(status["recall_verified"])
        self.assertTrue(status["revocation_verified"])
        self.store.grant_project("codex", project, "read")
        self.store.revoke_project("codex", project, "read")
        self.assertFalse(self.api.setup_status(project, "codex")["data"]["revocation_verified"])
        self.store.recall("reversible", client_id="codex", project_id=project, purpose="fresh denial")
        self.assertTrue(self.api.setup_status(project, "codex")["data"]["revocation_verified"])

    def test_malformed_switch_values_cannot_grant_access_or_enable_capture(self) -> None:
        project = self.api.create_project("Malformed switch check")["data"]["id"]
        setters = [
            lambda value: self.api.set_permission("codex", "work", value),
            lambda value: self.api.set_project_permission("codex", project, "read", value),
            lambda value: self.api.set_capability("codex", "work", "write", value),
            self.api.set_capture_enabled,
        ]
        for invalid in ("false", "true", "1", 0, 1, None, [], {}):
            for setter in setters:
                with self.subTest(value=invalid, setter=setter):
                    self.assertFalse(setter(invalid)["ok"])
            self.assertEqual(self.store.allowed_scopes("codex"), set())
            self.assertFalse(self.store.can_access_project("codex", project))
            self.assertEqual(self.store.permissions("codex"), [])
            self.assertFalse(self.store.capture_enabled())
        self.assertTrue(self.api.set_permission("codex", "work", True)["ok"])
        self.assertFalse(self.api.set_permission("codex", "work", "false")["ok"])
        self.assertEqual(self.store.allowed_scopes("codex"), {"work"})
        self.assertTrue(self.api.set_permission("codex", "work", False)["ok"])
        self.assertEqual(self.store.allowed_scopes("codex"), set())

    def test_project_revoke_normalizes_client_and_rejects_missing_project(self) -> None:
        project = self.api.create_project("Whitespace client check")["data"]["id"]
        self.assertTrue(self.api.set_project_permission(" codex ", project, "read", True)["ok"])
        self.assertTrue(self.store.can_access_project("codex", project))
        self.assertTrue(self.api.set_project_permission(" codex ", project, "read", False)["ok"])
        self.assertFalse(self.store.can_access_project("codex", project))
        self.assertTrue(self.api.set_project_permission("codex", project, "read", False)["ok"])
        self.assertFalse(self.api.set_project_permission("codex", "missing", "read", False)["ok"])
        self.assertFalse(self.api.set_project_permission(" ", project, "read", False)["ok"])

    def test_empty_selection_and_legacy_logs_never_verify_a_new_project(self) -> None:
        for project, client in ((None, None), ("", ""), ("missing", "codex")):
            status = self.api.setup_status(project, client)["data"]
            self.assertFalse(status["project_selected"])
            self.assertFalse(status["memory_saved"])
            self.assertFalse(status["read_allowed"])
            self.assertFalse(status["recall_verified"])
            self.assertFalse(status["revocation_verified"])
        old_path = Path(self.temp.name) / "legacy.sqlite3"
        with sqlite3.connect(old_path) as db:
            db.execute("""CREATE TABLE access_logs (
                id TEXT PRIMARY KEY, client_id TEXT NOT NULL, purpose TEXT NOT NULL,
                query TEXT NOT NULL, scopes TEXT NOT NULL, memory_ids TEXT NOT NULL,
                estimated_tokens INTEGER NOT NULL, created_at TEXT NOT NULL)""")
            db.execute("INSERT INTO access_logs VALUES(?,?,?,?,?,?,?,?)", (
                "old", "codex", "legacy recall", "decision", '["project"]',
                '["old-memory"]', 20, "2026-01-01T00:00:00+00:00",
            ))
        legacy = MemoryStore(old_path)
        api = DesktopApi(legacy)
        project = api.create_project("New named project")["data"]["id"]
        api.add_memory("Keep changes reversible", project_id=project)
        legacy.grant_project("codex", project, "read")
        self.assertFalse(api.setup_status(project, "codex")["data"]["recall_verified"])
        self.assertIsNone(legacy.list_logs()[0]["project_id"])
        reopened = MemoryStore(old_path)
        self.assertEqual(len(reopened.list_logs()), 1)
        self.assertEqual(len(reopened.list_projects()), 1)
        reopened.recall("reversible", client_id="codex", project_id=project, purpose="fresh named-project check")
        self.assertTrue(DesktopApi(reopened).setup_status(project, "codex")["data"]["recall_verified"])

    def test_cli_status_treats_a_timeout_as_needing_attention(self) -> None:
        with (
            patch("ninai.desktop.api.shutil.which", return_value="/usr/local/bin/claude"),
            patch(
                "ninai.desktop.api.subprocess.run",
                side_effect=subprocess.TimeoutExpired("claude", 3),
            ),
        ):
            self.assertEqual(_cli_connection_status("claude-code"), (True, False))

    def test_gemini_status_treats_malformed_settings_as_needing_attention(self) -> None:
        home = Path(self.temp.name) / "home"
        settings = home / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("not-json", encoding="utf-8")
        with (
            patch("ninai.desktop.api.shutil.which", return_value="/usr/local/bin/gemini"),
            patch("ninai.desktop.api.Path.home", return_value=home),
        ):
            self.assertEqual(_gemini_connection_status(), (True, False))

    def test_beginner_first_handoff_and_revocation_journey(self) -> None:
        memory_id = self.api.add_memory(
            "Keep every migration reversible", memory_type="decision", scope="project"
        )["data"]["id"]
        self.api.set_permission("claude-code", "project", True)
        packet = self.store.recall(
            "migration decision", client_id="claude-code", purpose="first handoff"
        )
        self.assertIn(memory_id, {fact["id"] for fact in packet["facts"]})

        self.api.set_permission("claude-code", "project", False)
        packet = self.store.recall(
            "migration decision", client_id="claude-code", purpose="revocation check"
        )
        self.assertEqual(packet["facts"], [])

    def test_project_controls_preserve_independent_capabilities(self) -> None:
        self.assertFalse(self.api.create_project("  ")["ok"])
        project = self.api.create_project("Client A")["data"]
        self.assertIn(project["id"], {row["id"] for row in self.api.list_projects()["data"]})
        memory_id = self.api.add_memory("Client A rollout decision", project_id=project["id"])["data"]["id"]
        self.api.set_permission("codex", "project", True)
        self.assertIsNone(self.store.explain(memory_id, client_id="codex"))
        self.api.set_project_permission("codex", project["id"], "read", True)
        grants = self.api.get_project_permissions("codex")["data"][0]
        self.assertTrue(grants["can_read"])
        self.assertFalse(grants["can_write"])
        self.assertFalse(grants["can_delete"])
        self.assertIsNotNone(self.store.explain(memory_id, client_id="codex"))
        self.assertFalse(self.store.forget(memory_id, client_id="codex"))
        self.api.set_project_permission("codex", project["id"], "read", False)
        self.assertIsNone(self.store.explain(memory_id, client_id="codex"))
        self.api.set_capability("codex", "work", "write", True)
        capabilities = self.api.get_capabilities("codex")["data"]["work"]
        self.assertTrue(capabilities["write"])
        self.assertFalse(capabilities["read"])
        self.assertFalse(capabilities["delete"])

    def test_today_groups_commitments_and_decisions(self) -> None:
        self.api.add_memory("Ship the alpha", memory_type="commitment", scope="project")
        self.api.add_memory("Chose SQLite first", memory_type="decision", scope="work")
        self.api.add_memory("A plain fact", memory_type="fact", scope="project")
        today = self.api.today()["data"]
        self.assertEqual(len(today["commitments"]), 1)
        self.assertEqual(len(today["decisions"]), 1)
        self.assertEqual(len(today["recent_memories"]), 3)

    def test_sources_group_by_scheme(self) -> None:
        self.api.add_memory("a", scope="project", source_uri="gmail://t/1")
        self.api.add_memory("b", scope="project", source_uri="gmail://t/2")
        self.api.add_memory("c", scope="project", source_uri="linear://NIN-1")
        groups = {g["scheme"]: g["count"] for g in self.api.sources()["data"]}
        self.assertEqual(groups["gmail"], 2)
        self.assertEqual(groups["linear"], 1)

    def test_list_logs_returns_envelope(self) -> None:
        res = self.api.list_logs()
        self.assertTrue(res["ok"])
        self.assertIsInstance(res["data"], list)

    def test_sessions_and_capture_consent_are_exposed(self) -> None:
        self.assertFalse(self.api.capture_status()["data"]["enabled"])
        enabled = self.api.set_capture_enabled(True)
        self.assertTrue(enabled["ok"])
        self.assertTrue(enabled["data"]["enabled"])
        sessions = self.api.list_sessions()
        self.assertTrue(sessions["ok"])
        self.assertEqual(sessions["data"], [])
        self.assertFalse(self.api.delete_session("missing")["data"]["deleted"])


if __name__ == "__main__":
    unittest.main()
