-- External OAuth identities remain provider strings; Ninai domain IDs remain UUIDs.
CREATE TABLE oauth_identities (
    id uuid PRIMARY KEY,
    issuer text NOT NULL,
    subject text NOT NULL,
    user_id uuid NOT NULL REFERENCES users(id),
    email text,
    display_name text,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (issuer, subject),
    UNIQUE (issuer, user_id)
);

CREATE TABLE oauth_client_bindings (
    id uuid PRIMARY KEY,
    issuer text NOT NULL,
    oauth_client_id text NOT NULL,
    user_id uuid NOT NULL REFERENCES users(id),
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    client_connection_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    FOREIGN KEY (workspace_id, client_connection_id)
        REFERENCES client_connections(workspace_id, id),
    UNIQUE (issuer, oauth_client_id, user_id, workspace_id),
    UNIQUE (workspace_id, client_connection_id)
);

CREATE INDEX oauth_identities_user_idx ON oauth_identities(user_id);
CREATE INDEX oauth_client_bindings_lookup_idx
    ON oauth_client_bindings(issuer, oauth_client_id, user_id)
    WHERE revoked_at IS NULL;
