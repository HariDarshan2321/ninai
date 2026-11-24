#!/usr/bin/env python3
"""Compare two explicitly confirmed PostgreSQL targets without exporting row data.

This does not create a backup, restore data, grant access, or connect a service.
Only aggregate counts, ephemeral salted digests and named invariant failures leave
the databases. Never log driver exceptions: they can contain connection secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cloud" / "src"))
from ninai_cloud.migrations import migration_files

LEGACY_TABLES = (
    "schema_migrations", "users", "workspaces", "workspace_members", "projects",
    "client_connections", "client_scope_grants", "memories", "memory_sources",
    "memory_relations", "disclosure_logs", "memory_feedback", "idempotency_keys",
    "personal_access_tokens", "oauth_identities", "oauth_client_bindings",
    "workspace_capture_settings", "sessions", "session_artifacts",
    "session_disclosure_logs", "installer_downloads",
)
TEAM_TABLES = (
    "team_workspaces", "team_members", "team_projects", "team_project_members", "team_groups",
    "team_group_members", "team_group_projects", "team_invitations", "team_bindings",
    "team_binding_actions", "team_decisions", "team_decision_versions", "team_decision_reviewers",
    "team_decision_sources", "team_source_pins", "team_decision_events", "team_supersessions",
    "team_audit_events", "team_audit_items",
)
TABLES = LEGACY_TABLES + TEAM_TABLES
TEAM_SCOPE_PREDICATE = "(workspace_id=(SELECTpublic.team_current_workspace()ASteam_current_workspace))"

# All checks return violation counts, never identifying rows or stored text.
INVARIANTS = {
    "memory_provenance_missing": "SELECT count(*) FROM public.memories m WHERE NOT EXISTS (SELECT 1 FROM public.memory_sources s WHERE s.workspace_id=m.workspace_id AND s.memory_id=m.id AND btrim(s.source_uri)<>'')",
    "blank_source_uri": "SELECT count(*) FROM public.memory_sources WHERE btrim(source_uri)=''",
    "memory_project_scope_invalid": "SELECT count(*) FROM public.memories m WHERE m.scope_kind='project' AND (m.project_id IS DISTINCT FROM m.scope_id OR NOT EXISTS (SELECT 1 FROM public.projects p WHERE p.workspace_id=m.workspace_id AND p.id=m.scope_id))",
    "memory_workspace_scope_invalid": "SELECT count(*) FROM public.memories WHERE scope_kind='workspace' AND scope_id<>workspace_id",
    "memory_user_scope_invalid": "SELECT count(*) FROM public.memories m WHERE m.scope_kind='user' AND NOT EXISTS (SELECT 1 FROM public.workspace_members w WHERE w.workspace_id=m.workspace_id AND w.user_id=m.scope_id)",
    "grant_project_scope_invalid": "SELECT count(*) FROM public.client_scope_grants g WHERE g.scope_kind='project' AND NOT EXISTS (SELECT 1 FROM public.projects p WHERE p.workspace_id=g.workspace_id AND p.id=g.scope_id)",
    "grant_workspace_scope_invalid": "SELECT count(*) FROM public.client_scope_grants WHERE scope_kind='workspace' AND scope_id<>workspace_id",
    "grant_user_scope_invalid": "SELECT count(*) FROM public.client_scope_grants g WHERE g.scope_kind='user' AND NOT EXISTS (SELECT 1 FROM public.workspace_members m WHERE m.workspace_id=g.workspace_id AND m.user_id=g.scope_id)",
    "client_membership_missing": "SELECT count(*) FROM public.client_connections c WHERE NOT EXISTS (SELECT 1 FROM public.workspace_members m WHERE m.workspace_id=c.workspace_id AND m.user_id=c.user_id)",
    "oauth_binding_owner_invalid": "SELECT count(*) FROM public.oauth_client_bindings b WHERE NOT EXISTS (SELECT 1 FROM public.client_connections c WHERE c.workspace_id=b.workspace_id AND c.id=b.client_connection_id AND c.user_id=b.user_id)",
    "pat_owner_invalid": "SELECT count(*) FROM public.personal_access_tokens t WHERE NOT EXISTS (SELECT 1 FROM public.client_connections c WHERE c.workspace_id=t.workspace_id AND c.id=t.client_connection_id AND c.user_id=t.user_id)",
    "blank_session_provenance": "SELECT count(*) FROM public.sessions WHERE btrim(source_uri)=''",
    "blank_artifact_provenance": "SELECT count(*) FROM public.session_artifacts WHERE btrim(source_uri)=''",
    "team_active_owner_missing": """SELECT count(*) FROM public.team_workspaces t
        JOIN public.workspaces w ON w.id=t.workspace_id
        WHERE t.quarantined_at IS NULL AND w.deleted_at IS NULL AND NOT EXISTS (
            SELECT 1 FROM public.team_members m JOIN public.users u ON u.id=m.user_id
            WHERE m.workspace_id=t.workspace_id AND m.role='owner' AND m.revoked_at IS NULL AND u.deleted_at IS NULL)""",
    "team_missing_version_history": """SELECT count(*) FROM public.team_decision_versions v WHERE NOT EXISTS (
            SELECT 1 FROM public.team_decision_events e WHERE
            (e.workspace_id,e.project_id,e.decision_id,e.version)=(v.workspace_id,v.project_id,v.decision_id,v.version)
            AND e.state='proposed')""",
    "team_replacement_without_approval": """SELECT count(*) FROM public.team_supersessions s WHERE NOT EXISTS (
            SELECT 1 FROM public.team_decision_events e WHERE
            (e.workspace_id,e.project_id,e.decision_id,e.version)=(s.workspace_id,s.project_id,s.decision_id,s.version)
            AND e.state='approved') OR NOT EXISTS (
            SELECT 1 FROM public.team_decision_events e WHERE
            (e.workspace_id,e.project_id,e.decision_id,e.version)=(s.workspace_id,s.project_id,s.replaces_decision_id,s.replaces_version)
            AND e.state='replaced')""",
    "team_replaced_version_without_edge": """SELECT count(*) FROM public.team_decision_events e
        WHERE e.state='replaced' AND NOT EXISTS (
            SELECT 1 FROM public.team_supersessions s WHERE
            (s.workspace_id,s.project_id,s.replaces_decision_id,s.replaces_version)=
            (e.workspace_id,e.project_id,e.decision_id,e.version))""",
}


def target_fingerprint(url: str) -> str:
    """Bind approval to host, port, database and role; exclude passwords entirely.

    Query options are rejected to prevent host/db overrides and client options.
    This deliberately accepts only simple PostgreSQL URLs, not service aliases.
    """
    parsed = urlsplit(url)
    if (parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname
            or not parsed.username or not parsed.path.strip("/")
            or parsed.query or parsed.fragment or "," in parsed.hostname):
        raise ValueError("use a simple PostgreSQL URL with host, database and role, without query options")
    identity = [parsed.hostname.lower(), parsed.port or 5432,
                unquote(parsed.path[1:]), unquote(parsed.username)]
    return hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()


def check_targets(source: str, restore: str, source_confirmation: str,
                  restore_confirmation: str, isolated: bool) -> tuple[str, str]:
    fingerprints = target_fingerprint(source), target_fingerprint(restore)
    if not isolated:
        raise ValueError("explicit isolated-restore confirmation required")
    if not (hmac.compare_digest(fingerprints[0], source_confirmation)
            and hmac.compare_digest(fingerprints[1], restore_confirmation)):
        raise ValueError("target confirmation mismatch")
    # Changing only the role cannot make a database an isolated restore.
    a, b = urlsplit(source), urlsplit(restore)
    if (a.hostname, a.port or 5432, unquote(a.path)) == (b.hostname, b.port or 5432, unquote(b.path)):
        raise ValueError("source and restore must be different databases")
    return fingerprints


def begin_snapshot(db, timeout_seconds: int) -> tuple:
    db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    db.execute("SELECT set_config('search_path','pg_catalog',true)")
    db.execute("SELECT set_config('TimeZone','UTC',true)")
    db.execute("SELECT set_config('DateStyle','ISO, YMD',true)")
    db.execute("SELECT set_config('statement_timeout',%s,true)", (str(timeout_seconds * 1000),))
    db.execute("SELECT set_config('lock_timeout','3000',true)")
    db.execute("SELECT set_config('idle_in_transaction_session_timeout','60000',true)")
    # PostgreSQL errors if rows would be filtered for this role. This setting
    # does not grant permission to read them. A restore operator needs an
    # independently provisioned identity with complete snapshot access.
    db.execute("SELECT set_config('row_security','off',true)")
    if db.execute("SHOW transaction_read_only").fetchone()[0] != "on":
        raise ValueError("read-only snapshot not established")
    return db.execute("SELECT current_database(), inet_server_addr()::text, inet_server_port()").fetchone()


def check_row_security(db) -> None:
    relations = db.execute("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,row_security_active(c.oid)
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND (c.relrowsecurity OR c.relforcerowsecurity)""").fetchall()
    if {name for name, _, _, _ in relations} != set(TEAM_TABLES):
        raise ValueError("unexpected row-level security inventory")
    if any(not enabled or not forced or filtered for _, enabled, forced, filtered in relations):
        raise ValueError("team row-level security requires forced policies and a complete snapshot role")

    policies = db.execute("""SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check
        FROM pg_catalog.pg_policies WHERE schemaname='public'""").fetchall()
    if len(policies) != len(TEAM_TABLES) or {policy[0] for policy in policies} != set(TEAM_TABLES):
        raise ValueError("unexpected team row-level policy inventory")
    for _, name, kind, roles, command, using, check in policies:
        if ((name, kind, roles, command) != ("team_workspace_scope", "PERMISSIVE", "{public}", "ALL")
                or any("".join((clause or "").split()) != TEAM_SCOPE_PREDICATE for clause in (using, check))):
            raise ValueError("unexpected team workspace policy")


