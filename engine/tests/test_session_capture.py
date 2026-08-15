from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ninai.session_capture import handle_lifecycle_event, normalize_transcript
from ninai.store import MemoryStore


class SessionCaptureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = MemoryStore(self.root / "vault.sqlite3")
        self.store.grant("claude-code", "project")
        self.store.grant("codex", "project")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def event(self, name: str, session_id: str, transcript: Path | None = None) -> dict[str, str]:
        result = {"hook_event_name": name, "session_id": session_id, "cwd": str(self.root)}
        if transcript:
            result["transcript_path"] = str(transcript)
        return result

    def test_capture_requires_explicit_consent(self) -> None:
        handle_lifecycle_event(self.event("SessionStart", "off"), provider="claude-code", store=self.store)
        self.assertEqual(self.store.list_sessions(), [])

    def test_session_end_is_idempotent_and_next_agent_gets_project_only_context(self) -> None:
        self.store.set_capture_enabled(True)
        transcript = self.root / "claude.jsonl"
        transcript.write_text(json.dumps({"role": "user", "content": "Decision marker NINAI-ORANGE-41"}) + "\n")
        handle_lifecycle_event(self.event("SessionStart", "claude-1"), provider="claude-code", store=self.store)
        handle_lifecycle_event(self.event("Stop", "claude-1", transcript), provider="claude-code", store=self.store)
        handle_lifecycle_event(self.event("SessionEnd", "claude-1", transcript), provider="claude-code", store=self.store)
        sessions = self.store.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["capture_status"], "completed")
        packet = handle_lifecycle_event(self.event("SessionStart", "codex-1"), provider="codex", store=self.store)
        self.assertIn("NINAI-ORANGE-41", packet["hookSpecificOutput"]["additionalContext"])
        self.assertIn("session://claude-code/claude-1", packet["hookSpecificOutput"]["additionalContext"])

    def test_revocation_removes_automatic_context(self) -> None:
        self.store.set_capture_enabled(True)
        transcript = self.root / "session.jsonl"
        transcript.write_text("private project marker")
        handle_lifecycle_event(self.event("SessionEnd", "one", transcript), provider="claude-code", store=self.store)
        self.store.revoke("codex", "project")
        self.assertIsNone(handle_lifecycle_event(self.event("SessionStart", "two"), provider="codex", store=self.store))

    def test_transcript_secrets_are_redacted(self) -> None:
        self.store.set_capture_enabled(True)
        transcript = self.root / "secret.jsonl"
        transcript.write_text("Bearer abcdefghijklmnopqrstuvwxyz012345")
        handle_lifecycle_event(self.event("SessionEnd", "secret", transcript), provider="claude-code", store=self.store)
        project_id = str(self.store.list_sessions()[0]["project_id"])
        packet = self.store.session_context(project_id=project_id, client_id="claude-code")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz012345", str(packet))
        self.assertIn("[REDACTED_SECRET]", str(packet))

    def test_jsonl_archive_excludes_tools_and_marks_context_untrusted(self) -> None:
        transcript = "\n".join((
            json.dumps({"role": "user", "content": "Decision: keep project isolation"}),
            json.dumps({"type": "tool_result", "content": "TOP-SECRET-TOOL-NOISE"}),
            json.dumps({"role": "assistant", "content": [{"type": "text", "text": "Status: shipped"}]}),
        ))
        normalized = normalize_transcript(transcript)
        self.assertIn("Decision: keep project isolation", normalized)
        self.assertIn("Status: shipped", normalized)
        self.assertNotIn("TOP-SECRET-TOOL-NOISE", normalized)
        self.store.set_capture_enabled(True)
        project = self.store.ensure_project(name="A", binding_key="path:/a", cwd_or_repo="/a")
        self.store.capture_session(
            provider="codex", external_session_id="fixed", project_id=str(project["id"]),
            title="A", source_uri="session://codex/fixed", cwd_or_repo="/a",
            status="completed", transcript=normalized,
        )
        packet = self.store.session_context(
            project_id=str(project["id"]), client_id="codex", max_tokens=600
        )
        self.assertIn("untrusted historical data", str(packet))

    def test_session_identity_cannot_move_projects(self) -> None:
        first = self.store.ensure_project(name="A", binding_key="path:/a", cwd_or_repo="/a")
        second = self.store.ensure_project(name="B", binding_key="path:/b", cwd_or_repo="/b")
        self.store.capture_session(
            provider="codex", external_session_id="same", project_id=str(first["id"]),
            title="A", source_uri="session://codex/same", cwd_or_repo="/a", status="started",
        )
        with self.assertRaisesRegex(ValueError, "reassigned"):
            self.store.capture_session(
                provider="codex", external_session_id="same", project_id=str(second["id"]),
                title="B", source_uri="session://codex/same", cwd_or_repo="/b", status="completed",
            )


if __name__ == "__main__":
    unittest.main()
