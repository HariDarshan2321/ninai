ALTER TABLE team_projects ADD COLUMN repository text
    CHECK (repository ~ '^[a-z0-9]([a-z0-9-]{0,37}[a-z0-9])?/[a-z0-9_.-]{1,100}$');

CREATE TRIGGER team_project_repository_immutable BEFORE UPDATE OF repository ON team_projects
    FOR EACH ROW WHEN (OLD.repository IS NOT NULL AND OLD.repository IS DISTINCT FROM NEW.repository)
    EXECUTE FUNCTION public.team_reject_record_updates();

CREATE UNIQUE INDEX team_active_repository_idx ON team_projects (workspace_id, repository)
    WHERE archived_at IS NULL AND repository IS NOT NULL;

ALTER TABLE team_binding_actions DROP CONSTRAINT team_binding_actions_action_check;
ALTER TABLE team_binding_actions ADD CONSTRAINT team_binding_actions_action_check
    CHECK (action IN ('read', 'propose', 'view-history', 'read-handoffs', 'publish-handoff'));

CREATE TABLE team_handoffs (
    workspace_id uuid NOT NULL,
    project_id uuid NOT NULL,
    id uuid NOT NULL,
    author_user_id uuid NOT NULL,
    request_key uuid NOT NULL,
    topic text NOT NULL CHECK (length(btrim(topic)) BETWEEN 1 AND 80),
    status text NOT NULL CHECK (status IN ('working', 'blocked', 'done')),
    summary text NOT NULL CHECK (length(btrim(summary)) BETWEEN 1 AND 400),
    next_step text CHECK (length(btrim(next_step)) BETWEEN 1 AND 240),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id, project_id, id),
    UNIQUE (workspace_id, project_id, author_user_id, request_key),
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id),
    FOREIGN KEY (workspace_id, author_user_id) REFERENCES team_members(workspace_id, user_id)
);

CREATE INDEX team_handoff_recent_idx ON team_handoffs (workspace_id, project_id, recorded_at DESC, id DESC);
ALTER TABLE team_handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_handoffs FORCE ROW LEVEL SECURITY;
CREATE POLICY team_workspace_scope ON team_handoffs
    USING (workspace_id = (SELECT public.team_current_workspace()))
    WITH CHECK (workspace_id = (SELECT public.team_current_workspace()));
CREATE TRIGGER team_record_immutable BEFORE UPDATE ON team_handoffs
    FOR EACH ROW EXECUTE FUNCTION public.team_reject_record_updates();
