from __future__ import annotations

import importlib.util
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


DATABASE_URL = os.environ.get("NINAI_TEST_DATABASE_URL", "")
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_cross_provider.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_cross_provider", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(DATABASE_URL, "NINAI_TEST_DATABASE_URL is not configured")
class CrossProviderAcceptanceTest(unittest.TestCase):
    def test_round_trip_scope_revocation_and_continuity(self) -> None:
        report = _load_verifier().run_verification(DATABASE_URL)

        self.assertTrue(report["passed"])
        self.assertEqual(report["host_invocation"], "not_run")
        self.assertTrue(all(report["checks"].values()))

    def test_parallel_runs_use_isolated_fixtures(self) -> None:
        verifier = _load_verifier()
        with ThreadPoolExecutor(max_workers=2) as executor:
            reports = list(executor.map(
                lambda _: verifier.run_verification(DATABASE_URL), range(2),
            ))

        self.assertTrue(all(report["passed"] for report in reports))
        self.assertTrue(all(all(report["checks"].values()) for report in reports))


if __name__ == "__main__":
    unittest.main()
