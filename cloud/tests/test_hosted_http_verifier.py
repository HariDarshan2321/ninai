from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("verify_hosted_http", ROOT / "scripts" / "verify_hosted_http.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
DATABASE = "postgresql://127.0.0.1:55439/synthetic"
ENDPOINT = "http://127.0.0.1:58039/mcp"
FIXTURE = {"user": "synthetic-user", "workspace": "synthetic-workspace", "tokens": {"claude": "synthetic-only"}}


class HostedHttpTargetTest(unittest.TestCase):
    def test_only_loopback_destinations_are_accepted(self):
        verifier.validate_targets(DATABASE, ENDPOINT)
        for database, endpoint in (
            ("postgresql://production.invalid/database", ENDPOINT),
            (DATABASE, "https://production.invalid/mcp"),
            (DATABASE + "?host=production.invalid", ENDPOINT),
            (DATABASE + "?hostaddr=203.0.113.8", ENDPOINT),
            (DATABASE + "?service=production", ENDPOINT),
            (DATABASE, "http://user@127.0.0.1:58039/mcp"),
        ):
            with self.subTest(database=database, endpoint=endpoint), self.assertRaises(ValueError):
                verifier.validate_targets(database, endpoint)

    def test_sql_timeouts_are_bounded_and_uri_spaces_are_percent_encoded(self):
        target = verifier.bounded_database_url(DATABASE + "?sslmode=disable&connect_timeout=999")
        values = parse_qs(urlsplit(target).query)
        self.assertEqual(values["connect_timeout"], ["5"])
        self.assertEqual(values["sslmode"], ["disable"])
        self.assertEqual(values["options"], ["-c statement_timeout=5000 -c lock_timeout=5000"])
        self.assertNotIn("+", urlsplit(target).query)


class HostedHttpOrchestrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_rounds_have_expected_counts_and_bounded_concurrency(self):
        active = 0
        maximum = 0
        invocations = 0

        async def fake_run(*args):
            nonlocal active, maximum, invocations
            active += 1
            maximum = max(maximum, active)
            invocations += 1
            try:
                await asyncio.sleep(.001)
                return {"passed": True, "cleanup_verified": True, "checks": {str(i): True for i in range(6)}}
            finally:
                active -= 1

        with patch.object(verifier, "run", new=fake_run):
            report = await verifier.run_many(DATABASE, ENDPOINT, concurrency=4, rounds=2, timeout_seconds=5)
        self.assertTrue(report["passed"])
        self.assertEqual(invocations, 8)
        self.assertEqual(maximum, 4)
        self.assertEqual(report["checks_passed"], 48)
        self.assertEqual(report["fixtures_cleaned"], 8)

    async def test_invalid_workload_bounds_start_no_run(self):
        for values in ({"concurrency": 0}, {"concurrency": 9}, {"rounds": 0}, {"rounds": 4}, {"timeout_seconds": 0}, {"timeout_seconds": 121}):
            with self.subTest(values=values), patch.object(verifier, "run") as run:
                with self.assertRaises(ValueError):
                    await verifier.run_many(DATABASE, ENDPOINT, **values)
                run.assert_not_called()

    async def test_transport_failure_still_cleans_the_created_fixture(self):
        @asynccontextmanager
        async def failed_transport(*args, **kwargs):
            raise RuntimeError("Synthetic transport failure")
            yield

        with (
            patch.object(verifier, "bootstrap", return_value=FIXTURE),
            patch.object(verifier, "streamable_http_client", new=failed_transport),
            patch.object(verifier, "cleanup_fixture", return_value=True) as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "Synthetic transport failure"):
                await verifier.run(DATABASE, ENDPOINT)
        cleanup.assert_called_once()
        self.assertEqual(cleanup.call_args.args[1], FIXTURE)

    async def test_timeout_during_bootstrap_waits_for_fixture_then_cleans_it(self):
        def delayed_bootstrap(*args, **kwargs):
            time.sleep(.03)
            return FIXTURE

        with (
            patch.object(verifier, "bootstrap", side_effect=delayed_bootstrap),
            patch.object(verifier, "cleanup_fixture", return_value=True) as cleanup,
            patch.object(verifier, "streamable_http_client") as transport,
        ):
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(verifier.run(DATABASE, ENDPOINT), timeout=.01)
        cleanup.assert_called_once()
        transport.assert_not_called()

    async def test_overall_timeout_cancels_all_active_lifecycles(self):
        completed_cleanup = []

        async def stalled_run(*args):
            try:
                await asyncio.Event().wait()
            finally:
                completed_cleanup.append(True)

        with patch.object(verifier, "run", new=stalled_run):
            with self.assertRaises(TimeoutError):
                await verifier.run_many(DATABASE, ENDPOINT, concurrency=3, rounds=1, timeout_seconds=1)
        self.assertEqual(len(completed_cleanup), 3)


if __name__ == "__main__":
    unittest.main()
