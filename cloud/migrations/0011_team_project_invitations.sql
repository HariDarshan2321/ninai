ALTER TABLE team_invitations ADD COLUMN project_id uuid;
ALTER TABLE team_invitations ADD CONSTRAINT team_invitation_project_scope
    FOREIGN KEY (workspace_id, project_id) REFERENCES team_projects(workspace_id, id);
