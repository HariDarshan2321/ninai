from __future__ import annotations

import json
import os
import subprocess
import re
from pathlib import Path
from typing import Any

from .security import redact_secrets
from .store import MemoryStore

MAX_TRANSCRIPT_BYTES = 1_000_000
MAX_ARCHIVE_CHARS = 120_000
SUPPORTED_PROVIDERS = {"claude-code", "codex"}


def _safe_remote(value: str) -> str:
    return re.sub(r"(://)[^/@\s]+@", r"\1", redact_secrets(value))[:1000]


def _project_identity(cwd: str) -> tuple[str, str, str]:
    root = Path(cwd or os.getcwd()).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            root = Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    remote = ""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if result.returncode == 0:
            remote = _safe_remote(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    binding = f"repo:{remote}" if remote else f"path:{root}"
    return root.name or "Inbox", binding, str(root)


def _message_text(value: Any) -> list[str]:
    """Extract conversation text while excluding tool calls, results, and metadata."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict) and str(item.get("type", "")).lower() not in {
                "text", "input_text", "output_text",
            }:
                continue
            result.extend(_message_text(item.get("text") if isinstance(item, dict) else item))
        return result
    if isinstance(value, dict):
        for key in ("content", "text", "message"):
            if key in value:
                return _message_text(value[key])
    return []


def normalize_transcript(raw: str) -> str | None:
    """Return a compact, redacted user/assistant archive from common JSONL formats."""
    messages: list[str] = []
    parsed_json = False
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (TypeError, ValueError):
            continue
        parsed_json = True
        candidates = [item]
        if isinstance(item, dict):
            candidates.extend(
                value for key in ("payload", "message", "response_item")
                if isinstance((value := item.get(key)), dict)
            )
        for candidate in candidates:
            role = str(candidate.get("role", "")).lower()
            if role not in {"user", "assistant"}:
                continue
            parts = [" ".join(part.split()) for part in _message_text(candidate) if part.strip()]
            if parts:
                messages.append(f"{role}: {' '.join(parts)}")
                break
    if not parsed_json:
        messages = [" ".join(line.split()) for line in raw.splitlines() if line.strip()]
    if not messages:
        return None
    return redact_secrets("\n".join(messages)[-MAX_ARCHIVE_CHARS:])


def _read_transcript(path_value: Any) -> str | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    path = Path(path_value).expanduser()
    try:
        if not path.is_file():
            return None
        with path.open("rb") as handle:
            data = handle.read(MAX_TRANSCRIPT_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_TRANSCRIPT_BYTES:
        data = data[-MAX_TRANSCRIPT_BYTES:]
    return normalize_transcript(data.decode("utf-8", "replace"))


def handle_lifecycle_event(
    event: dict[str, Any], *, provider: str, store: MemoryStore | None = None
) -> dict[str, Any] | None:
    if provider not in SUPPORTED_PROVIDERS:
        return None
    active_store = store or MemoryStore()
    if not active_store.capture_enabled():
        return None
    event_name = str(event.get("hook_event_name") or event.get("event") or "")
    session_id = str(event.get("session_id") or "").strip()
    if not session_id:
        return None
    name, binding, root = _project_identity(str(event.get("cwd") or os.getcwd()))
    project = active_store.ensure_project(name=name, binding_key=binding, cwd_or_repo=root)
    source_uri = f"session://{provider}/{session_id}"
    if event_name == "SessionStart":
        active_store.capture_session(
            provider=provider, external_session_id=session_id, project_id=str(project["id"]),
            title=f"{name} session", source_uri=source_uri, cwd_or_repo=root, status="started",
        )
        packet = active_store.session_context(
            project_id=str(project["id"]), client_id=provider, max_tokens=600
        )
        if not packet["sessions"]:
            return None
        lines = ["NINAI PROJECT CONTEXT", f"Project: {name}"]
        for item in packet["sessions"]:
            lines.extend((f"Source: {item['source_uri']}", str(item["context"])))
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n\n".join(lines),
            }
        }
    if event_name not in {"Stop", "SessionEnd"}:
        return None
    transcript = _read_transcript(event.get("transcript_path"))
    active_store.capture_session(
        provider=provider, external_session_id=session_id, project_id=str(project["id"]),
        title=f"{name} session", source_uri=source_uri, cwd_or_repo=root,
        status="completed" if event_name == "SessionEnd" else "checkpointed",
        transcript=transcript,
    )
    return None


def main(provider: str) -> int:
    try:
        event = json.load(__import__("sys").stdin)
        output = handle_lifecycle_event(event, provider=provider)
        if output:
            print(json.dumps(output, ensure_ascii=False))
    except Exception:
        # Lifecycle capture must never break the user's coding session.
        return 0
    return 0
