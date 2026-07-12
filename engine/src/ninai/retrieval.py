from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Iterable

HALF_LIFE_DAYS = {
    "event": 14.0,
    "commitment": 45.0,
    "decision": 180.0,
    "fact": 365.0,
    "preference": 365.0,
    "procedure": 730.0,
}

PACT_WEIGHTS = {
    "lexical": 0.34,
    "search_position": 0.18,
    "freshness": 0.16,
    "importance": 0.14,
    "confidence": 0.12,
    "reinforcement": 0.06,
}


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def rank_candidates(
    candidates: Iterable[dict[str, object]],
    query: str,
    *,
    now: datetime | None = None,
) -> list[dict[str, object]]:
    query_terms = set(re.findall(r"[a-z0-9_-]+", query.lower()))
    reference_time = now or datetime.now(timezone.utc)
    ranked: list[dict[str, object]] = []

    for position, item in enumerate(candidates):
        content_terms = set(
            re.findall(r"[a-z0-9_-]+", str(item["content"]).lower())
        )
        lexical = len(query_terms & content_terms) / max(1, len(query_terms))
        freshness = _freshness(item, reference_time)
        reinforcement = min(1.0, math.log1p(int(item.get("access_count", 0))) / 6)
        search_position = 1 / (1 + position)
        score = (
            PACT_WEIGHTS["lexical"] * lexical
            + PACT_WEIGHTS["search_position"] * search_position
            + PACT_WEIGHTS["freshness"] * freshness
            + PACT_WEIGHTS["importance"] * float(item["importance"])
            + PACT_WEIGHTS["confidence"] * float(item["confidence"])
            + PACT_WEIGHTS["reinforcement"] * reinforcement
        )
        enriched = dict(item)
        enriched["score"] = score
        ranked.append(enriched)

    return sorted(
        ranked,
        key=lambda candidate: float(candidate["score"]),
        reverse=True,
    )


def compose_context(
    ranked: Iterable[dict[str, object]],
    *,
    max_items: int,
    max_tokens: int,
) -> tuple[list[dict[str, object]], int]:
    selected: list[dict[str, object]] = []
    token_total = 0

    for item in ranked:
        fact = {
            "id": item["id"],
            "content": item["content"],
            "type": item["memory_type"],
            "scope": item["scope"],
            "source_uri": item["source_uri"],
            "confidence": item["confidence"],
            "updated_at": item["updated_at"],
            "score": round(float(item["score"]), 4),
        }
        # Estimate from the full serialized fact so source_uri and metadata are
        # counted against the budget, not just the content string. This keeps
        # the returned packet within the requested token budget.
        fact_tokens = estimate_tokens(json.dumps(fact, ensure_ascii=False))
        if fact_tokens > max_tokens - token_total:
            continue
        selected.append(fact)
        token_total += fact_tokens
        if len(selected) >= max_items:
            break

    return selected, token_total


def _freshness(item: dict[str, object], now: datetime) -> float:
    try:
        updated = datetime.fromisoformat(str(item["updated_at"]))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - updated).total_seconds() / 86400)
    except ValueError:
        age_days = 365.0
    half_life = HALF_LIFE_DAYS.get(str(item["memory_type"]), 180.0)
    return math.exp(-math.log(2) * age_days / half_life)
