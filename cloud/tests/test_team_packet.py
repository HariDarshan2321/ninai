from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from ninai_cloud.team_packet import (
    DecisionVersion,
    EvidenceStatus,
    SourceEvidence,
    TaskContext,
    compose_task_packet,
    matches_task,
)


NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)
REFUND_TASK = TaskContext("Add retries to refund writes", ("checkout:refunds/write.py",))
SOURCE = SourceEvidence("s1", EvidenceStatus.VERIFIED, source_uri="https://github.com/example/repo/pull/1")
CURRENT = DecisionVersion(
    "refund@2", "refund", 2, "refund-idempotency", "Use the refund intent ID.", None,
    "approved", (SOURCE,), scope_paths=("checkout:refunds/",),
)


class TeamPacketTests(unittest.TestCase):
    def compose(self, *versions, context=REFUND_TASK, **kwargs):
        return compose_task_packet(context, versions, now=NOW, **kwargs)

    def test_projects_exact_version_and_only_documented_rationale(self):
        rendered = self.compose(CURRENT)
        self.assertEqual(rendered.outcome, "packet")
        self.assertEqual(rendered.payload, json.loads(rendered.serialized))
        self.assertEqual(rendered.released_versions, ("refund@2",))
        item = rendered.payload["current"][0]
        self.assertEqual(item["version"], 2)
        self.assertEqual(item["rationale_status"], "undocumented")
        self.assertIsNone(item["rationale"])
        self.assertEqual(item["sources"], [{"id": SOURCE.source_id, "uri": SOURCE.source_uri}])
        documented = self.compose(replace(CURRENT, rationale="One intent may be retried."))
        self.assertEqual(documented.payload["current"][0]["rationale"], "One intent may be retried.")
        self.assertEqual(documented.payload["current"][0]["rationale_status"], "documented")

    def test_omits_proposed_replaced_expired_retired_and_revoked_current_versions(self):
        for state in ("proposed", "replaced", "expired", "retired", "revoked"):
            with self.subTest(status=state):
                self.assertEqual(self.compose(replace(CURRENT, status=state)).payload, {"outcome": "empty"})
        self.assertEqual(self.compose(replace(CURRENT, expires_at=NOW)).outcome, "empty")
        self.assertEqual(self.compose(replace(CURRENT, expires_at=NOW.replace(tzinfo=None))).outcome, "empty")
        self.assertEqual(self.compose(replace(CURRENT, expires_at=NOW + timedelta(seconds=1))).outcome, "packet")

    def test_an_inaccessible_required_source_cannot_influence_output(self):
        other = replace(CURRENT, version_id="other@1", decision_id="other", version=1,
                        rule="Generate a random ID each retry.")
        baseline = self.compose(CURRENT).serialized
        for status in (EvidenceStatus.PERMISSION_DENIED, EvidenceStatus.UNKNOWN):
            with self.subTest(status=status):
                hidden_source = replace(SOURCE, source_id="hidden", status=status)
                hidden = replace(other, sources=(hidden_source,))
                self.assertEqual(self.compose(CURRENT, hidden).serialized, baseline)
                # A second source with affirmative access cannot signal an
                # issue when one required reference is inaccessible.
                changed = replace(SOURCE, source_id="changed", status=EvidenceStatus.CHANGED)
                self.assertEqual(self.compose(CURRENT, replace(hidden, sources=(hidden_source, changed))).serialized,
                                 baseline)

    def test_positive_access_without_current_evidence_suppresses_a_rival_answer(self):
        for status in (EvidenceStatus.CHANGED, EvidenceStatus.UNAVAILABLE):
            with self.subTest(status=status):
                source = replace(SOURCE, source_id="inspect-only", status=status)
                stale_evidence = replace(CURRENT, version_id="legacy@1", rule="Use a fresh request ID.",
                                         sources=(source,))
                packet = self.compose(CURRENT, stale_evidence)
                self.assertEqual(packet.payload, {"outcome": "abstain", "signals": ["evidence-unverified"]})
                self.assertFalse(packet.released_versions)
        self.assertEqual(self.compose(replace(CURRENT, sources=())).outcome, "empty")
        self.assertEqual(self.compose(replace(CURRENT, sources=(replace(SOURCE, source_uri=None),))).outcome, "empty")

    def test_inaccessible_optional_reference_is_indistinguishable_from_absence(self):
        extra = SourceEvidence("hidden", EvidenceStatus.PERMISSION_DENIED, required=False,
                               source_uri="https://github.com/example/repo/pull/900")
        with_optional = replace(CURRENT, sources=(extra, SOURCE))
        self.assertEqual(self.compose(with_optional).serialized, self.compose(CURRENT).serialized)
        self.assertEqual(self.compose(replace(with_optional, sources=(extra,))).outcome, "empty")

    def test_conflict_has_no_winner_under_an_item_or_serialized_budget(self):
        other = replace(CURRENT, version_id="legacy@1", decision_id="legacy", version=1,
                        rule="Use a fresh request ID for every retry.")
        complete = self.compose(CURRENT, other)
        self.assertEqual(complete.outcome, "conflict")
        self.assertEqual(set(complete.released_versions), {"refund@2", "legacy@1"})
        self.assertEqual(complete.serialized, self.compose(other, CURRENT).serialized)
        for limits in ({"max_items": 1}, {"max_tokens": 90}, {"max_tokens": 1}):
            with self.subTest(limits=limits):
                result = self.compose(CURRENT, other, **limits)
                self.assertEqual(result.outcome, "conflict")
                self.assertEqual(result.signals, ("resolve-before-edit", "budget-exhausted"))
                self.assertFalse(result.released_versions)
                self.assertNotIn("current", result.payload or {})

    def test_conflict_preserves_meaningful_punctuation_in_rules(self):
        min_rule = replace(CURRENT, rule="Refund size must satisfy amount >= 5.")
        max_rule = replace(CURRENT, version_id="legacy@1", decision_id="legacy", version=1,
                           rule="Refund size must satisfy amount <= 5.")
        self.assertEqual(self.compose(min_rule, max_rule).outcome, "conflict")

    def test_replacement_lineage_and_full_history_have_separate_permissions(self):
        predecessor_source = replace(SOURCE, source_id="s0")
        old = replace(CURRENT, version_id="refund@1", version=1, status="replaced",
                      rule="Use the gateway request ID.", sources=(predecessor_source,))
        current = replace(CURRENT, replaces_version_id=old.version_id)
        denied_history = self.compose(current, old, history_only=True)
        self.assertEqual(denied_history.outcome, "denied")
        self.assertNotIn("refund@1", self.compose(current, old).serialized.decode())
        allowed = self.compose(current, old, can_view_history=True)
        self.assertEqual(allowed.payload["lineage"], [{"current": "refund@2", "replaces": "refund@1"}])
        self.assertEqual(allowed.released_versions, ("refund@2", "refund@1"))
        self.assertNotIn(old.rule, allowed.serialized.decode())
        self.assertNotIn("s0", allowed.serialized.decode())
        trimmed = self.compose(current, old, can_view_history=True, max_items=1)
        self.assertNotIn("lineage", trimmed.payload)
        hidden = replace(old, sources=(replace(predecessor_source, status=EvidenceStatus.PERMISSION_DENIED),))
        self.assertEqual(self.compose(current, hidden, can_view_history=True).serialized,
                         self.compose(current, can_view_history=True).serialized)
        history = self.compose(current, old, can_view_history=True, history_only=True)
        self.assertEqual(history.outcome, "history")
        self.assertEqual(history.payload["history"][0]["rule"], old.rule)
        self.assertEqual(history.released_versions, ("refund@1",))

    def test_relevance_respects_repository_and_directory_segments(self):
        for paths in (("checkout:refundsmanship/write.py",), ("other:refunds/write.py",),
                      ("checkout:refunds/../private.py",), ()):
            with self.subTest(paths=paths):
                wrong_scope = TaskContext("refund-idempotency", paths)
                self.assertFalse(matches_task(wrong_scope, CURRENT))
                self.assertEqual(self.compose(CURRENT, context=wrong_scope).outcome, "empty")
        self.assertTrue(matches_task(REFUND_TASK, CURRENT))
        term = replace(CURRENT, scope_paths=(), scope_terms=("refund writes",))
        self.assertEqual(self.compose(term, context=TaskContext("Update refund writes")).outcome, "packet")
        self.assertEqual(self.compose(term, context=TaskContext("Update refund writebacks")).outcome, "empty")

    def test_final_serialized_payload_budget_covers_unicode_and_escaping(self):
        multilingual = replace(CURRENT, rule='Use "idempotency" for 限定☃\n.')
        original = self.compose(multilingual)
        byte_count = len(original.serialized)
        self.assertEqual(self.compose(multilingual, max_tokens=byte_count).serialized, original.serialized)
        self.assertEqual(self.compose(multilingual, max_tokens=byte_count - 1).outcome, "empty")
        tiny = self.compose(multilingual, max_tokens=1)
        self.assertEqual(tiny.signals, ("budget-exhausted",))
        self.assertIsNone(tiny.payload)
        self.assertIsNone(tiny.serialized)
        self.assertFalse(tiny.released_versions)

    def test_packet_limits_are_bounded_and_unambiguous(self):
        for limits in ({"max_items": 0}, {"max_items": 25}, {"max_tokens": 4097}, {"max_tokens": True}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                self.compose(CURRENT, **limits)


if __name__ == "__main__":
    unittest.main()
