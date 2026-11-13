"""Operator-only storage inventory and explicit session-retention maintenance.

Run with the private database credential in DATABASE_URL. Output contains row
counts and byte estimates, never memory content, queries, or bearer credentials.
Audit records and memory tombstones are never pruned by this command.
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from typing import Any

from .postgres_store import PostgresStore

TABLES = (
    "memories", "memory_sources", "idempotency_keys", "sessions", "session_artifacts",
    "disclosure_logs", "session_disclosure_logs", "client_connections", "client_scope_grants",
)


def storage_report(store: PostgresStore, workspace_id: str, *, apply_retention: bool = False) -> dict[str, Any]:
    workspace_id = str(uuid.UUID(workspace_id))
    with store._connection() as db:
        # Match capture/delete locking so retention and incoming writes cannot
        # race to resurrect an expired artifact or invalidate the inventory.
        store._lock_workspace(db, workspace_id)
        workspace = db.execute("SELECT id FROM workspaces WHERE id=%s", (workspace_id,)).fetchone()
        if not workspace:
            raise ValueError("Workspace not found")
        tables = {}
        for table in TABLES:
            row = db.execute(
                f"SELECT count(*) rows,COALESCE(sum(pg_column_size(t)),0) bytes FROM {table} t WHERE workspace_id=%s",
                (workspace_id,),
            ).fetchone()
            tables[table] = {"rows": int(row["rows"]), "estimated_row_bytes": int(row["bytes"])}
        expired = db.execute(
            """SELECT count(*) rows,COALESCE(sum(octet_length(a.content)),0) bytes
               FROM session_artifacts a JOIN sessions s
                 ON s.workspace_id=a.workspace_id AND s.id=a.session_id
               LEFT JOIN workspace_capture_settings c ON c.workspace_id=s.workspace_id
               WHERE s.workspace_id=%s AND (s.deleted_at IS NOT NULL OR
                 (c.retention_days IS NOT NULL AND
                  s.updated_at < now()-make_interval(days => c.retention_days)))""",
            (workspace_id,),
        ).fetchone()
        if apply_retention:
            db.execute(
                """DELETE FROM session_artifacts a USING sessions s
                   WHERE a.workspace_id=%s AND s.workspace_id=a.workspace_id AND s.id=a.session_id
                   AND (s.deleted_at IS NOT NULL OR EXISTS (
                     SELECT 1 FROM workspace_capture_settings c WHERE c.workspace_id=s.workspace_id
                       AND c.retention_days IS NOT NULL
                       AND s.updated_at < now()-make_interval(days => c.retention_days)))""",
                (workspace_id,),
            )
            db.execute(
                """UPDATE sessions s SET deleted_at=now(),updated_at=now()
                   FROM workspace_capture_settings c WHERE s.workspace_id=%s
                     AND c.workspace_id=s.workspace_id AND s.deleted_at IS NULL
                     AND c.retention_days IS NOT NULL
                     AND s.updated_at < now()-make_interval(days => c.retention_days)""",
                (workspace_id,),
            )
        return {"workspace_id": workspace_id, "mode": "apply" if apply_retention else "dry_run",
                "tables_before": tables, "limits": store.storage_limits,
                "session_artifacts_eligible_for_removal": int(expired["rows"]),
                "session_content_bytes_eligible_for_removal": int(expired["bytes"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Internal workspace UUID")
    parser.add_argument("--apply-retention", action="store_true", help="Delete expired session artifacts using existing workspace retention consent")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is required")
    try:
        report = storage_report(PostgresStore(database_url), args.workspace, apply_retention=args.apply_retention)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
