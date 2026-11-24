-- Apply as the migration operator to an existing, dedicated LOGIN role.
-- psql -v team_runtime_role=ninai_team_runtime -f cloud/team_runtime_grants.sql
BEGIN;
GRANT USAGE ON SCHEMA public TO :"team_runtime_role";
GRANT SELECT (id, deleted_at, display_name) ON users TO :"team_runtime_role";
GRANT SELECT (id, owner_user_id, deleted_at) ON workspaces TO :"team_runtime_role";
GRANT SELECT (workspace_id, user_id, role, revoked_at) ON workspace_members TO :"team_runtime_role";
GRANT SELECT (user_id, issuer, subject) ON oauth_identities TO :"team_runtime_role";

GRANT SELECT, INSERT ON team_workspaces, team_members, team_projects, team_project_members, team_groups,
    team_group_members, team_group_projects, team_invitations, team_bindings, team_binding_actions,
    team_decisions, team_decision_versions, team_decision_reviewers, team_decision_sources,
    team_source_pins, team_decision_events, team_supersessions, team_audit_events, team_audit_items
    TO :"team_runtime_role";

GRANT UPDATE (authorization_epoch) ON team_workspaces TO :"team_runtime_role";
GRANT UPDATE (archived_at) ON team_projects TO :"team_runtime_role";
GRANT UPDATE (role, revoked_at) ON team_members, team_project_members TO :"team_runtime_role";
GRANT UPDATE (revoked_at) ON team_group_members, team_group_projects,
    team_binding_actions, team_decision_reviewers TO :"team_runtime_role";
GRANT UPDATE (accepted_at, accepted_by_user_id, revoked_at) ON team_invitations TO :"team_runtime_role";
GRANT UPDATE (token_hash, expires_at, revoked_at) ON team_bindings TO :"team_runtime_role";
COMMIT;
