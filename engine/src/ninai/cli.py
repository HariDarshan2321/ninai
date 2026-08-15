from __future__ import annotations

import argparse
import json
import sys

from .config import client_id as configured_client_id
from .hook_capture import capture
from .session_capture import handle_lifecycle_event
from .store import ALLOWED_SCOPES, MemoryStore


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="ninai", description="Ninai local memory CLI")
    sub = root.add_subparsers(dest="command", required=True)

    permission = sub.add_parser("permission", help="Manage client memory scopes")
    permission_sub = permission.add_subparsers(dest="action", required=True)
    for action in ("grant", "revoke"):
        command = permission_sub.add_parser(action)
        command.add_argument("client_id")
        command.add_argument("scope", choices=sorted(ALLOWED_SCOPES))
    list_permissions = permission_sub.add_parser("list")
    list_permissions.add_argument("client_id")

    remember = sub.add_parser("remember", help="Store a manual memory")
    remember.add_argument("content")
    remember.add_argument("--type", default="fact", dest="memory_type")
    remember.add_argument("--scope", default="project", choices=sorted(ALLOWED_SCOPES))
    remember.add_argument("--source", default="cli://manual", dest="source_uri")

    recall = sub.add_parser("recall", help="Test a context packet")
    recall.add_argument("query")
    recall.add_argument("--client", default=configured_client_id(), dest="client_id")
    recall.add_argument("--purpose", default="manual CLI test")
    recall.add_argument("--max-tokens", type=int, default=600)

    sub.add_parser("memories", help="List recent memories")
    sub.add_parser("logs", help="List recent access logs")
    sub.add_parser("doctor", help="Show vault status")

    hook = sub.add_parser("capture-hook", help="Read a Claude Code hook event from stdin")
    hook.add_argument("--quiet", action="store_true")
    lifecycle = sub.add_parser("session-hook", help="Read a Claude Code or Codex lifecycle hook event")
    lifecycle.add_argument("--provider", required=True, choices=("claude-code", "codex"))
    capture_setting = sub.add_parser("capture", help="Manage automatic session archiving consent")
    capture_setting.add_argument("action", choices=("enable", "disable", "status"))
    sessions = sub.add_parser("sessions", help="Export or delete local session archives")
    sessions.add_argument("action", choices=("export", "delete"))
    sessions.add_argument("session_id", nargs="?")
    return root


def main() -> None:
    args = parser().parse_args()
    store = MemoryStore()

    if args.command == "permission":
        if args.action == "grant":
            store.grant(args.client_id, args.scope)
            print(f"Granted {args.client_id!r} access to {args.scope!r}.")
        elif args.action == "revoke":
            store.revoke(args.client_id, args.scope)
            print(f"Revoked {args.client_id!r} access to {args.scope!r}.")
        else:
            print(json.dumps(store.permissions(args.client_id), indent=2))
        return

    if args.command == "remember":
        try:
            memory = store.remember(
                args.content,
                memory_type=args.memory_type,
                scope=args.scope,
                source_uri=args.source_uri,
            )
        except ValueError as error:
            print(json.dumps({"stored": False, "error": str(error)}, indent=2))
            sys.exit(1)
        print(json.dumps({"stored": True, "id": memory.id}, indent=2))
        return

    if args.command == "recall":
        print(
            json.dumps(
                store.recall(
                    args.query,
                    client_id=args.client_id,
                    purpose=args.purpose,
                    max_tokens=args.max_tokens,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if args.command == "memories":
        print(json.dumps(store.list_memories(), indent=2, ensure_ascii=False))
        return

    if args.command == "logs":
        print(json.dumps(store.list_logs(), indent=2, ensure_ascii=False))
        return

    if args.command == "doctor":
        print(json.dumps(store.status(configured_client_id()), indent=2))
        return

    if args.command == "capture-hook":
        try:
            event = json.load(sys.stdin)
            memory_id = capture(event, store)
        except Exception:
            return
        if not args.quiet:
            print(json.dumps({"captured": memory_id is not None, "memory_id": memory_id}))
        return

    if args.command == "session-hook":
        try:
            event = json.load(sys.stdin)
            output = handle_lifecycle_event(event, provider=args.provider, store=store)
        except Exception:
            return
        if output:
            print(json.dumps(output, ensure_ascii=False))
        return

    if args.command == "capture":
        if args.action == "enable":
            store.set_capture_enabled(True)
        elif args.action == "disable":
            store.set_capture_enabled(False)
        print(json.dumps({"session_capture": store.capture_enabled()}))
        return

    if args.command == "sessions":
        if args.action == "export":
            print(json.dumps({"sessions": store.export_sessions()}, indent=2, ensure_ascii=False))
        else:
            if not args.session_id:
                raise SystemExit("sessions delete requires a session_id")
            print(json.dumps({"deleted": store.delete_session(args.session_id)}))
        return


if __name__ == "__main__":
    main()
