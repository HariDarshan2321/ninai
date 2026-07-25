#!/usr/bin/env python3
"""Verify Ninai's hosted cross-provider semantics against PostgreSQL.

This is a deterministic service-level acceptance test. It models Claude Code
and Codex as distinct hosted client connections; it does not invoke either
vendor's model or host application.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud" / "src"))

from ninai_cloud.migrations import apply_migrations
from ninai_cloud.postgres_store import AuthorizationError, PostgresStore, Principal


NAMESPACE = uuid.UUID("2caa28f8-71b7-4cb1-b351-854892c22620")
ID_NAMES = (
    "user", "workspace", "shared-project", "private-project", "claude-client",
    "codex-client", "claude-grant", "codex-grant", "private-grant",
)


def _ids(run_id: str) -> dict[str, str]:
    """Return stable fixture IDs isolated to one verifier invocation."""
    run_namespace = uuid.uuid5(NAMESPACE, run_id)
    return {name: str(uuid.uuid5(run_namespace, name)) for name in ID_NAMES}


def _delete_fixture(db: Any, ids: dict[str, str]) -> None:
    workspace, user = ids["workspace"], ids["user"]
    for table in (
        "disclosure_logs", "memory_feedback", "idempotency_keys", "memory_relations",
        "memory_sources", "memories", "client_scope_grants", "client_connections", "projects",
        "workspace_members",
    ):
        db.execute(f"DELETE FROM {table} WHERE workspace_id=%s", (workspace,))
    db.execute("DELETE FROM workspaces WHERE id=%s", (workspace,))
    db.execute("DELETE FROM users WHERE id=%s", (user,))


def _seed(
    database_url: str, ids: dict[str, str], run_id: str,
) -> tuple[PostgresStore, Principal, Principal]:
    import psycopg

    fixture_key = uuid.uuid5(NAMESPACE, run_id).hex
    apply_migrations(database_url)
    with psycopg.connect(database_url) as db:
        _delete_fixture(db, ids)
        db.execute(
            "INSERT INTO users(id,email,display_name) VALUES(%s,%s,'Acceptance Owner')",
            (ids["user"], f"cross-provider-{fixture_key}@ninai.invalid"),
        )
        db.execute(
            "INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES(%s,'Acceptance',%s,%s)",
            (ids["workspace"], f"cross-provider-{fixture_key}", ids["user"]),
        )
        db.execute(
            "INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')",
            (ids["workspace"], ids["user"]),
        )
        db.execute(
            "INSERT INTO projects(id,workspace_id,name,slug) VALUES(%s,%s,'Shared','shared')",
            (ids["shared-project"], ids["workspace"]),
        )
        db.execute(
            "INSERT INTO projects(id,workspace_id,name,slug) VALUES(%s,%s,'Claude private','claude-private')",
            (ids["private-project"], ids["workspace"]),
        )
        db.execute(
            """INSERT INTO client_connections
               (id,workspace_id,user_id,provider,client_type,display_name)
               VALUES(%s,%s,%s,'anthropic','claude-code','Claude Code'),
                     (%s,%s,%s,'openai','codex','Codex')""",
            (ids["claude-client"], ids["workspace"], ids["user"],
             ids["codex-client"], ids["workspace"], ids["user"]),
        )
        grants = (
            (ids["claude-grant"], ids["claude-client"], ids["shared-project"]),
            (ids["codex-grant"], ids["codex-client"], ids["shared-project"]),
            (ids["private-grant"], ids["claude-client"], ids["private-project"]),
        )
        for grant_id, client_id, project_id in grants:
            db.execute(
                """INSERT INTO client_scope_grants
                   (id,workspace_id,client_connection_id,scope_kind,scope_id,
                    can_read,can_propose,can_auto_activate,created_by_user_id)
                   VALUES(%s,%s,%s,'project',%s,true,true,true,%s)""",
                (grant_id, ids["workspace"], client_id, project_id, ids["user"]),
            )

    store = PostgresStore(database_url)
    return (
        store,
        Principal(ids["user"], ids["workspace"], ids["claude-client"]),
        Principal(ids["user"], ids["workspace"], ids["codex-client"]),
    )


def run_verification(
    database_url: str, *, cleanup: bool = True, run_id: str | None = None,
) -> dict[str, Any]:
    """Run the release-gate semantics and return a machine-readable report."""
    import psycopg
    from psycopg.rows import dict_row

    run_id = run_id or uuid.uuid4().hex
    ids = _ids(run_id)
    store, claude, codex = _seed(database_url, ids, run_id)
    checks: dict[str, bool] = {}
    try:
        claude_memory = store.create_memory(
            claude, content="The launch theme is shared continuity", memory_type="decision",
            scope_kind="project", scope_id=ids["shared-project"], project_id=ids["shared-project"],
            source_uri="claude-code://session/acceptance/turn-1",
            idempotency_key="acceptance-claude-to-codex", activate=True,
        )
        codex_results = store.search(codex, "shared continuity")
        checks["claude_to_openai"] = [m.id for m in codex_results] == [claude_memory.id]
        checks["claude_source_preserved"] = (
            len(codex_results) == 1
            and codex_results[0].source_uri == "claude-code://session/acceptance/turn-1"
        )
        checks["claude_scope_preserved"] = (
            len(codex_results) == 1
            and codex_results[0].scope_kind == "project"
            and codex_results[0].scope_id == ids["shared-project"]
        )
        store.record_disclosure(
            codex, tool_name="search", query="shared continuity", purpose="cross-provider acceptance",
            returned_memory_ids=[m.id for m in codex_results], request_id="acceptance-codex-read",
        )

        codex_memory = store.create_memory(
            codex, content="The verified release command is make acceptance", memory_type="fact",
            scope_kind="project", scope_id=ids["shared-project"], project_id=ids["shared-project"],
            source_uri="codex://task/acceptance/turn-2",
            idempotency_key="acceptance-codex-to-claude", activate=True,
        )
        claude_results = store.search(claude, "verified release command")
        checks["openai_to_claude"] = [m.id for m in claude_results] == [codex_memory.id]
        checks["openai_source_preserved"] = (
            len(claude_results) == 1
            and claude_results[0].source_uri == "codex://task/acceptance/turn-2"
        )
        checks["openai_scope_preserved"] = (
            len(claude_results) == 1
            and claude_results[0].scope_kind == "project"
            and claude_results[0].scope_id == ids["shared-project"]
        )
        store.record_disclosure(
            claude, tool_name="search", query="verified release command",
            purpose="cross-provider acceptance", returned_memory_ids=[m.id for m in claude_results],
            request_id="acceptance-claude-read",
        )

        private = store.create_memory(
            claude, content="Claude private marker zephyr", memory_type="fact",
            scope_kind="project", scope_id=ids["private-project"], project_id=ids["private-project"],
            source_uri="claude-code://session/acceptance/private",
            idempotency_key="acceptance-private-scope", activate=True,
        )
        checks["openai_scope_denied"] = (
            store.get_memory(codex, private.id) is None and store.search(codex, "zephyr") == []
        )
        checks["claude_scope_allowed"] = store.get_memory(claude, private.id) is not None

        checks["openai_revoked"] = store.revoke_client(
            ids["workspace"], ids["codex-client"], ids["user"]
        )
        try:
            store.search(codex, "shared continuity")
        except AuthorizationError:
            checks["openai_denied_after_revoke"] = True
        else:
            checks["openai_denied_after_revoke"] = False
        checks["claude_continues_after_openai_revoke"] = (
            [m.id for m in store.search(claude, "verified release command")] == [codex_memory.id]
        )

        with psycopg.connect(database_url, row_factory=dict_row) as db:
            rows = db.execute(
                """SELECT request_id,decision,returned_memory_ids,allowed_scope_snapshot
                   FROM disclosure_logs WHERE workspace_id=%s ORDER BY request_id""",
                (ids["workspace"],),
            ).fetchall()
        checks["disclosures_audited"] = (
            len(rows) == 2
            and {row["request_id"] for row in rows}
            == {"acceptance-codex-read", "acceptance-claude-read"}
            and all(row["decision"] == "allow" and row["returned_memory_ids"] for row in rows)
        )

        passed = all(checks.values())
        report = {
            "gate": "hosted-cross-provider-service-semantics",
            "passed": passed,
            "host_invocation": "not_run",
            "clients": {
                "writer_1": {"provider": "anthropic", "client_type": "claude-code"},
                "writer_2": {"provider": "openai", "client_type": "codex"},
            },
            "checks": checks,
        }
        if not passed:
            failed = ", ".join(name for name, ok in checks.items() if not ok)
            raise AssertionError(f"Cross-provider acceptance failed: {failed}")
        return report
    finally:
        if cleanup:
            with psycopg.connect(database_url) as db:
                _delete_fixture(db, ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("NINAI_TEST_DATABASE_URL"))
    parser.add_argument("--output", type=Path, help="Also write the JSON report to this path")
    parser.add_argument("--keep-fixture", action="store_true", help="Keep acceptance rows for inspection")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("set NINAI_TEST_DATABASE_URL or pass --database-url")
    report = run_verification(args.database_url, cleanup=not args.keep_fixture)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