def inspect(db, salt: str, deadline: float) -> dict:
    def bounded():
        if time.monotonic() > deadline:
            raise TimeoutError("comparison deadline exceeded")

    bounded()
    inventory = tuple(row[0] for row in db.execute(
        "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename"
    ).fetchall())
    missing = sorted(set(TABLES) - set(inventory))
    unknown = sorted(set(inventory) - set(TABLES))
    # Fail before querying unreviewed tables (potential views/functions are excluded).
    if missing or unknown:
        return {"missing_tables": missing, "unknown_tables": unknown, "valid": False}
    check_row_security(db)
    # Include row security and decision invariants implemented by functions and triggers.
    # Digest catalog text inside the server, avoiding output of any default values.
    schema_digest = db.execute("""
        SELECT encode(sha256(convert_to(%s || jsonb_build_object(
          'columns', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.ordinal_position)
                      FROM (SELECT table_name,ordinal_position,column_name,data_type,udt_name,
                                   is_nullable,column_default,identity_generation FROM information_schema.columns
                            WHERE table_schema='public') x),
          'constraints', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.name)
                          FROM (SELECT c.relname AS table_name,k.conname AS name,
                                       pg_get_constraintdef(k.oid) AS definition,k.convalidated
                                FROM pg_catalog.pg_constraint k
                                JOIN pg_catalog.pg_class c ON c.oid=k.conrelid
                                JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                                WHERE n.nspname='public') x),
          'indexes', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.tablename,x.indexname)
                      FROM (SELECT tablename,indexname,indexdef FROM pg_catalog.pg_indexes
                            WHERE schemaname='public') x),
          'functions', (SELECT jsonb_agg(pg_get_functiondef(p.oid) ORDER BY p.proname,pg_get_function_identity_arguments(p.oid))
                        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
                        WHERE n.nspname='public' AND p.proname IN ('team_current_workspace',
                              'team_reject_record_updates','team_check_version_write',
                              'team_check_supersession','team_check_committed_supersession')),
          'triggers', (SELECT jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.name)
                       FROM (SELECT c.relname AS table_name,t.tgname AS name,
                                    pg_get_triggerdef(t.oid) AS definition,t.tgenabled
                             FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
                             JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                             WHERE n.nspname='public' AND NOT t.tgisinternal) x)
        )::text, 'UTF8')), 'hex')
    """, (salt,)).fetchone()[0]
    expected = sorted(path.stem for path in migration_files())
    applied = [r[0] for r in db.execute("SELECT version FROM public.schema_migrations ORDER BY version").fetchall()]
    tables = {}
    for index, table in enumerate(TABLES):
        bounded()
        digest = hashlib.sha256()
        count = 0
        # The server serializes rows; the client receives only salted row hashes.
        # Sort hashes rather than identifiers; retain duplicates and stream bounded batches.
        with db.cursor(name=f"restore_digest_{index}") as cursor:
            cursor.execute(
                f'SELECT encode(sha256(convert_to(%s || to_jsonb(t)::text, \'UTF8\')),\'hex\') AS digest FROM public."{table}" t ORDER BY digest',
                (salt,),
            )
            while batch := cursor.fetchmany(512):
                bounded()
                for (row_hash,) in batch:
                    digest.update(bytes.fromhex(row_hash))
                    count += 1
        tables[table] = {"rows": count, "digest": digest.hexdigest()}
    violations = {}
    for name, query in INVARIANTS.items():
        bounded()
        violations[name] = db.execute(query).fetchone()[0]
    for table in ("team_decision_versions", "team_decision_events"):
        bounded()
        latest = db.execute(f'SELECT max(sequence) FROM public."{table}"').fetchone()[0]
        last_value = db.execute("""SELECT last_value FROM pg_catalog.pg_sequences
            WHERE schemaname='public' AND sequencename=%s""", (f"{table}_sequence_seq",)).fetchone()
        violations[f"{table}_sequence_behind"] = int(latest is not None and
            (last_value is None or last_value[0] is None or last_value[0] < latest))
    return {
        "valid": applied == expected and not any(violations.values()),
        "expected_migrations": expected, "applied_migrations": applied,
        "tables": tables, "invariant_violations": violations,
        "schema_digest": schema_digest,
        "server_version": db.info.server_version,
    }


