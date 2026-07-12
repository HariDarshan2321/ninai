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

    def test_explain_denies_out_of_scope_client_and_logs(self) -> None:
        self.store.grant("claude-code", "project")
        private = self.store.remember("A private health detail", scope="health")

        # A named client without the health scope must not read it, and the
        # attempt must be logged (no memory disclosed).
        self.assertIsNone(self.store.explain(private.id, client_id="claude-code"))
        log = self.store.list_logs()[0]
        self.assertEqual(log["purpose"], "explain")
        self.assertEqual(log["memory_ids"], [])

        # The local operator (no client_id) retains full access.
        self.assertIsNotNone(self.store.explain(private.id))

    def test_explain_allows_and_logs_in_scope_client(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember("Ninai launch decision", scope="project")

        result = self.store.explain(memory.id, client_id="claude-code")
        self.assertIsNotNone(result)
        log = self.store.list_logs()[0]
        self.assertEqual(log["memory_ids"], [memory.id])

    def test_forget_denies_out_of_scope_client(self) -> None:
        self.store.grant("claude-code", "project")
        private = self.store.remember("A private personal note", scope="personal")

        # Untrusted client cannot delete a memory outside its scopes.
        self.assertFalse(self.store.forget(private.id, client_id="claude-code"))
        self.assertIsNotNone(self.store.explain(private.id))

        # The local operator can.
        self.assertTrue(self.store.forget(private.id))

    def test_recall_is_word_order_independent(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember("Ninai launch checklist", scope="project")
        packet = self.store.recall(
            "checklist launch Ninai",
            client_id="claude-code",
            purpose="order independence",
        )
        self.assertIn(memory.id, {fact["id"] for fact in packet["facts"]})

    def test_update_preserves_provenance_and_refreshes_search(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember(
            "Send Priya the draft deck",
            scope="project",
            source_uri="gmail://thread/1",
        )
        updated = self.store.update(
            memory.id, content="Send Priya the final launch deck", scope="work"
        )
        self.assertIsNotNone(updated)
        # provenance and creation time preserved; updated_at bumped.
        self.assertEqual(updated["source_uri"], "gmail://thread/1")
        self.assertEqual(updated["created_at"], memory.created_at)
        self.assertGreaterEqual(updated["updated_at"], memory.updated_at)
        self.assertEqual(updated["scope"], "work")
        # FTS reflects the new content: searchable by a new term, and the old
        # unique term no longer matches.
        self.store.grant("claude-code", "work")
        hit = self.store.recall("final launch deck", client_id="claude-code", purpose="t")
        self.assertIn(memory.id, {f["id"] for f in hit["facts"]})

    def test_update_rejects_secret_content(self) -> None:
        self.store.grant("claude-code", "project")
        memory = self.store.remember("A safe note", scope="project")
        with self.assertRaises(ValueError):
            self.store.update(memory.id, content="new key AKIAIOSFODNN7EXAMPLE here")

    def test_update_rejects_invalid_scope_and_sensitivity(self) -> None:
        memory = self.store.remember("A note", scope="project")
        with self.assertRaises(ValueError):
            self.store.update(memory.id, scope="not-a-scope")
        with self.assertRaises(ValueError):
            self.store.update(memory.id, sensitivity="ultra")

    def test_update_missing_memory_returns_none(self) -> None:
        self.assertIsNone(self.store.update("does-not-exist", content="x"))

    def test_migration_adds_sensitivity_to_preexisting_vault(self) -> None:
        import sqlite3

        # Simulate a vault created before the sensitivity column existed.
        legacy_path = Path(self.temp.name) / "legacy.sqlite3"
        con = sqlite3.connect(legacy_path)
        con.executescript(
            """
            CREATE TABLE memories (
                id TEXT PRIMARY KEY, content TEXT NOT NULL, memory_type TEXT NOT NULL,
                scope TEXT NOT NULL, source_uri TEXT NOT NULL, importance REAL NOT NULL,
                confidence REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
            );
            INSERT INTO memories VALUES
              ('m1','old fact','fact','project','cli://x',0.6,1.0,'2026-01-01T00:00:00+00:00',
               '2026-01-01T00:00:00+00:00',0,NULL);
            """
        )
        con.commit()
        con.close()

        # Opening it through MemoryStore must migrate without data loss.
        store = MemoryStore(legacy_path)
        row = store.explain("m1")
        self.assertIsNotNone(row)
        self.assertEqual(row["content"], "old fact")
        self.assertEqual(row["sensitivity"], "normal")

    def test_sensitivity_defaults_to_normal_and_is_editable(self) -> None:
        memory = self.store.remember("A note", scope="project")
        stored = self.store.explain(memory.id)
        self.assertEqual(stored["sensitivity"], "normal")
        updated = self.store.update(memory.id, sensitivity="restricted")
        self.assertEqual(updated["sensitivity"], "restricted")

    def test_source_uri_counts_against_token_budget(self) -> None:
        self.store.grant("claude-code", "project")
        long_uri = "https://example.test/" + "a" * 900
        self.store.remember("OK", scope="project", source_uri=long_uri)
        packet = self.store.recall(
            "OK",
            client_id="claude-code",
            purpose="budget",
            max_tokens=400,
        )
        # The fact fits, and estimated_tokens reflects the 900-char source_uri
        # rather than just the two-character content (the pre-fix undercount
        # would have reported ~25 tokens).
        self.assertEqual(len(packet["facts"]), 1)
        self.assertGreater(packet["estimated_tokens"], 200)
        self.assertLessEqual(packet["estimated_tokens"], 400)


if __name__ == "__main__":
    unittest.main()
