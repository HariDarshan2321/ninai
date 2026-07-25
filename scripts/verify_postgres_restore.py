#!/usr/bin/env python3
"""Read-only structural verification for a restored Ninai PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud" / "src"))

from ninai_cloud.migrations import migration_files


REQUIRED_TABLES = (
    "schema_migrations",
    "users",
    "workspaces",
    "workspace_members",
    "projects",
    "client_connections",
    "client_scope_grants",
    "memories",
    "memory_sources",
    "memory_relations",
    "disclosure_logs",
    "memory_feedback",
    "idempotency_keys",
    "personal_access_tokens",
)


def inspect_restore(connection: Any) -> dict[str, Any]:
    """Inspect schema and non-sensitive row totals without modifying the restore."""
    connection.execute("SET TRANSACTION READ ONLY")
    expected = {path.stem for path in migration_files()}
    missing_tables = [
        table
        for table in REQUIRED_TABLES
        if connection.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
        is None
    ]
    applied = (
        {
            row[0]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        }
        if "schema_migrations" not in missing_tables
        else set()
    )
    missing_migrations = sorted(expected - applied)
    counts = {}
    for table in ("workspaces", "projects", "client_connections", "memories", "disclosure_logs"):
        if table not in missing_tables:
            counts[table] = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    return {
        "status": "ok" if not missing_migrations and not missing_tables else "failed",
        "expected_migrations": sorted(expected),
        "applied_migrations": sorted(applied),
        "missing_migrations": missing_migrations,
        "missing_tables": missing_tables,
        "row_counts": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify a restored Ninai database using read-only queries."
    )
    parser.add_argument(
        "--database-url-env",
        default="NINAI_RESTORE_DATABASE_URL",
        help="name of the environment variable containing the restore URL",
    )
    args = parser.parse_args()
    database_url = os.environ.get(args.database_url_env, "").strip()
    if not database_url:
        raise SystemExit(f"{args.database_url_env} is required")

    import psycopg

    with psycopg.connect(database_url) as connection:
        report = inspect_restore(connection)
        connection.rollback()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
