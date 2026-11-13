"""One-shot bootstrap for a small self-hosted Claude/Codex workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .migrations import apply_migrations


def _token() -> str:
    return "ninai_pat_" + secrets.token_urlsafe(32)


def bootstrap(database_url: str, *, email: str, workspace_name: str,
              project_name: str, expires_days: int = 90) -> dict[str, Any]:
    if expires_days < 1 or expires_days > 3650:
        raise ValueError("expires_days must be between 1 and 3650")
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install ninai-cloud to bootstrap hosted mode") from exc
    apply_migrations(database_url)
    ids = {name: str(uuid.uuid4()) for name in
           ("user", "workspace", "project", "claude_client", "codex_client", "operator_client")}
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    credentials = {"claude": _token(), "codex": _token(), "operator": _token()}
    slug_suffix = ids["workspace"].split("-")[0]
    slug = "-".join(workspace_name.lower().split())[:40].strip("-") or "ninai"
    slug = f"{slug}-{slug_suffix}"
    with psycopg.connect(database_url) as db:
        db.execute("INSERT INTO users(id,email,display_name) VALUES(%s,%s,%s)",
                   (ids["user"], email, email.split("@", 1)[0]))
        db.execute("INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES(%s,%s,%s,%s)",
                   (ids["workspace"], workspace_name, slug, ids["user"]))
        db.execute("INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')",
                   (ids["workspace"], ids["user"]))
        db.execute("INSERT INTO projects(id,workspace_id,name,slug) VALUES(%s,%s,%s,%s)",
                   (ids["project"], ids["workspace"], project_name,
                    ("-".join(project_name.lower().split())[:40].strip("-") or "project")))
        for provider, client_type, display_name, id_key in (
            ("anthropic", "claude-code", "Claude Code", "claude_client"),
            ("openai", "codex", "Codex", "codex_client"),
            ("ninai", "control-owner", "Owner control (never give to an AI client)", "operator_client"),
        ):
            client_id = ids[id_key]
            db.execute("""INSERT INTO client_connections
                (id,workspace_id,user_id,provider,client_type,display_name)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (client_id, ids["workspace"], ids["user"], provider, client_type, display_name))
            if provider != "ninai":
                db.execute("""INSERT INTO client_scope_grants
                    (id,workspace_id,client_connection_id,scope_kind,scope_id,
                     can_read,can_propose,can_auto_activate,created_by_user_id)
                    VALUES(%s,%s,%s,'project',%s,true,true,true,%s)""",
                    (str(uuid.uuid4()), ids["workspace"], client_id, ids["project"], ids["user"]))
            raw = credentials[{"anthropic": "claude", "openai": "codex", "ninai": "operator"}[provider]]
            db.execute("""INSERT INTO personal_access_tokens
                (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (str(uuid.uuid4()), ids["workspace"], ids["user"], client_id,
                 hashlib.sha256(raw.encode()).hexdigest(), display_name, expires_at))
    return {**ids, "project_scope_id": ids["project"], "expires_at": expires_at.isoformat(),
            "tokens": credentials,
            "control_pat_sha256": hashlib.sha256(credentials["operator"].encode()).hexdigest()}


def issue_control_credential(database_url: str, *, workspace_id: str, user_id: str,
                             expires_days: int = 90) -> dict[str, Any]:
    """Privileged DB-operator migration: issue a console-only owner credential."""
    if not 1 <= expires_days <= 3650:
        raise ValueError("expires_days must be between 1 and 3650")
    workspace_id, user_id = str(uuid.UUID(workspace_id)), str(uuid.UUID(user_id))
    import psycopg
    apply_migrations(database_url)
    raw, client_id = _token(), str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    with psycopg.connect(database_url) as db:
        active = db.execute("""SELECT 1 FROM workspace_members m
            JOIN users u ON u.id=m.user_id JOIN workspaces w ON w.id=m.workspace_id
            WHERE m.workspace_id=%s AND m.user_id=%s AND m.revoked_at IS NULL
              AND m.role IN ('owner','admin') AND u.deleted_at IS NULL AND w.deleted_at IS NULL""",
            (workspace_id, user_id)).fetchone()
        if not active:
            raise ValueError("An active workspace owner or admin is required")
        db.execute("""INSERT INTO client_connections
            (id,workspace_id,user_id,provider,client_type,display_name)
            VALUES(%s,%s,%s,'ninai','control-owner','Owner control (never give to an AI client)')""",
            (client_id, workspace_id, user_id))
        digest = hashlib.sha256(raw.encode()).hexdigest()
        db.execute("""INSERT INTO personal_access_tokens
            (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
            VALUES(%s,%s,%s,%s,%s,'Dedicated owner control',%s)""",
            (str(uuid.uuid4()), workspace_id, user_id, client_id, digest, expires_at))
    return {"workspace": workspace_id, "user": user_id, "operator_client": client_id,
            "tokens": {"operator": raw}, "control_pat_sha256": digest,
            "expires_at": expires_at.isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Ninai PAT clients (tokens print once)")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--email")
    parser.add_argument("--operator-workspace", help="Issue only an operator credential for this existing workspace UUID")
    parser.add_argument("--operator-user", help="Existing active owner/admin UUID for --operator-workspace")
    parser.add_argument("--workspace", default="Personal Ninai")
    parser.add_argument("--project", default="Shared AI Memory")
    parser.add_argument("--expires-days", type=int, default=90)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    if args.operator_workspace or args.operator_user:
        if not args.operator_workspace or not args.operator_user or args.email:
            parser.error("--operator-workspace and --operator-user must be supplied together, without --email")
        result = issue_control_credential(args.database_url, workspace_id=args.operator_workspace,
            user_id=args.operator_user, expires_days=args.expires_days)
    else:
        if not args.email:
            parser.error("--email is required when creating a workspace")
        result = bootstrap(args.database_url, email=args.email, workspace_name=args.workspace,
                           project_name=args.project, expires_days=args.expires_days)
    print(json.dumps(result, indent=2))
    print("Store these tokens now; Ninai stores only their SHA-256 hashes.")


if __name__ == "__main__":
    main()
