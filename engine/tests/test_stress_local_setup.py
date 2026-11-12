from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "stress_local_setup.py"
SPEC = importlib.util.spec_from_file_location("stress_local_setup", SCRIPT)
stress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stress)


class StressAcceptanceOracleTest(unittest.TestCase):
    def test_workload_detects_a_cross_project_disclosure(self):
        original = stress.MemoryStore.recall

        def incorrect_recall(store, *args, **kwargs):
            packet = original(store, *args, **kwargs)
            if packet["facts"]:
                packet["facts"][0]["project_id"] = "ungranted-project"
            return packet

        with patch.object(stress.MemoryStore, "recall", new=incorrect_recall):
            with self.assertRaisesRegex(AssertionError, "Cross-project memory disclosed"):
                stress.run_stress(workers=2, operations=10, timeout_seconds=10)

    def test_workload_detects_provenance_loss(self):
        original = stress.MemoryStore.recall

        def incorrect_recall(store, *args, **kwargs):
            packet = original(store, *args, **kwargs)
            if packet["facts"]:
                packet["facts"][0]["source_uri"] = "synthetic://wrong-source"
            return packet

        with patch.object(stress.MemoryStore, "recall", new=incorrect_recall):
            with self.assertRaisesRegex(AssertionError, "Provenance lost or crossed projects"):
                stress.run_stress(workers=2, operations=10, timeout_seconds=10)

    def test_workload_detects_exceeded_token_budget(self):
        original = stress.MemoryStore.recall

        def incorrect_recall(store, *args, **kwargs):
            packet = original(store, *args, **kwargs)
            if packet["facts"]:
                packet["estimated_tokens"] = kwargs["max_tokens"] + 1
            return packet

        with patch.object(stress.MemoryStore, "recall", new=incorrect_recall):
            with self.assertRaisesRegex(AssertionError, "Recall exceeded estimated token budget"):
                stress.run_stress(workers=2, operations=10, timeout_seconds=10)


if __name__ == "__main__":
    unittest.main()
