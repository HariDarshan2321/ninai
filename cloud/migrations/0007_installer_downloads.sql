CREATE TABLE installer_downloads (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL,
    user_id uuid NOT NULL,
    platform text NOT NULL CHECK(platform IN ('macos')),
    artifact_sha256 text NOT NULL CHECK(artifact_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(workspace_id,user_id)
        REFERENCES workspace_members(workspace_id,user_id)
);

CREATE INDEX installer_downloads_workspace_created_idx
    ON installer_downloads(workspace_id,created_at DESC);
CREATE INDEX installer_downloads_user_created_idx
    ON installer_downloads(user_id,created_at DESC);
