from __future__ import annotations

import json
import re
from typing import Any

from .security import redact_secrets
from .store import MemoryStore

DURABLE_TERMS = {
    "assigned",
    "deadline",
    "due",
    "decision",
    "decided",
    "milestone",
    "issue",
    "pull request",
    "merged",
    "status",
    "commitment",
    "owner",
    "launch",
    "blocked",
    "resolved",
}

IGNORED_TOOL_PARTS = {"ninai", "memory"}
OUTCOME_FIELDS = {
    "assignee",
    "assigned",
    "commitment",
    "deadline",
    "decision",
    "due",
    "id",
    "issue",
    "merged",
    "milestone",
    "number",
    "owner",
    "pull_request",
    "state",
    "status",
    "summary",
    "title",
    "url",
}


def compact_json(value: Any, max_chars: int = 2400) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    text = " ".join(text.split())
    return text[:max_chars]


def compact_outcome(event: dict[str, Any]) -> str | None:
    fields: list[tuple[str, str]] = []
    _collect_outcome_fields(event.get("tool_input", {}), fields)
    _collect_outcome_fields(event.get("tool_response", {}), fields)
    if fields:
        unique: list[str] = []
        seen: set[tuple[str, str]] = set()
        for key, value in fields:
            pair = (key, value)
            if pair in seen:
                continue
            seen.add(pair)
            unique.append(f"{key}={redact_secrets(value)}")
        return "; ".join(unique)[:2800]

    response = event.get("tool_response")
    if isinstance(response, str):
        sentences = re.split(r"(?<=[.!?])\s+|\n+", response)
        durable = [
            redact_secrets(sentence.strip())
            for sentence in sentences
            if any(term in sentence.lower() for term in DURABLE_TERMS)
        ]
        if durable:
            return " ".join(durable[:3])[:1200]
    return None


def _collect_outcome_fields(
    value: Any,
    fields: list[tuple[str, str]],
    *,
    prefix: str = "",
) -> None:
    if len(fields) >= 12:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            name = str(key).lower()
            path = f"{prefix}.{name}" if prefix else name
            if name in OUTCOME_FIELDS and not isinstance(child, (dict, list)):
                compact = " ".join(str(child).split())[:320]
                if compact:
                    fields.append((path, compact))
            elif isinstance(child, (dict, list)):
                _collect_outcome_fields(child, fields, prefix=path)
    elif isinstance(value, list):
        for child in value[:3]:
            _collect_outcome_fields(child, fields, prefix=prefix)


def event_to_memory(event: dict[str, Any]) -> dict[str, Any] | None:
    tool_name = str(event.get("tool_name", "unknown"))
    lower_tool = tool_name.lower()
    if any(part in lower_tool for part in IGNORED_TOOL_PARTS):
        return None

    tool_input = compact_json(event.get("tool_input", {}), 900)
    tool_response = compact_json(event.get("tool_response", {}), 1800)
    combined = f"{tool_name} {tool_input} {tool_response}".lower()
    if not any(term in combined for term in DURABLE_TERMS):
        return None

    outcome = compact_outcome(event)
    if outcome is None:
        return None
    content = re.sub(r"\s+", " ", f"Tool outcome from {tool_name}: {outcome}").strip()
    memory_type = "event"
    commitment_terms = ("deadline", "due", "assigned", "commitment", "owner")
    if any(term in combined for term in commitment_terms):
        memory_type = "commitment"
    elif any(term in combined for term in ("decision", "decided")):
        memory_type = "decision"
    return {
        "content": content,
        "memory_type": memory_type,
        "scope": "project",
        "source_uri": (
            f"claude-hook://{event.get('session_id', 'unknown')}"
            f"/{event.get('tool_use_id', 'tool')}"
        ),
        "importance": 0.55,
        "confidence": 0.8,
    }


def capture(event: dict[str, Any], store: MemoryStore | None = None) -> str | None:
    payload = event_to_memory(event)
    if payload is None:
        return None
    active_store = store or MemoryStore()
    existing = active_store.get_by_source_uri(str(payload["source_uri"]))
    if existing is not None:
        return str(existing["id"])
    memory = active_store.remember(**payload)
    return memory.id
