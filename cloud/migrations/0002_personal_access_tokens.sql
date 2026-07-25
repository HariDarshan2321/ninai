-- Self-hosted PAT credentials. Only the irreversible SHA-256 digest is stored.
CREATE TABLE personal_access_tokens (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    user_id uuid NOT NULL REFERENCES users(id),
    client_connection_id uuid NOT NULL,
    token_hash char(64) NOT NULL UNIQUE,
    label text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    last_used_at timestamptz,
    revoked_at timestamptz,
    FOREIGN KEY(workspace_id,client_connection_id)
        REFERENCES client_connections(workspace_id,id)
);
CREATE INDEX personal_access_tokens_client_idx
    ON personal_access_tokens(workspace_id,client_connection_id)
    WHERE revoked_at IS NULL;
