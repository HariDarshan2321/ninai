"""Verify the deployed PostgreSQL boundary before enabling the team preview."""
from secrets import randbits


TEAM_TABLES = frozenset({
    "team_workspaces", "team_members", "team_projects", "team_project_members", "team_groups",
    "team_group_members", "team_group_projects", "team_invitations", "team_bindings",
    "team_binding_actions", "team_decisions", "team_decision_versions", "team_decision_reviewers",
    "team_decision_sources", "team_source_pins", "team_decision_events", "team_supersessions",
    "team_audit_events", "team_audit_items", "team_handoffs",
})
LEGACY_READ_COLUMNS = {
    "users": {"id", "deleted_at", "display_name"},
    "workspaces": {"id", "owner_user_id", "deleted_at"},
    "workspace_members": {"workspace_id", "user_id", "role", "revoked_at"},
    "oauth_identities": {"user_id", "issuer", "subject"},
}
TEAM_UPDATE_COLUMNS = {
    "team_workspaces": {"authorization_epoch"},
    "team_projects": {"archived_at", "repository"},
    "team_members": {"role", "revoked_at"},
    "team_project_members": {"role", "revoked_at"},
    "team_group_members": {"revoked_at"},
    "team_group_projects": {"revoked_at"},
    "team_binding_actions": {"revoked_at"},
    "team_decision_reviewers": {"revoked_at"},
    "team_invitations": {"accepted_at", "accepted_by_user_id", "revoked_at"},
    "team_bindings": {"token_hash", "expires_at", "revoked_at"},
}
WORKSPACE_PREDICATE = "(workspace_id = ( SELECT public.team_current_workspace() AS team_current_workspace))"
WORKSPACE_FUNCTION = """CREATE OR REPLACE FUNCTION public.team_current_workspace()
 RETURNS uuid
 LANGUAGE sql
 STABLE PARALLEL SAFE
 SET search_path TO 'pg_catalog'
RETURN (NULLIF(current_setting('ninai.team_workspace_id'::text, true), ''::text))::uuid"""


