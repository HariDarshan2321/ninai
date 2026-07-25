ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_status_check;
ALTER TABLE memories ADD CONSTRAINT memories_status_check
    CHECK(status IN ('proposed','active','conflicted','superseded','rejected','deleted'));

ALTER TABLE memories ADD COLUMN IF NOT EXISTS freshness_policy text NOT NULL DEFAULT 'type_default';

CREATE INDEX IF NOT EXISTS memories_current_recall_idx
    ON memories(workspace_id,scope_kind,scope_id,updated_at DESC)
    WHERE status='active' AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS memories_conflict_review_idx
    ON memories(workspace_id,conflict_group_id,updated_at DESC)
    WHERE status='conflicted' AND deleted_at IS NULL;
