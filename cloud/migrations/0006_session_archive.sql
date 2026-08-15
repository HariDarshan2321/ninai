CREATE TABLE workspace_capture_settings (
    workspace_id uuid PRIMARY KEY REFERENCES workspaces(id),
    archive_sessions boolean NOT NULL DEFAULT false,
    propose_memories boolean NOT NULL DEFAULT true,
    auto_approve_low_risk boolean NOT NULL DEFAULT false,
    retention_days integer CHECK(retention_days IS NULL OR retention_days BETWEEN 1 AND 3650),
    accepted_by_user_id uuid REFERENCES users(id),
    accepted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id uuid NOT NULL,
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    project_id uuid NOT NULL,
    client_connection_id uuid NOT NULL,
    provider text NOT NULL,
    external_session_id text NOT NULL,
    title text NOT NULL,
    source_uri text NOT NULL,
    cwd_or_repo text NOT NULL DEFAULT '',
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    capture_status text NOT NULL CHECK(capture_status IN ('started','checkpointed','completed','failed')),
    last_checkpoint_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    PRIMARY KEY(workspace_id,id),
    UNIQUE(workspace_id,provider,external_session_id),
    FOREIGN KEY(workspace_id,project_id) REFERENCES projects(workspace_id,id),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id)
);

CREATE TABLE session_artifacts (
    workspace_id uuid NOT NULL,
    session_id uuid NOT NULL,
    content text NOT NULL,
    content_hash text NOT NULL,
    source_uri text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(workspace_id,session_id),
    FOREIGN KEY(workspace_id,session_id) REFERENCES sessions(workspace_id,id) ON DELETE CASCADE
);

CREATE TABLE session_disclosure_logs (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    project_id uuid NOT NULL,
    client_connection_id uuid NOT NULL,
    returned_session_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    estimated_tokens integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,project_id) REFERENCES projects(workspace_id,id),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id)
);

CREATE INDEX sessions_workspace_updated_idx ON sessions(workspace_id,updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX sessions_project_updated_idx ON sessions(workspace_id,project_id,updated_at DESC) WHERE deleted_at IS NULL;
