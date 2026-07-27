-- Bind every OAuth client mapping to a connection owned by the same user and
-- workspace. Application queries already enforce this relationship; the
-- composite foreign key makes it impossible for manual/admin SQL to create a
-- cross-user binding.
ALTER TABLE client_connections
    ADD CONSTRAINT client_connections_workspace_id_id_user_id_key
    UNIQUE (workspace_id, id, user_id);

ALTER TABLE oauth_client_bindings
    ADD CONSTRAINT oauth_client_bindings_connection_owner_fkey
    FOREIGN KEY (workspace_id, client_connection_id, user_id)
    REFERENCES client_connections(workspace_id, id, user_id);
