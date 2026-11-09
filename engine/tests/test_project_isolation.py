from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ninai.contracts import SearchRequest
from ninai.store import MemoryStore


class ProjectIsolationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "vault.sqlite3"
        self.store = MemoryStore(self.path)
        self.a = self.store.ensure_project(name="Client A", binding_key="a", cwd_or_repo="/a")["id"]
        self.b = self.store.ensure_project(name="Client B", binding_key="b", cwd_or_repo="/b")["id"]

    def tearDown(self):
        self.temp.cleanup()

    def recall(self, project_id=None):
        return self.store.recall("launch decision", client_id="assistant", purpose="isolation test", project_id=project_id)

    def test_broad_grants_never_reveal_project_records(self):
        legacy = self.store.remember("legacy launch decision")
        a = self.store.remember("client A launch decision", project_id=self.a)
        b = self.store.remember("client B launch decision", project_id=self.b)
        self.store.grant("assistant", "project")
        self.assertEqual({f["id"] for f in self.recall()["facts"]}, {legacy.id})
        self.assertEqual(self.recall(self.a)["facts"], [])
        self.assertIsNone(self.store.explain(a.id, client_id="assistant"))
        self.store.grant_project("assistant", self.a)
        with patch("ninai.store.rank_candidates", wraps=__import__("ninai.store", fromlist=["rank_candidates"]).rank_candidates) as rank:
            self.assertEqual({f["id"] for f in self.recall(self.a)["facts"]}, {a.id})
            self.assertEqual({f["id"] for f in rank.call_args.args[0]}, {a.id})
        self.assertNotIn(b.id, self.store.list_logs()[0]["memory_ids"])
        self.assertEqual(self.recall(self.b)["facts"], [])
        self.store.revoke_project("assistant", self.a)
        self.assertEqual(self.recall(self.a)["facts"], [])

    def test_project_actions_are_independent_and_default_deny(self):
        self.store.grant_project("assistant", self.a, "read")
        with self.assertRaises(PermissionError):
            self.store.remember("launch decision", project_id=self.a, client_id="assistant")
        self.store.grant_project("assistant", self.a, "write")
        memory = self.store.remember("launch decision", project_id=self.a, client_id="assistant")
        self.assertFalse(self.store.forget(memory.id, client_id="assistant"))
        self.store.grant_project("assistant", self.a, "delete")
        self.store.revoke_project("assistant", self.a, "write")
        with self.assertRaises(PermissionError):
            self.store.remember("another decision", project_id=self.a, client_id="assistant")
        self.assertTrue(self.store.forget(memory.id, client_id="assistant"))

    def test_legacy_actions_do_not_inherit_read_grants(self):
        self.store.grant("assistant", "project")
        memory = self.store.remember("legacy launch decision")
        with self.assertRaises(PermissionError):
            self.store.remember("new decision", client_id="assistant")
        self.assertFalse(self.store.forget(memory.id, client_id="assistant"))
        self.store.grant_action("assistant", "project", "write")
        self.store.remember("new decision", client_id="assistant")
        self.store.grant_action("assistant", "project", "delete")
        self.assertTrue(self.store.forget(memory.id, client_id="assistant"))

    def test_invalid_projects_and_nonproject_scope_rejected(self):
        with self.assertRaises(ValueError):
            self.store.remember("decision", project_id="missing")
        with self.assertRaises(ValueError):
            self.store.grant_project("assistant", "missing")
        with self.assertRaises(ValueError):
            self.store.remember("decision", scope="personal", project_id=self.a)

    def test_contract_search_enforces_client_project_grant(self):
        self.store.remember("launch decision", project_id=self.a)
        request = SearchRequest("launch", frozenset({"project"}), project_id=self.a, client_id="assistant")
        self.assertEqual(self.store.search_candidates(request), [])
        self.store.grant_project("assistant", self.a)
        self.assertEqual(len(self.store.search_candidates(request)), 1)

    def test_migration_leaves_existing_records_legacy_without_escalation(self):
        path = Path(self.temp.name) / "old.sqlite3"
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE memories(id TEXT PRIMARY KEY,content TEXT NOT NULL,
                memory_type TEXT NOT NULL,scope TEXT NOT NULL,source_uri TEXT NOT NULL,
                importance REAL NOT NULL,confidence REAL NOT NULL,created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,access_count INTEGER NOT NULL DEFAULT 0,deleted_at TEXT)""")
            db.execute("INSERT INTO memories VALUES('old','launch decision','decision','project','user://manual',1,1,'2026-01-01','2026-01-01',0,NULL)")
        store = MemoryStore(path)
        self.assertIsNone(store.explain("old")["project_id"])
        store.grant("assistant", "project")
        self.assertIsNotNone(store.explain("old", client_id="assistant"))
        self.assertFalse(store.forget("old", client_id="assistant"))
        self.assertEqual(store.project_permissions("assistant"), [])


if __name__ == "__main__":
    unittest.main()