def verify_team_runtime(connect, legacy_connect):
    """Require the expected role, database, table inventory, and isolation policy."""
    with connect() as db, db.transaction():
        db.execute("SET LOCAL search_path TO pg_catalog, pg_temp")
        role = db.execute("""
            SELECT rolname, rolname=session_user AND rolcanlogin
                AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication)
                AND NOT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=r.oid)
                AND NOT pg_has_role(d.datdba, 'MEMBER')
                AND NOT has_database_privilege(d.oid, 'CREATE')
                AND NOT has_schema_privilege('public', 'CREATE')
                AND has_schema_privilege('public', 'USAGE')
                AND current_setting('row_security')='on' AS isolated
            FROM pg_roles r JOIN pg_database d ON d.datname=current_database()
            WHERE r.rolname=current_user
        """).fetchone()
        if not role or not role["isolated"]:
            raise RuntimeError("Team preview requires a dedicated unprivileged PostgreSQL login")

        # A transaction advisory lock is visible only in this database, even when
        # DSNs use different names or endpoints for the same server.
        lock_key = randbits(63)
        with legacy_connect() as legacy, legacy.transaction():
            legacy_role = legacy.execute("""
                SELECT session_user AS login, pg_catalog.pg_try_advisory_xact_lock(%s) AS locked
            """, (lock_key,)).fetchone()
            team_lock = db.execute("SELECT pg_try_advisory_xact_lock(%s) AS locked", (lock_key,)).fetchone()
            if not legacy_role["locked"] or team_lock["locked"] or legacy_role["login"] == role["rolname"]:
                raise RuntimeError("Team and legacy previews require separate logins to the same PostgreSQL database")

        helper = db.execute("""
            SELECT pg_get_functiondef(p.oid) AS definition,
                NOT pg_has_role(p.proowner, 'MEMBER') AND has_function_privilege(p.oid, 'EXECUTE') AS allowed
            FROM pg_proc p WHERE p.oid=to_regprocedure('public.team_current_workspace()') AND p.prokind='f'
        """).fetchone()
        if not helper or not helper["allowed"] or helper["definition"].strip() != WORKSPACE_FUNCTION:
            raise RuntimeError("Team preview requires the expected PostgreSQL workspace scope function")

        relations = db.execute("""
            SELECT c.relname, c.relkind,
                c.relrowsecurity AND c.relforcerowsecurity AND row_security_active(c.oid)
                    AND NOT pg_has_role(c.relowner, 'MEMBER') AS forced,
                has_table_privilege(c.oid,'SELECT') AS can_read,
                has_table_privilege(c.oid,'INSERT') AS can_insert,
                has_table_privilege(c.oid,'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS can_alter,
                CASE WHEN current_setting('server_version_num')::int >= 170000
                    THEN has_table_privilege(c.oid,'MAINTAIN') ELSE false END AS can_maintain,
                has_table_privilege(c.oid,'SELECT WITH GRANT OPTION,INSERT WITH GRANT OPTION') AS can_delegate
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
        """).fetchall()
        inventory = {r["relname"] for r in relations if r["relname"].startswith("team_")}
        if inventory != TEAM_TABLES:
            raise RuntimeError("Team preview requires the expected PostgreSQL team table inventory")
        for row in relations:
            is_team = row["relname"] in TEAM_TABLES
            if (row["can_read"] != is_team or row["can_insert"] != is_team
                    or row["can_alter"] or row["can_maintain"] or row["can_delegate"]
                    or (is_team and (row["relkind"] != "r" or not row["forced"]))):
                raise RuntimeError("Team preview requires forced PostgreSQL RLS and limited relation privileges")

        columns = db.execute("""
            SELECT c.relname, a.attname, has_column_privilege(c.oid,a.attnum,'SELECT') AS can_read,
                has_column_privilege(c.oid,a.attnum,'UPDATE') AS can_update,
                has_column_privilege(c.oid,a.attnum,'INSERT') AS can_insert,
                has_column_privilege(c.oid,a.attnum,'REFERENCES') AS can_reference,
                has_column_privilege(c.oid,a.attnum,'SELECT WITH GRANT OPTION,INSERT WITH GRANT OPTION,'
                    'UPDATE WITH GRANT OPTION,REFERENCES WITH GRANT OPTION') AS can_delegate
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_attribute a ON a.attrelid=c.oid
            WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') AND a.attnum>0 AND NOT a.attisdropped
        """).fetchall()
        actual_update_columns = set()
        actual_legacy_columns = set()
        for row in columns:
            relation, column = row["relname"], row["attname"]
            if (row["can_delegate"] or row["can_reference"]
                    or (row["can_insert"] and relation not in TEAM_TABLES)):
                raise RuntimeError("Team preview requires limited PostgreSQL column privileges")
            if row["can_update"]:
                actual_update_columns.add((relation, column))
            if row["can_read"] and relation not in TEAM_TABLES:
                actual_legacy_columns.add((relation, column))
        if (actual_update_columns != {(t, c) for t, cs in TEAM_UPDATE_COLUMNS.items() for c in cs}
                or actual_legacy_columns != {(t, c) for t, cs in LEGACY_READ_COLUMNS.items() for c in cs}):
            raise RuntimeError("Team preview requires the expected PostgreSQL column privileges")

        policies = db.execute("""
            SELECT c.relname, p.polname, p.polpermissive, p.polcmd, p.polroles=ARRAY[0]::oid[] AS everyone,
                pg_get_expr(p.polqual,p.polrelid) AS using_scope,
                pg_get_expr(p.polwithcheck,p.polrelid) AS check_scope
            FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=ANY(%s)
        """, (list(TEAM_TABLES),)).fetchall()
        if (len(policies) != len(TEAM_TABLES) or {p["relname"] for p in policies} != TEAM_TABLES
                or any(p["polname"] != "team_workspace_scope" or not p["polpermissive"]
                       or p["polcmd"] != "*" or not p["everyone"]
                       or p["using_scope"] != WORKSPACE_PREDICATE or p["check_scope"] != WORKSPACE_PREDICATE
                       for p in policies)):
            raise RuntimeError("Team preview requires the exact PostgreSQL workspace row policies")
