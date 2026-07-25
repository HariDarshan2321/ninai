from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ninai_cloud.policy import (ALLOWED_MEMORY_TYPES, WriteDisposition, classify_write,
                                validate_memory_type)


def decision(content: str = "Project Nova uses PostgreSQL", **overrides):
    values = dict(content=content, memory_type="decision", scope_kind="project",
                  scope_id="project-nova", source_uri="client-session://claude/123",
                  requested_auto=True)
    values.update(overrides)
    return classify_write(**values)


class HostedWritePolicyTest(unittest.TestCase):
    def test_complete_memory_type_enum_is_validated(self) -> None:
        self.assertEqual(ALLOWED_MEMORY_TYPES,
                         {"commitment", "constraint", "decision", "event", "fact",
                          "preference", "procedure", "project_state"})
        for memory_type in ALLOWED_MEMORY_TYPES:
            self.assertEqual(validate_memory_type(memory_type), memory_type)
        for invalid in ("", "transient", "Decision", None):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "Unsupported memory type"):
                validate_memory_type(invalid)  # type: ignore[arg-type]

    def test_review_is_the_default_even_for_low_risk_content(self) -> None:
        result = decision(requested_auto=False)
        self.assertEqual(result.disposition, WriteDisposition.PROPOSED)
        self.assertFalse(result.allows_auto_activation)
        self.assertIn("review_mode_default", result.reasons)

    def test_only_explicit_source_backed_unambiguous_low_risk_item_is_auto_eligible(self) -> None:
        result = decision()
        self.assertEqual(result.disposition, WriteDisposition.ACTIVE)
        self.assertEqual(result.risk_level, "low")

    def test_every_forbidden_auto_category_stays_proposed(self) -> None:
        cases = {
            "permission_change": "Grant the contractor admin access",
            "delete_or_forget": "Delete the customer history permanently",
            "legal_commitment": "Sign the supplier contract tomorrow",
            "financial_commitment": "Pay the vendor invoice on Friday",
            "company_wide_policy": "All employees must use this company-wide policy",
            "inferred_sensitive_information": "Jordan has a medical condition",
            "secret_or_credential": "The API credential belongs in the shared vault",
            "ambiguous_statement": "Maybe the project uses PostgreSQL",
        }
        for reason, content in cases.items():
            with self.subTest(reason=reason):
                result = decision(content)
                self.assertEqual(result.disposition, WriteDisposition.PROPOSED)
                self.assertEqual(result.risk_level, "high")
                self.assertIn(reason, result.reasons)

    def test_missing_source_ambiguous_scope_and_conflict_cannot_auto_activate(self) -> None:
        cases = (
            ({"source_uri": "model://inference"}, "missing_authoritative_source"),
            ({"scope_id": ""}, "ambiguous_scope"),
            ({"has_active_conflict": True}, "active_conflict"),
        )
        for overrides, reason in cases:
            with self.subTest(reason=reason):
                result = decision(**overrides)
                self.assertEqual(result.disposition, WriteDisposition.PROPOSED)
                self.assertIn(reason, result.reasons)

    def test_detected_secret_is_rejected_not_merely_proposed(self) -> None:
        result = decision(contains_secret=True)
        self.assertEqual(result.disposition, WriteDisposition.REJECTED)
        self.assertEqual(result.risk_level, "blocked")


if __name__ == "__main__":
    unittest.main()
