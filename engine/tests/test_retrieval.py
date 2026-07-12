from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from ninai.retrieval import compose_context, rank_candidates


class RetrievalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    def candidate(self, **overrides: object) -> dict[str, object]:
        candidate: dict[str, object] = {
            "id": "memory-1",
            "content": "Finish the Ninai permission dashboard",
            "memory_type": "commitment",
            "scope": "project",
            "source_uri": "linear://NIN-42",
            "importance": 0.8,
            "confidence": 0.9,
            "updated_at": self.now.isoformat(),
            "access_count": 0,
        }
        candidate.update(overrides)
        return candidate

    def test_query_relevance_outweighs_unrelated_candidate(self) -> None:
        relevant = self.candidate(id="relevant")
        unrelated = self.candidate(
            id="unrelated",
            content="Prefer meetings after lunch",
            memory_type="preference",
        )

        ranked = rank_candidates(
            [unrelated, relevant],
            "Ninai permission dashboard",
            now=self.now,
        )

        self.assertEqual(ranked[0]["id"], "relevant")

    def test_type_aware_decay_keeps_decisions_fresher_than_events(self) -> None:
        old_time = (self.now - timedelta(days=90)).isoformat()
        event = self.candidate(id="event", memory_type="event", updated_at=old_time)
        decision = self.candidate(
            id="decision",
            memory_type="decision",
            updated_at=old_time,
        )

        ranked = rank_candidates(
            [event, decision],
            "Ninai permission dashboard",
            now=self.now,
        )

        self.assertEqual(ranked[0]["id"], "decision")

    def test_access_reinforcement_improves_equal_candidate_score(self) -> None:
        unused = self.candidate(id="unused")
        reinforced = self.candidate(id="reinforced", access_count=20)

        unused_score = rank_candidates(
            [unused], "Ninai permission dashboard", now=self.now
        )[0]["score"]
        reinforced_score = rank_candidates(
            [reinforced], "Ninai permission dashboard", now=self.now
        )[0]["score"]

        self.assertGreater(reinforced_score, unused_score)

    def test_context_composer_respects_item_and_token_limits(self) -> None:
        candidates = [
            {**self.candidate(id=f"memory-{index}"), "score": 1.0 - index / 10}
            for index in range(4)
        ]

        facts, estimated_tokens = compose_context(
            candidates,
            max_items=2,
            max_tokens=80,
        )

        self.assertLessEqual(len(facts), 2)
        self.assertLessEqual(estimated_tokens, 80)
        self.assertTrue(
            all(fact["source_uri"] == "linear://NIN-42" for fact in facts)
        )


if __name__ == "__main__":
    unittest.main()
