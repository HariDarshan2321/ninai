from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ninai.desktop.api import DesktopApi
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
        self.assertIn("claude-desktop", clients["data"])

        before = self.api.get_permissions("claude-code")["data"]
        self.assertFalse(before["project"])

        self.api.set_permission("claude-code", "project", True)
        after = self.api.get_permissions("claude-code")["data"]
        self.assertTrue(after["project"])

        self.api.set_permission("claude-code", "project", False)
        self.assertFalse(self.api.get_permissions("claude-code")["data"]["project"])

    def test_today_groups_commitments_and_decisions(self) -> None:
        self.api.add_memory("Ship the alpha", memory_type="commitment", scope="project")
        self.api.add_memory("Chose SQLite first", memory_type="decision", scope="work")
        self.api.add_memory("A plain fact", memory_type="fact", scope="project")
        today = self.api.today()["data"]
        self.assertEqual(len(today["commitments"]), 1)
        self.assertEqual(len(today["decisions"]), 1)

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


if __name__ == "__main__":
    unittest.main()
