from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ninai.hook_capture import capture
from ninai.retrieval import estimate_tokens
from ninai.store import MemoryStore


def run_verification(database: Path) -> None:
    store = MemoryStore(database)
    client_id = "claude-code"
    event = {
        "session_id": "mvp-verification",
        "tool_use_id": "linear-NIN-42",
        "tool_name": "mcp__linear__get_issue",
        "tool_input": {"issue": "NIN-42"},
        "tool_response": {
            "title": "Prepare Ninai permission dashboard",
            "status": "assigned",
            "due": "2026-07-18",
            "owner": "Darshan",
            "description": "Detailed source material " * 180,
        },
    }

    store.grant(client_id, "project")
    memory_id = capture(event, store)
    packet = store.recall(
        "What must I finish before the Ninai launch?",
        client_id=client_id,
        purpose="release verification",
        max_tokens=300,
    )
    source_tokens = estimate_tokens(json.dumps(event, ensure_ascii=False))
    released_tokens = int(packet["estimated_tokens"])
    reduction = 100 * (1 - released_tokens / max(1, source_tokens))

    print("CAPTURED")
    print(json.dumps({"memory_id": memory_id, "database": str(database)}, indent=2))
    print("\nPERMITTED RECALL")
    print(json.dumps(packet, indent=2, ensure_ascii=False))
    print("\nCONTEXT REDUCTION")
    print(
        json.dumps(
            {
                "source_estimated_tokens": source_tokens,
                "released_estimated_tokens": released_tokens,
                "reduction_percent": round(reduction, 1),
            },
            indent=2,
        )
    )

    store.revoke(client_id, "project")
    denied = store.recall(
        "What must I finish before the Ninai launch?",
        client_id=client_id,
        purpose="revocation proof",
        max_tokens=300,
    )
    print("\nREVOKED RECALL")
    print(json.dumps(denied, indent=2, ensure_ascii=False))
    print("\nACCESS LOG")
    print(json.dumps(store.list_logs(), indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the deterministic Ninai MVP flow")
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    if args.data_dir:
        args.data_dir.mkdir(parents=True, exist_ok=True)
        run_verification(args.data_dir / "ninai-verification.sqlite3")
        return
    with tempfile.TemporaryDirectory() as directory:
        run_verification(Path(directory) / "ninai-verification.sqlite3")


if __name__ == "__main__":
    main()
