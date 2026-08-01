"""Create an idempotent synthetic workspace for directory reviewers."""
from __future__ import annotations

import argparse
import hashlib
import os
import uuid
from dataclasses import dataclass

from .migrations import apply_migrations


@dataclass(frozen=True, slots=True)
class SampleMemory:
    memory_type: str
    content: str
    source_uri: str


SAMPLES = (
    SampleMemory("decision", "Project Atlas uses reversible database migrations with a documented rollback step.", "reviewer://atlas/architecture-001"),
    SampleMemory("constraint", "Project Atlas test fixtures must contain synthetic data and must never contain credentials.", "reviewer://atlas/security-002"),
    SampleMemory("procedure", "Project Atlas memory changes are proposed first, reviewed by a workspace owner, and activated only after approval.", "reviewer://atlas/workflow-003"),
)


def seed(database_url: str, email: str) -> dict[str, object]:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install ninai-cloud before seeding") from exc
    clean_email = email.strip().lower()
    if "@" not in clean_email:
        raise ValueError("a valid reviewer email is required")
    apply_migrations(database_url)
    with psycopg.connect(database_url, row_factory=dict_row) as db:
        user = db.execute("SELECT id,email FROM users WHERE lower(email)=%s AND deleted_at IS NULL", (clean_email,)).fetchone()
        if not user:
            raise ValueError("reviewer must sign up at /control/login?screen_hint=signup before seeding")
        workspace = db.execute("SELECT id,owner_user_id FROM workspaces WHERE slug='ninai-directory-review' AND deleted_at IS NULL").fetchone()
        if workspace and str(workspace["owner_user_id"]) != str(user["id"]):
            raise ValueError("the reviewer workspace slug already belongs to another account")
        workspace_id = str(workspace["id"]) if workspace else str(uuid.uuid4())
        if not workspace:
            db.execute("INSERT INTO workspaces(id,name,slug,owner_user_id) VALUES(%s,'Ninai Directory Review','ninai-directory-review',%s)", (workspace_id, user["id"]))
        db.execute("""INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')
                      ON CONFLICT(workspace_id,user_id) DO UPDATE SET role='owner',revoked_at=NULL""", (workspace_id, user["id"]))
        project = db.execute("SELECT id FROM projects WHERE workspace_id=%s AND slug='project-atlas'", (workspace_id,)).fetchone()
        project_id = str(project["id"]) if project else str(uuid.uuid4())
        if not project:
            db.execute("INSERT INTO projects(id,workspace_id,name,slug,description) VALUES(%s,%s,'Project Atlas','project-atlas','Synthetic, non-sensitive directory review workspace')", (project_id, workspace_id))
        memory_ids: list[str] = []
        for sample in SAMPLES:
            memory = db.execute("""SELECT id FROM memories WHERE workspace_id=%s AND scope_kind='project'
                                   AND scope_id=%s AND memory_type=%s AND normalized_content=%s AND status='active'""",
                                (workspace_id, project_id, sample.memory_type, sample.content.lower())).fetchone()
            memory_id = str(memory["id"]) if memory else str(uuid.uuid4())
            if not memory:
                db.execute("""INSERT INTO memories(id,workspace_id,project_id,owner_user_id,memory_type,scope_kind,
                              scope_id,content,normalized_content,status,risk_level,authority,confidence,importance,
                              write_mode_requested,write_mode_applied,created_by_user_id,last_verified_at)
                              VALUES(%s,%s,%s,%s,%s,'project',%s,%s,%s,'active','low',1,1,.8,'propose','review',%s,now())""",
                           (memory_id, workspace_id, project_id, user["id"], sample.memory_type, project_id,
                            sample.content, sample.content.lower(), user["id"]))
            source = db.execute("SELECT 1 FROM memory_sources WHERE workspace_id=%s AND memory_id=%s AND source_uri=%s", (workspace_id, memory_id, sample.source_uri)).fetchone()
            if not source:
                db.execute("""INSERT INTO memory_sources(id,workspace_id,memory_id,source_type,source_uri,provider,
                              excerpt,content_hash,authority,occurred_at) VALUES(%s,%s,%s,'review_fixture',%s,'ninai',%s,%s,1,now())""",
                           (str(uuid.uuid4()), workspace_id, memory_id, sample.source_uri, sample.content,
                            hashlib.sha256(sample.content.encode()).hexdigest()))
            memory_ids.append(memory_id)
    return {"workspace_id": workspace_id, "project_id": project_id, "memory_ids": memory_ids}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Existing Auth0/Ninai reviewer account email")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is required")
    try:
        result = seed(database_url, args.email)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print("Reviewer fixture ready:", result)


if __name__ == "__main__":
    main()