def compare_reports(source: dict, restore: dict) -> dict:
    same_tables = source.get("tables") == restore.get("tables")
    same_schema = source.get("schema_digest") == restore.get("schema_digest")
    return {
        "status": "ok" if source["valid"] and restore["valid"] and same_tables and same_schema and "tables" in source and "schema_digest" in source else "failed",
        "schema_match": same_schema and "schema_digest" in source,
        "exact_snapshot_match": same_tables and "tables" in source,
        "mismatched_tables": sorted(name for name in set(source.get("tables", {})) | set(restore.get("tables", {}))
                                    if source.get("tables", {}).get(name) != restore.get("tables", {}).get(name)),
        "source": source, "restore": restore,
        "limitations": "Independent read-only snapshots; live writes or an earlier PITR point can cause differences. No application authorization or real-host acceptance is established.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url-env", default="NINAI_SOURCE_DATABASE_URL")
    parser.add_argument("--restore-url-env", default="NINAI_RESTORE_DATABASE_URL")
    parser.add_argument("--fingerprint-env", help="Print only the identity fingerprint of this environment URL; do not connect")
    parser.add_argument("--confirm-source")
    parser.add_argument("--confirm-restore")
    parser.add_argument("--confirm-isolated-restore", action="store_true")
    parser.add_argument("--statement-timeout", type=int, default=30)
    parser.add_argument("--total-timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        if args.fingerprint_env:
            print(target_fingerprint(os.environ.get(args.fingerprint_env, "")))
            return 0
        if not (1 <= args.statement_timeout <= 60 and 1 <= args.total_timeout <= 600):
            raise ValueError("timeouts must be 1..60 and 1..600 seconds respectively")
        source_url = os.environ.get(args.source_url_env, "")
        restore_url = os.environ.get(args.restore_url_env, "")
        fingerprints = check_targets(source_url, restore_url, args.confirm_source or "",
                                     args.confirm_restore or "", args.confirm_isolated_restore)
        if any(os.environ.get(name) for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE")):
            raise ValueError("libpq target overrides must be unset")
        import psycopg
        # Explicit settings override unsafe libpq environment defaults. No URL is logged.
        options = {"connect_timeout": 10, "application_name": "ninai-restore-readonly",
                   "options": "-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=3000",
                   "sslmode": "require"}
        deadline = time.monotonic() + args.total_timeout
        with psycopg.connect(source_url, **options) as source, psycopg.connect(restore_url, **options) as restore:
            source_id = begin_snapshot(source, args.statement_timeout)
            restore_id = begin_snapshot(restore, args.statement_timeout)
            if source_id == restore_id:
                raise ValueError("server identities resolve to the same database")
            salt = secrets.token_hex(32)
            report = compare_reports(inspect(source, salt, deadline), inspect(restore, salt, deadline))
            source.rollback()
            restore.rollback()
        report["target_fingerprints"] = dict(zip(("source", "restore"), fingerprints))
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0 if report["status"] == "ok" else 1
    except Exception:
        # Do not print exceptions, URLs, failing SQL parameters or driver diagnostics.
        print(json.dumps({"status": "failed", "reason": "Target validation or read-only comparison failed; inspect private operator diagnostics without recording secrets."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
