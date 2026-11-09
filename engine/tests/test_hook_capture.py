from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ninai.hook_capture import capture, event_to_memory
from ninai.session_capture import _project_identity
from ninai.store import MemoryStore


class HookCaptureTest(unittest.TestCase):
    def test_new_outcomes_use_project_identity_and_require_exact_project_grant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "test.sqlite3")
            event = {
                "cwd": directory, "session_id": "isolated", "tool_use_id": "outcome",
                "tool_name": "mcp__linear__update_issue",
                "tool_input": {"issue": "SYNTHETIC-42"},
                "tool_response": {"status": "resolved", "decision": "Keep project boundaries"},
            }
            memory_id = capture(event, store)
            memory = store.explain(str(memory_id))
            name, binding, root = _project_identity(directory)
            project = store.ensure_project(name=name, binding_key=binding, cwd_or_repo=root)
            self.assertEqual(memory["project_id"], project["id"])
            store.grant("claude-code", "project")
            self.assertEqual(store.recall("SYNTHETIC-42", client_id="claude-code", purpose="broad grant")["facts"], [])
            project_id = str(project["id"])
            self.assertEqual(store.recall("SYNTHETIC-42", client_id="claude-code", purpose="no project grant", project_id=project_id)["facts"], [])
            store.grant_project("claude-code", project_id)
            packet = store.recall("SYNTHETIC-42", client_id="claude-code", purpose="exact grant", project_id=project_id)
            self.assertEqual([fact["id"] for fact in packet["facts"]], [memory_id])

    def test_ignores_temporary_tool_output(self) -> None:
        event = {
            "tool_name": "Bash",
            "tool_input": {"command": "pwd"},
            "tool_response": {"stdout": "/tmp"},
        }
        self.assertIsNone(event_to_memory(event))

    def test_captures_durable_mcp_result(self) -> None:
        event = {
            "session_id": "abc",
            "tool_use_id": "tool-1",
            "tool_name": "mcp__linear__get_issue",
            "tool_input": {"issue": "NIN-42"},
            "tool_response": {"status": "assigned", "due": "2026-07-18"},
        }
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "test.sqlite3")
            memory_id = capture(event, store)
            self.assertIsNotNone(memory_id)
            memory = store.explain(str(memory_id))
            self.assertIn("NIN-42", memory["content"])
            self.assertEqual(memory["memory_type"], "commitment")
            self.assertNotIn("tool_response", memory["content"])

    def test_captures_github_decision_as_compact_fields(self) -> None:
        event = {
            "session_id": "github-session",
            "tool_use_id": "github-tool",
            "tool_name": "mcp__github__merge_pull_request",
            "tool_input": {"pull_request": 81},
            "tool_response": {
                "status": "merged",
                "decision": "Use SQLite as the authoritative local vault",
                "debug_payload": "temporary output that should not be stored",
            },
        }

        payload = event_to_memory(event)

        self.assertEqual(payload["memory_type"], "decision")
        self.assertIn("pull_request=81", payload["content"])
        self.assertIn("decision=Use SQLite", payload["content"])
        self.assertNotIn("debug_payload", payload["content"])

    def test_redacts_secret_inside_selected_outcome(self) -> None:
        event = {
            "tool_name": "mcp__linear__update_issue",
            "tool_input": {"issue": "NIN-51"},
            "tool_response": {
                "status": "resolved",
                "summary": "Resolved using api_key=sk-abcdefghijklmnopqrstuvwxyz123456",
            },
        }

        payload = event_to_memory(event)

        self.assertIn("[REDACTED_SECRET]", payload["content"])
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz123456", payload["content"])

    def test_capture_is_idempotent_for_same_tool_event(self) -> None:
        event = {
            "session_id": "same-session",
            "tool_use_id": "same-tool",
            "tool_name": "mcp__linear__get_issue",
            "tool_input": {"issue": "NIN-42"},
            "tool_response": {"status": "assigned", "due": "2026-07-18"},
        }
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "test.sqlite3")

            first_id = capture(event, store)
            second_id = capture(event, store)

            self.assertEqual(first_id, second_id)
            self.assertEqual(len(store.list_memories()), 1)


if __name__ == "__main__":
    unittest.main()
