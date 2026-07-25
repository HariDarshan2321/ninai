from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ninai.contracts import (
    CreateMemoryRequest,
    DisclosureEvent,
    MemoryStore as MemoryStoreContract,
    PermissionService,
    PrincipalContext,
    SearchRequest,
)
from ninai.store import MemoryStore


class SQLiteStoreContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name) / "contract.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sqlite_implements_shared_protocols(self) -> None:
        self.assertIsInstance(self.store, MemoryStoreContract)
        self.assertIsInstance(self.store, PermissionService)

    def test_create_search_and_scoped_fetch(self) -> None:
        memory = self.store.create_memory(
            CreateMemoryRequest(
                content="Ninai uses reversible SQLite migrations",
                memory_type="decision",
                scope="project",
                source_uri="docs://architecture",
            )
        )
        candidates = self.store.search_candidates(
            SearchRequest(
                query="reversible migrations",
                scopes=frozenset({"project"}),
            )
        )
        self.assertEqual([candidate["id"] for candidate in candidates], [memory.id])

        self.assertIsNone(
            self.store.get_memory(PrincipalContext("codex"), memory.id)
        )
        self.store.grant("codex", "project")
        fetched = self.store.get_memory(PrincipalContext("codex"), memory.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["source_uri"], "docs://architecture")

    def test_empty_scope_search_cannot_return_candidates(self) -> None:
        self.store.create_memory(CreateMemoryRequest(content="private project fact"))
        result = self.store.search_candidates(
            SearchRequest(query="private", scopes=frozenset())
        )
        self.assertEqual(result, [])

    def test_disclosure_event_is_recorded(self) -> None:
        self.store.record_disclosure(
            DisclosureEvent(
                client_id="codex",
                purpose="contract test",
                query="Ninai",
                scopes=("project",),
                memory_ids=("memory-1",),
                estimated_tokens=12,
            )
        )
        log = self.store.list_logs()[0]
        self.assertEqual(log["client_id"], "codex")
        self.assertEqual(log["memory_ids"], ["memory-1"])
        self.assertEqual(log["estimated_tokens"], 12)


if __name__ == "__main__":
    unittest.main()
