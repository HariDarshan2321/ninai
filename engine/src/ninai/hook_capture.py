from __future__ import annotations

import json
import os
import re
from typing import Any

from .security import redact_secrets
from .store import MemoryStore
from .session_capture import _project_identity

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

RESULT_ENVELOPES = {"result", "data", "structuredcontent", "structured_content"}
DURABLE_FIELDS = {"assignee", "assigned", "commitment", "deadline", "decision", "due", "merged", "milestone", "owner"}
DURABLE_STATES = {"assigned", "blocked", "closed", "completed", "done", "in_progress", "merged", "resolved"}
FAILED_STATES = {"error", "failed", "failure", "cancelled", "canceled", "timeout", "denied"}


def _decoded_response(value: Any) -> dict[str, Any] | None:
    """Accept structured results, never promote arbitrary output text to memory."""
    if isinstance(value, str):
        if len(value) > 65536:
            return None
        try:
            value = json.loads(value)
        except (ValueError, RecursionError):
            return None
    return value if isinstance(value, dict) else None


def _failed_response(value: Any, depth: int = 0) -> bool:
    # Fail closed on excessively nested results and inspect MCP text envelopes
    # as well as structuredContent. An attempted write is not a completed one.
    if depth > 8:
        return True
    if isinstance(value, str):
        decoded = _decoded_response(value)
        return decoded is not None and _failed_response(decoded, depth + 1)
    if isinstance(value, dict):
        if len(value) > 100:
            return True
        for key, child in value.items():
            name = str(key).lower()
            if name in {"iserror", "is_error"} and child is True:
                return True
            if name in {"success", "ok"} and child is False:
                return True
            if name == "error" and child:
                return True
            if name in {"status", "state"} and isinstance(child, str) and child.lower() in FAILED_STATES:
                return True
            if isinstance(child, (dict, list)) or name in RESULT_ENVELOPES | {"text"}:
                if _failed_response(child, depth + 1):
                    return True
    elif isinstance(value, list):
        if len(value) > 100:
            return True
        return any(_failed_response(child, depth + 1) for child in value)
    return False


def compact_json(value: Any, max_chars: int = 2400) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    text = " ".join(text.split())
    return text[:max_chars]


def compact_outcome(event: dict[str, Any]) -> str | None:
    response = _decoded_response(event.get("tool_response"))
    if response is None or _failed_response(response):
        return None
    # Query rows are source material, even when columns happen to be called
    # status, owner or id. Capture an explicit decision separately instead.
    action = str(event.get("tool_name", "")).lower().split("__")[-1]
    if re.search(r"(?:^|_)(?:query|queries|sql|select)(?:_|$)", action):
        return None
    result_fields: list[tuple[str, str]] = []
    _collect_outcome_fields(response, result_fields)
    meaningful = any(
        key.split(".")[-1] in DURABLE_FIELDS
        or (key.split(".")[-1] in {"status", "state"} and value.lower() in DURABLE_STATES)
        for key, value in result_fields
    )
    input_fields: list[tuple[str, str]] = []
    _collect_outcome_fields(event.get("tool_input", {}), input_fields)
    mutating = re.match(r"(?:create|update|save|set|assign|resolve|close|merge|commit|schedule)(?:_|$)", action)
    # A successful write may return only its new identity. Require a useful
    # named outcome in its input as well; generic id/status is insufficient.
    write_outcome = bool(mutating and result_fields and any(
        key.split(".")[-1] in DURABLE_FIELDS | {"title", "summary"}
        for key, _ in input_fields
    ))
    if not meaningful and not write_outcome:
        return None
    fields: list[tuple[str, str]] = []
    fields.extend(input_fields)
    fields.extend(result_fields)
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
                compact = " ".join(str(child).split())[:320] if child is not None else ""
                if compact:
                    fields.append((path, compact))
            elif name in RESULT_ENVELOPES and isinstance(child, dict):
                _collect_outcome_fields(child, fields, prefix=path)
            elif name == "content" and isinstance(child, list):
                for block in child[:3]:
                    if isinstance(block, dict) and block.get("type") == "text":
                        decoded = _decoded_response(block.get("text"))
                        if decoded is not None:
                            _collect_outcome_fields(decoded, fields, prefix=path)


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
    name, binding, root = _project_identity(str(event.get("cwd") or os.getcwd()))
    project = active_store.ensure_project(name=name, binding_key=binding, cwd_or_repo=root)
    payload["project_id"] = str(project["id"])
    memory = active_store.remember(**payload)
    return memory.id
