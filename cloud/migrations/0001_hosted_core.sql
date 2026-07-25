CREATE TABLE users (
    id uuid PRIMARY KEY, email text NOT NULL UNIQUE, display_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(), deleted_at timestamptz
);
CREATE TABLE workspaces (
    id uuid PRIMARY KEY, name text NOT NULL, slug text NOT NULL UNIQUE,
    owner_user_id uuid NOT NULL REFERENCES users(id), plan text NOT NULL DEFAULT 'free',
    default_write_mode text NOT NULL DEFAULT 'propose', created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);
CREATE TABLE workspace_members (
    workspace_id uuid NOT NULL REFERENCES workspaces(id), user_id uuid NOT NULL REFERENCES users(id),
    role text NOT NULL CHECK (role IN ('owner','admin','member')),
    created_at timestamptz NOT NULL DEFAULT now(), revoked_at timestamptz,
    PRIMARY KEY (workspace_id,user_id)
);
CREATE TABLE projects (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id), name text NOT NULL,
    slug text NOT NULL, description text NOT NULL DEFAULT '', created_at timestamptz NOT NULL DEFAULT now(),
    archived_at timestamptz, UNIQUE(workspace_id,slug), UNIQUE(workspace_id,id)
);
CREATE TABLE client_connections (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id),
    user_id uuid NOT NULL REFERENCES users(id), provider text NOT NULL, client_type text NOT NULL,
    external_client_id text, display_name text NOT NULL, status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(), last_seen_at timestamptz, revoked_at timestamptz,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb, UNIQUE(workspace_id,id)
);
CREATE TABLE client_scope_grants (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL, client_connection_id uuid NOT NULL,
    scope_kind text NOT NULL CHECK(scope_kind IN ('workspace','project','user')),
    scope_id uuid NOT NULL, can_read boolean NOT NULL DEFAULT false,
    can_propose boolean NOT NULL DEFAULT false, can_auto_activate boolean NOT NULL DEFAULT false,
    memory_types text[], expires_at timestamptz, created_by_user_id uuid NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(), revoked_at timestamptz,
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id)
);
CREATE TABLE memories (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id),
    project_id uuid, owner_user_id uuid REFERENCES users(id), memory_type text NOT NULL,
    scope_kind text NOT NULL CHECK(scope_kind IN ('workspace','project','user')),
    scope_id uuid NOT NULL, content text NOT NULL, normalized_content text NOT NULL,
    status text NOT NULL CHECK(status IN ('proposed','active','superseded','deleted')),
    risk_level text NOT NULL DEFAULT 'normal', authority real NOT NULL DEFAULT 0.5 CHECK(authority BETWEEN 0 AND 1),
    confidence real NOT NULL DEFAULT 1.0 CHECK(confidence BETWEEN 0 AND 1),
    importance real NOT NULL DEFAULT 0.6 CHECK(importance BETWEEN 0 AND 1),
    write_mode_requested text NOT NULL DEFAULT 'propose', write_mode_applied text NOT NULL DEFAULT 'propose',
    created_by_user_id uuid REFERENCES users(id), created_by_client_connection_id uuid,
    supersedes_memory_id uuid REFERENCES memories(id), conflict_group_id uuid,
    valid_from timestamptz NOT NULL DEFAULT now(), valid_until timestamptz, last_verified_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), deleted_at timestamptz,
    FOREIGN KEY(workspace_id,project_id) REFERENCES projects(workspace_id,id),
    FOREIGN KEY(workspace_id,created_by_client_connection_id) REFERENCES client_connections(workspace_id,id),
    UNIQUE(workspace_id,id)
);
CREATE TABLE memory_sources (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL, memory_id uuid NOT NULL,
    source_type text NOT NULL, source_uri text NOT NULL, provider text,
    client_connection_id uuid, session_id text, request_id text, excerpt text,
    content_hash text NOT NULL, authority real NOT NULL DEFAULT 0.5,
    occurred_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,memory_id) REFERENCES memories(workspace_id,id),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id)
);
CREATE TABLE memory_relations (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL, from_memory_id uuid NOT NULL,
    relation_type text NOT NULL, to_memory_id uuid, target_type text, target_id uuid,
    source_id uuid REFERENCES memory_sources(id), created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,from_memory_id) REFERENCES memories(workspace_id,id),
    FOREIGN KEY(workspace_id,to_memory_id) REFERENCES memories(workspace_id,id)
);
CREATE TABLE disclosure_logs (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id), user_id uuid,
    client_connection_id uuid, tool_name text NOT NULL, query_hash text NOT NULL,
    purpose text NOT NULL, allowed_scope_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb,
    returned_memory_ids jsonb NOT NULL DEFAULT '[]'::jsonb, denied_memory_count integer NOT NULL DEFAULT 0,
    estimated_tokens integer NOT NULL DEFAULT 0, decision text NOT NULL,
    denial_reason text, request_id text, created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id)
);
CREATE TABLE memory_feedback (
    id uuid PRIMARY KEY, workspace_id uuid NOT NULL, memory_id uuid NOT NULL,
    user_id uuid, client_connection_id uuid, feedback_type text NOT NULL,
    notes text, created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,memory_id) REFERENCES memories(workspace_id,id),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id),
    CHECK(feedback_type IN ('useful','irrelevant','incorrect','stale','unsafe','missing_source'))
);
CREATE TABLE idempotency_keys (
    workspace_id uuid NOT NULL REFERENCES workspaces(id), client_connection_id uuid NOT NULL,
    idempotency_key text NOT NULL, request_hash text NOT NULL, memory_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(workspace_id,client_connection_id,idempotency_key),
    FOREIGN KEY(workspace_id,client_connection_id) REFERENCES client_connections(workspace_id,id),
    FOREIGN KEY(workspace_id,memory_id) REFERENCES memories(workspace_id,id)
);
CREATE INDEX memories_workspace_search_idx ON memories(workspace_id,status,scope_kind,scope_id,updated_at DESC);
CREATE INDEX memories_keyword_idx ON memories USING gin(to_tsvector('simple',normalized_content));
CREATE INDEX grants_client_idx ON client_scope_grants(workspace_id,client_connection_id,scope_kind,scope_id) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX grants_one_active_scope_idx ON client_scope_grants(workspace_id,client_connection_id,scope_kind,scope_id) WHERE revoked_at IS NULL;
CREATE INDEX disclosures_workspace_idx ON disclosure_logs(workspace_id,created_at DESC);
CREATE INDEX sources_workspace_memory_idx ON memory_sources(workspace_id,memory_id);
