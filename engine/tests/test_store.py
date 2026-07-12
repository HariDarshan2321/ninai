from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ninai.store import MemoryStore


class MemoryStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / "test.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_permission_denies_ungranted_client(self) -> None:
        self.store.remember("Finish the Ninai release checklist before launch", scope="project")
        packet = self.store.recall(
            "What must I finish?",
            client_id="claude-code",
            purpose="planning",
        )
        self.assertEqual(packet["facts"], [])

    def test_recall_returns_provenance_after_grant(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember(
            "Finish the Ninai permission dashboard before launch",
            memory_type="commitment",
            scope="project",
            source_uri="linear://NIN-42",
        )
        packet = self.store.recall(
            "Ninai dashboard launch",
            client_id="claude-code",
            purpose="daily planning",
        )
        self.assertEqual(packet["facts"][0]["id"], memory.id)
        self.assertEqual(packet["facts"][0]["source_uri"], "linear://NIN-42")

    def test_revocation_removes_scope_from_future_recall(self) -> None:
        self.store.grant("claude-code", "project")
        self.store.remember("Ninai project launch decision", scope="project")
        self.store.revoke("claude-code", "project")

        packet = self.store.recall(
            "Ninai project launch",
            client_id="claude-code",
            purpose="verify revocation",
        )

        self.assertEqual(packet["scopes"], [])
        self.assertEqual(packet["facts"], [])
        self.assertEqual(
            packet["message"],
            "No memory scopes are granted to this client.",
        )

    def test_recall_never_ranks_or_logs_memory_outside_granted_scope(self) -> None:
        self.store.grant("claude-code", "project")
        permitted = self.store.remember(
            "Ninai launch planning belongs to the project",
            scope="project",
        )
        private = self.store.remember(
            "Ninai launch planning includes a private health detail",
            scope="health",
        )

        packet = self.store.recall(
            "Ninai launch planning",
            client_id="claude-code",
            purpose="scope isolation test",
        )
        log = self.store.list_logs()[0]

        self.assertEqual({fact["id"] for fact in packet["facts"]}, {permitted.id})
        self.assertNotIn(private.id, log["memory_ids"])
        self.assertEqual(log["scopes"], ["project"])

    def test_token_budget_is_respected(self) -> None:
        self.store.grant("claude-code", "project")
        for index in range(10):
            self.store.remember(
                f"Ninai project item {index} " + ("context " * 80),
                scope="project",
            )
        packet = self.store.recall(
            "Ninai project context",
            client_id="claude-code",
            purpose="test",
            max_tokens=220,
        )
        self.assertLessEqual(packet["estimated_tokens"], 220)

    def test_secret_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.remember("api_key=sk-thislooksverysecret0123456789")

    def test_secret_in_source_uri_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.remember(
                "A safe durable fact",
                source_uri="https://example.test/?access_token=abcdefghijklmnop",
            )

    def test_unknown_memory_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.remember("A durable note", memory_type="transient")

    def test_forget_removes_memory(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember("Temporary project decision", scope="project")
        self.assertTrue(self.store.forget(memory.id))
        self.assertIsNone(self.store.explain(memory.id))


if __name__ == "__main__":
    unittest.main()
