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
           ("user", "workspace", "project", "claude_client", "codex_client")}
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    credentials = {"claude": _token(), "codex": _token()}
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
        ):
            client_id = ids[id_key]
            db.execute("""INSERT INTO client_connections
                (id,workspace_id,user_id,provider,client_type,display_name)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (client_id, ids["workspace"], ids["user"], provider, client_type, display_name))
            db.execute("""INSERT INTO client_scope_grants
                (id,workspace_id,client_connection_id,scope_kind,scope_id,
                 can_read,can_propose,can_auto_activate,created_by_user_id)
                VALUES(%s,%s,%s,'project',%s,true,true,true,%s)""",
                (str(uuid.uuid4()), ids["workspace"], client_id, ids["project"], ids["user"]))
            raw = credentials["claude" if provider == "anthropic" else "codex"]
            db.execute("""INSERT INTO personal_access_tokens
                (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (str(uuid.uuid4()), ids["workspace"], ids["user"], client_id,
                 hashlib.sha256(raw.encode()).hexdigest(), display_name, expires_at))
    return {**ids, "project_scope_id": ids["project"], "expires_at": expires_at.isoformat(),
            "tokens": credentials}


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Ninai PAT clients (tokens print once)")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--email", required=True)
    parser.add_argument("--workspace", default="Personal Ninai")
    parser.add_argument("--project", default="Shared AI Memory")
    parser.add_argument("--expires-days", type=int, default=90)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    result = bootstrap(args.database_url, email=args.email, workspace_name=args.workspace,
                       project_name=args.project, expires_days=args.expires_days)
    print(json.dumps(result, indent=2))
    print("Store these tokens now; Ninai stores only their SHA-256 hashes.")


if __name__ == "__main__":
    main()
