from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare_external_tester_acceptance.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("prepare_external_tester_acceptance", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExternalTesterAcceptanceTest(unittest.TestCase):
    def test_rejects_non_https_non_loopback_endpoint(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires HTTPS"):
            _load_script().prepare("http://example.com")

    def test_local_rehearsal_is_explicitly_not_release_evidence(self) -> None:
        script = _load_script()
        responses = [
            {"status": "ok", "service": "ninai-cloud-mcp"},
            {"resource": "http://127.0.0.1:8000/mcp"},
        ]
        with (
            patch.object(script, "_get_json", side_effect=responses),
            patch.object(script, "_version", return_value="test-version"),
            patch.object(script, "_commit", return_value="test-commit"),
        ):
            report = script.prepare("http://127.0.0.1:8000", allow_http_local=True)

        self.assertIn("LOCAL HTTP REHEARSAL — NOT RELEASE EVIDENCE", report)
        self.assertIn("Preflight decision | PASS", report)
        self.assertIn("External-tester release gate: PENDING / FAIL", report)
        self.assertNotIn("Bearer", report)

    def test_https_preflight_requires_exact_mcp_resource(self) -> None:
        script = _load_script()
        responses = [{"status": "ok"}, {"resource": "https://wrong.example/mcp"}]
        with (
            patch.object(script, "_get_json", side_effect=responses),
            patch.object(script, "_version", return_value="test-version"),
            patch.object(script, "_commit", return_value="test-commit"),
        ):
            report = script.prepare("https://ninai.example")

        self.assertIn("Protected-resource metadata | FAIL", report)
        self.assertIn("Preflight decision | FAIL", report)


if __name__ == "__main__":
    unittest.main()
