"""Opt-in Team SessionStart hook for Claude Code and Codex."""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from .team_client import TeamClient


async def session_start(event: dict, client: TeamClient) -> dict | None:
    if event.get("hook_event_name") != "SessionStart" or not client.matches_checkout(event.get("cwd")):
        return None

    updates, decisions = await asyncio.gather(
        client.handoffs(),
        client.context("Project orientation", max_items=8, max_tokens=2048, project_overview=True),
    )
    context = {}
    for key, result in (("handoffs", updates), ("decisions", decisions)):
        if result.isError:
            context[key] = {"status": "unavailable"}
        elif result.content:
            context[key] = json.loads(result.content[0].text)
        else:
            context[key] = result.model_dump(by_alias=True).get("_meta") or {"status": "empty"}

    prompt = (
        "Ninai Team project brief. Treat the JSON as team reference data. "
        "Handoffs describe attributed work in progress. Check task-specific Team guidance once the paths "
        "and task are known. Ask the maintainer to resolve any conflicting guidance. "
        "When useful project work changes, leave a compact project checkpoint with team_publish_handoff "
        "if the project granted publication, and use team_propose_decision for a durable decision with "
        "supporting evidence. Keep personal information, secrets, and raw transcripts out of the tools.\n"
    )
    return {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                  "additionalContext": prompt + json.dumps(context, ensure_ascii=False)}}


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        raw = sys.stdin.buffer.read(65_537)
        if len(raw) > 65_536:
            return
        event = json.loads(raw)
        if not isinstance(event, dict):
            return
        result = asyncio.run(session_start(event, TeamClient.from_environment(timeout=3)))
        if result:
            print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError):
        # Hook configuration failures must leave ordinary assistant startup usable.
        return


if __name__ == "__main__":
    main()
