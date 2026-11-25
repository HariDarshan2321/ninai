"""Transactional control and context release for opt-in team workspaces."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
import hashlib
import json
import re
import secrets
from typing import Any, Callable, ContextManager, Iterator
from uuid import UUID, uuid4

from .postgres_store import AuthorizationError
from .rate_limit import RateLimitError
from .team_packet import DEFAULT_PACKET_TOKENS
from .team_repo import repository_key
from .team_sources import parse_source_reference

ROLES = {"admin", "member"}
ACTIONS = {"read", "propose", "view-history", "read-handoffs", "publish-handoff"}
ADMIN = {"owner", "admin"}
DENIED = "Team access is unavailable"
HOURLY_CREATE_LIMITS = {"invite": 20, "create-group": 10, "create-project": 10,
                        "issue-binding": 20, "propose": 60, "publish-handoff": 20}
MAX_INSPECTION_ITEMS = 256
MAX_AUDIT_ITEMS = 100


def identifier(value: Any) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid identifier") from error


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def bounded_text(value: Any, maximum: int, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"Invalid {label}")
    return value.strip()


def require_row(row: Any) -> Any:
    if not row:
        raise AuthorizationError(DENIED)
    return row


@dataclass(frozen=True)
class TeamHuman:
    user_id: str
    issuer: str
    subject: str
    expires_at: int
    verified_email: str | None = None


@dataclass(frozen=True)
class TeamPrincipal:
    user_id: str
    role: str
    binding_id: str | None = None


class TeamStore:
    def __init__(self, connect: Callable[[], ContextManager[Any]], *, verifier=None,
                 bootstrap_user_ids: frozenset[str] | None = None):
        self._connect = connect
        self.verifier = verifier
        self._bootstrap_user_ids = bootstrap_user_ids

    def can_create_team(self, human: TeamHuman) -> bool:
        return self._bootstrap_user_ids is None or human.user_id in self._bootstrap_user_ids

    def check_ready(self) -> None:
        with self._connect() as db:
            db.execute("SELECT 1").fetchone()

    @contextmanager
    def _tenant(self, workspace: str, *, lock: bool = False) -> Iterator[Any]:
        with self._connect() as db, db.transaction():
            db.execute("SET LOCAL search_path TO pg_catalog, public, pg_temp")
            db.execute("SELECT set_config('ninai.team_workspace_id', %s, true)", (identifier(workspace),))
            db.execute("SELECT set_config('lock_timeout', '2s', true)")
            db.execute("SELECT set_config('statement_timeout', '5s', true)")
            if lock:
                # Team writes and packet finalization share the same tenant fence.
                db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (workspace,))
            yield db

    @staticmethod
    def _workspace(db, workspace):
        return require_row(db.execute("""
            SELECT t.authorization_epoch FROM team_workspaces t
            JOIN workspaces w ON w.id=t.workspace_id
            WHERE t.workspace_id=%s AND t.quarantined_at IS NULL AND w.deleted_at IS NULL
        """, (workspace,)).fetchone())

    @staticmethod
    def _check_human_expiry(human):
        if human.expires_at <= time.time():
            raise AuthorizationError(DENIED)

    def _human(self, db, workspace, human, *, admin=False):
        self._check_human_expiry(human)
        self._workspace(db, workspace)
        row = require_row(db.execute("""
            SELECT m.role FROM team_members m
            JOIN users u ON u.id=m.user_id AND u.deleted_at IS NULL
            JOIN oauth_identities o ON o.user_id=u.id AND o.issuer=%s AND o.subject=%s
            WHERE m.workspace_id=%s AND m.user_id=%s AND m.revoked_at IS NULL
        """, (human.issuer, human.subject, workspace, human.user_id)).fetchone())
        if admin and row["role"] not in ADMIN:
            raise AuthorizationError(DENIED)
        return TeamPrincipal(human.user_id, row["role"])

    @staticmethod
    def _projects(db, workspace, user, *, project=None, include_unassigned=False):
        return db.execute("""
            SELECT id,name,repository,access,maintainer FROM (
                SELECT p.id,p.name,p.repository,COALESCE(pm.role='maintainer', false) AS maintainer,
                    pm.user_id IS NOT NULL OR EXISTS (
                        SELECT 1 FROM team_group_projects gp
                        JOIN team_groups g ON (g.workspace_id,g.id)=(gp.workspace_id,gp.group_id)
                            AND g.archived_at IS NULL
                        JOIN team_group_members gm ON (gm.workspace_id,gm.group_id)=(gp.workspace_id,gp.group_id)
                            AND gm.revoked_at IS NULL AND gm.user_id=%s
                        WHERE (gp.workspace_id,gp.project_id)=(p.workspace_id,p.id) AND gp.revoked_at IS NULL
                    ) AS access
                FROM team_projects p
                LEFT JOIN team_project_members pm ON (pm.workspace_id,pm.project_id,pm.user_id)
                    =(p.workspace_id,p.id,%s) AND pm.revoked_at IS NULL
                WHERE p.workspace_id=%s AND p.archived_at IS NULL AND (%s::uuid IS NULL OR p.id=%s)
            ) inventory
            WHERE access OR %s
            ORDER BY access DESC,name,id LIMIT 250
        """, (user, user, workspace, project, project, include_unassigned))

    def _project(self, db, workspace, project, user):
        return require_row(self._projects(db, workspace, user, project=project).fetchone())

    @staticmethod
    def _require_repository(db, workspace, project, repository):
        require_row(db.execute(
            "SELECT 1 FROM team_projects WHERE workspace_id=%s AND id=%s AND repository=%s",
            (workspace, project, repository),
        ).fetchone())

    @staticmethod
    def _advance(db, workspace):
        db.execute("""UPDATE team_workspaces SET authorization_epoch=authorization_epoch+1
                      WHERE workspace_id=%s""", (workspace,))

    @staticmethod
    def _audit(db, workspace, principal, action, *, project=None, outcome="applied", reason=None,
               request_id=None):
        event = str(uuid4())
        db.execute("""
            INSERT INTO team_audit_events(workspace_id,id,project_id,actor_user_id,binding_id,
                request_id,action,outcome,reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (workspace, event, project, principal.user_id, principal.binding_id,
              request_id or str(uuid4()), action, outcome, reason))
        return event

    @staticmethod
    def _check_create_quota(db, workspace, actor, action):
        # Call only after live authorization and under the tenant write fence.
        # A sponsor shares their proposal budget with all sponsored bindings.
        recent = db.execute("""
            SELECT 1 FROM team_audit_events
            WHERE workspace_id=%s AND actor_user_id=%s AND action=%s AND outcome='applied'
              AND recorded_at>statement_timestamp()-interval '1 hour'
            ORDER BY recorded_at DESC OFFSET %s LIMIT 1
        """, (workspace, actor.user_id, action, HOURLY_CREATE_LIMITS[action] - 1)).fetchone()
        if recent:
            raise RateLimitError("Team creation quota reached", retry_after=3600)

    def enable(self, workspace, human):
        """Opt in as the verified legacy workspace owner. No legacy access is copied."""
        self._check_human_expiry(human)
        with self._tenant(workspace, lock=True) as db:
            if not self.can_create_team(human):
                require_row(db.execute("SELECT 1 FROM team_workspaces WHERE workspace_id=%s",
                                       (workspace,)).fetchone())
            require_row(db.execute("""
                SELECT w.id FROM workspaces w
                JOIN workspace_members m ON m.workspace_id=w.id AND m.user_id=w.owner_user_id
                JOIN users u ON u.id=m.user_id AND u.deleted_at IS NULL
                JOIN oauth_identities o ON o.user_id=u.id AND o.issuer=%s AND o.subject=%s
                WHERE w.id=%s AND m.user_id=%s AND m.role='owner'
                  AND m.revoked_at IS NULL AND w.deleted_at IS NULL
            """, (human.issuer, human.subject, workspace, human.user_id)).fetchone())
            created = db.execute("""
                INSERT INTO team_workspaces(workspace_id) VALUES(%s)
                ON CONFLICT DO NOTHING RETURNING workspace_id
            """, (workspace,)).fetchone()
            if created:
                db.execute("INSERT INTO team_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')",
                           (workspace, human.user_id))
                self._audit(db, workspace, TeamPrincipal(human.user_id, "owner"), "enable")
            self._human(db, workspace, human)
        return {"workspace_id": workspace}

    def invite(self, workspace, human, *, issuer=None, subject=None, role="member", email=None, project=None):
        if role not in ROLES or (email is None) == (subject is None):
            raise ValueError("Enter one invitation recipient")
        if email is not None:
            email = bounded_text(email, 254, "recipient email").lower()
            if issuer is not None or role != "member" or project is None or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                raise ValueError("Enter a valid email and select a project")
            issuer = human.issuer
        else:
            if issuer != human.issuer or project is not None:
                raise ValueError("Invalid invitation issuer or project")
            subject = bounded_text(subject, 255, "recipient subject")
        token = new_token()
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            if role == "admin" and actor.role != "owner":
                raise AuthorizationError(DENIED)
            if project is not None:
                self._project(db, workspace, project, actor.user_id)
            self._check_create_quota(db, workspace, actor, "invite")
            db.execute("""
                INSERT INTO team_invitations(workspace_id,id,inviter_user_id,recipient_issuer,
                    recipient_subject,recipient_email,project_id,role,token_hash,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,now()+interval '24 hours')
            """, (workspace, str(uuid4()), actor.user_id, issuer, subject, email, project, role, digest(token)))
            self._audit(db, workspace, actor, "invite")
        return {"invitation_token": token}

    def accept_invite(self, workspace, human, *, token):
        token = bounded_text(token, 128, "invitation")
        with self._tenant(workspace, lock=True) as db:
            self._check_human_expiry(human)
            self._workspace(db, workspace)
            row = require_row(db.execute("""
                SELECT i.id,i.role,i.project_id FROM team_invitations i
                JOIN team_members m ON (m.workspace_id,m.user_id)=(i.workspace_id,i.inviter_user_id)
                    AND m.revoked_at IS NULL AND m.role IN ('owner','admin')
                JOIN users inviter ON inviter.id=m.user_id AND inviter.deleted_at IS NULL
                JOIN oauth_identities o ON o.issuer=i.recipient_issuer
                    AND o.user_id=%s AND o.issuer=%s AND o.subject=%s
                JOIN users u ON u.id=o.user_id AND u.deleted_at IS NULL
                WHERE i.workspace_id=%s AND i.token_hash=%s AND i.accepted_at IS NULL
                    AND i.revoked_at IS NULL AND i.expires_at>clock_timestamp()
                    AND (i.role<>'admin' OR m.role='owner')
                    AND (i.recipient_subject=o.subject OR i.recipient_email=%s)
                    AND NOT EXISTS (
                        SELECT 1 FROM team_members recipient
                        WHERE recipient.workspace_id=i.workspace_id AND recipient.user_id=u.id
                          AND recipient.revoked_at>=i.created_at
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM team_project_members recipient
                        WHERE recipient.workspace_id=i.workspace_id AND recipient.project_id=i.project_id
                          AND recipient.user_id=u.id AND recipient.revoked_at>=i.created_at
                    )
            """, (human.user_id, human.issuer, human.subject, workspace, digest(token),
                  human.verified_email.strip().lower() if human.verified_email else None)).fetchone())
            if row["project_id"] is not None:
                require_row(db.execute("""
                    SELECT 1 FROM team_projects WHERE workspace_id=%s AND id=%s AND archived_at IS NULL
                """, (workspace, row["project_id"])).fetchone())
            db.execute("""
                INSERT INTO team_members(workspace_id,user_id,role) VALUES(%s,%s,%s)
                ON CONFLICT(workspace_id,user_id) DO UPDATE SET role=excluded.role,revoked_at=NULL
                WHERE team_members.revoked_at IS NOT NULL
            """, (workspace, human.user_id, row["role"]))
            if row["project_id"] is not None:
                db.execute("""
                    INSERT INTO team_project_members(workspace_id,project_id,user_id,role) VALUES(%s,%s,%s,'member')
                    ON CONFLICT(workspace_id,project_id,user_id) DO UPDATE SET role='member',revoked_at=NULL
                    WHERE team_project_members.revoked_at IS NOT NULL
                """, (workspace, row["project_id"], human.user_id))
            db.execute("""
                UPDATE team_invitations SET accepted_at=clock_timestamp(),accepted_by_user_id=%s
                WHERE workspace_id=%s AND id=%s
            """, (human.user_id, workspace, row["id"]))
            actor = self._human(db, workspace, human)
            self._advance(db, workspace)
            self._audit(db, workspace, actor, "accept-invite")
        result = {"workspace_id": workspace}
        if row["project_id"] is not None:
            result["project_id"] = str(row["project_id"])
        return result

    def assign_project(self, workspace, human, *, project, user, role="member"):
        if role not in {"member", "maintainer", "remove"}:
            raise ValueError("Invalid project role")
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            require_row(db.execute("""
                SELECT p.id FROM team_projects p JOIN team_members m ON m.workspace_id=p.workspace_id
                JOIN users u ON u.id=m.user_id AND u.deleted_at IS NULL
                WHERE p.workspace_id=%s AND p.id=%s AND m.user_id=%s
                  AND m.revoked_at IS NULL AND p.archived_at IS NULL
            """, (workspace, project, user)).fetchone())
            if role == "remove":
                db.execute("""
                    UPDATE team_project_members SET revoked_at=clock_timestamp()
                    WHERE workspace_id=%s AND project_id=%s AND user_id=%s AND revoked_at IS NULL
                """, (workspace, project, user))
            else:
                db.execute("""
                    INSERT INTO team_project_members(workspace_id,project_id,user_id,role)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(workspace_id,project_id,user_id)
                    DO UPDATE SET role=excluded.role,revoked_at=NULL
                """, (workspace, project, user, role))
            self._advance(db, workspace)
            self._audit(db, workspace, actor, "project-membership", project=project, reason=user)
        return {"updated": True}

    def change_member(self, workspace, human, *, user, role):
        if role not in ROLES | {"remove"}:
            raise ValueError("Invalid workspace role")
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            current = require_row(db.execute("""
                SELECT role FROM team_members WHERE workspace_id=%s AND user_id=%s AND revoked_at IS NULL
            """, (workspace, user)).fetchone())
            if current["role"] == "owner" or (
                actor.role != "owner" and (current["role"] == "admin" or role == "admin")
            ):
                raise AuthorizationError(DENIED)
            if role == "remove":
                for table, member_column in (
                    ("team_members", "user_id"), ("team_project_members", "user_id"),
                    ("team_group_members", "user_id"), ("team_decision_reviewers", "user_id"),
                    ("team_bindings", "sponsor_user_id"), ("team_invitations", "inviter_user_id"),
                ):
                    # Table and column are fixed application identifiers.
                    db.execute(f"""UPDATE {table} SET revoked_at=clock_timestamp()
                            WHERE workspace_id=%s AND {member_column}=%s AND revoked_at IS NULL""",
                               (workspace, user))
                db.execute("""
                    UPDATE team_invitations i SET revoked_at=clock_timestamp()
                    FROM oauth_identities o
                    WHERE i.workspace_id=%s AND o.user_id=%s
                      AND (i.recipient_issuer,i.recipient_subject)=(o.issuer,o.subject)
                      AND i.accepted_at IS NULL AND i.revoked_at IS NULL
                """, (workspace, user))
            else:
                db.execute("UPDATE team_members SET role=%s WHERE workspace_id=%s AND user_id=%s",
                           (role, workspace, user))
            self._advance(db, workspace)
            self._audit(db, workspace, actor, "offboard" if role == "remove" else "workspace-role",
                        reason=user)
        return {"updated": True}

    def create_group(self, workspace, human, *, name):
        name = bounded_text(name, 100, "group name")
        group = str(uuid4())
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            self._check_create_quota(db, workspace, actor, "create-group")
            db.execute("INSERT INTO team_groups(workspace_id,id,name) VALUES(%s,%s,%s)",
                       (workspace, group, name))
            self._audit(db, workspace, actor, "create-group", reason=group)
        return {"group_id": group}

    def group_edge(self, workspace, human, *, group, subject, kind, active):
        if kind not in {"member", "project"} or type(active) is not bool:
            raise ValueError("Invalid group membership")
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            require_row(db.execute("""
                SELECT id FROM team_groups WHERE workspace_id=%s AND id=%s AND archived_at IS NULL
            """, (workspace, group)).fetchone())
            if kind == "member":
                require_row(db.execute("""
                    SELECT user_id FROM team_members WHERE workspace_id=%s AND user_id=%s AND revoked_at IS NULL
                """, (workspace, subject)).fetchone())
                table, column = "team_group_members", "user_id"
            else:
                require_row(db.execute("""
                    SELECT id FROM team_projects WHERE workspace_id=%s AND id=%s AND archived_at IS NULL
                """, (workspace, subject)).fetchone())
                table, column = "team_group_projects", "project_id"
            if active:
                db.execute(f"""
                    INSERT INTO {table}(workspace_id,group_id,{column}) VALUES(%s,%s,%s)
                    ON CONFLICT(workspace_id,group_id,{column}) DO UPDATE SET revoked_at=NULL
                """, (workspace, group, subject))
            else:
                db.execute(f"""
                    UPDATE {table} SET revoked_at=clock_timestamp()
                    WHERE workspace_id=%s AND group_id=%s AND {column}=%s AND revoked_at IS NULL
                """, (workspace, group, subject))
            self._advance(db, workspace)
            self._audit(db, workspace, actor, f"group-{kind}",
                        project=subject if kind == "project" else None, reason=f"{group}:{subject}")
        return {"updated": True}

    def issue_binding(self, workspace, human, *, project, client, actions, kind="human"):
        client = bounded_text(client, 80, "assistant registration")
        if kind not in {"human", "service"} or not isinstance(actions, list) or any(
                not isinstance(action, str) or action not in ACTIONS for action in actions):
            raise ValueError("Invalid binding actions")
        if len(actions) != len(set(actions)):
            raise ValueError("Duplicate binding action")
        binding, token = str(uuid4()), new_token()
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human)
            self._project(db, workspace, project, actor.user_id)
            if kind == "service" and actor.role not in ADMIN:
                raise AuthorizationError(DENIED)
            self._check_create_quota(db, workspace, actor, "issue-binding")
            row = db.execute("""
                INSERT INTO team_bindings(workspace_id,project_id,id,sponsor_user_id,
                    kind,client_registration,token_hash,expires_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp()+interval '1 hour')
                RETURNING expires_at
            """, (workspace, project, binding, actor.user_id, kind, client, digest(token))).fetchone()
            for action in actions:
                db.execute("""
                    INSERT INTO team_binding_actions(workspace_id,project_id,binding_id,action)
                    VALUES(%s,%s,%s,%s)
                """, (workspace, project, binding, action))
            self._audit(db, workspace, actor, "issue-binding", project=project, reason=binding)
        return {"binding_id": binding, "token": token, "expires_at": row["expires_at"]}

    def check_binding(self, workspace, project, human, *, binding):
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, human, "read")
            require_row(db.execute("""
                SELECT 1 FROM team_bindings
                WHERE workspace_id=%s AND project_id=%s AND id=%s AND sponsor_user_id=%s
                  AND revoked_at IS NULL AND expires_at>clock_timestamp()
            """, (workspace, project, binding, actor.user_id)).fetchone())
            used = db.execute("""
                SELECT 1 FROM team_audit_events WHERE workspace_id=%s AND project_id=%s AND binding_id=%s
                  AND actor_user_id=%s AND action IN ('read','read-handoffs')
                  AND outcome IN ('released','packet','empty','conflict','abstain')
                LIMIT 1
            """, (workspace, project, binding, actor.user_id)).fetchone()
        return {"connected": bool(used)}

    def update_binding(self, workspace, human, *, project, binding, operation):
        if operation not in {"revoke", "rotate"}:
            raise ValueError("Invalid binding operation")
        result = {"updated": True}
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human)
            administrative_revoke = operation == "revoke" and actor.role in ADMIN
            if not administrative_revoke:
                self._project(db, workspace, project, actor.user_id)
            row = require_row(db.execute("""
                SELECT sponsor_user_id FROM team_bindings
                WHERE workspace_id=%s AND project_id=%s AND id=%s AND revoked_at IS NULL
            """, (workspace, project, binding)).fetchone())
            own = str(row["sponsor_user_id"]) == actor.user_id
            if not own and not administrative_revoke:
                raise AuthorizationError(DENIED)
            if operation == "revoke":
                db.execute("""
                    UPDATE team_bindings SET revoked_at=clock_timestamp()
                    WHERE workspace_id=%s AND project_id=%s AND id=%s
                """, (workspace, project, binding))
            else:
                token = new_token()
                updated = db.execute("""
                    UPDATE team_bindings SET token_hash=%s,expires_at=clock_timestamp()+interval '1 hour'
                    WHERE workspace_id=%s AND project_id=%s AND id=%s RETURNING expires_at
                """, (digest(token), workspace, project, binding)).fetchone()
                result.update(token=token, expires_at=updated["expires_at"])
            self._advance(db, workspace)
            self._audit(db, workspace, actor, f"{operation}-binding", project=project, reason=binding)
        return result

    def _assistant(self, db, workspace, project, token, action):
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise AuthorizationError(DENIED)
        self._workspace(db, workspace)
        row = require_row(db.execute("""
            SELECT b.id,b.sponsor_user_id,b.kind,m.role
            FROM team_bindings b JOIN team_members m
              ON (m.workspace_id,m.user_id)=(b.workspace_id,b.sponsor_user_id)
            JOIN users u ON u.id=m.user_id AND u.deleted_at IS NULL
            JOIN team_binding_actions a
              ON (a.workspace_id,a.project_id,a.binding_id)=(b.workspace_id,b.project_id,b.id)
            WHERE b.workspace_id=%s AND b.project_id=%s AND b.token_hash=%s
              AND b.audience='ninai-team' AND b.expires_at>clock_timestamp()
              AND b.revoked_at IS NULL AND m.revoked_at IS NULL
              AND a.action=%s AND a.revoked_at IS NULL
              AND (b.kind='human' OR m.role IN ('owner','admin'))
        """, (workspace, project, digest(token), action)).fetchone())
        user = str(row["sponsor_user_id"])
        self._project(db, workspace, project, user)
        return TeamPrincipal(user, row["role"], str(row["id"]))

    def _authorize(self, db, workspace, project, credential, action):
        if isinstance(credential, TeamHuman):
            actor = self._human(db, workspace, credential)
            role = self._project(db, workspace, project, actor.user_id)
            if action == "review" and actor.role not in ADMIN and not role["maintainer"]:
                raise AuthorizationError(DENIED)
            return actor
        return self._assistant(db, workspace, project, credential, action)

    @staticmethod
    def _record_state(db, workspace, project, decision, version, state, actor):
        db.execute("""
            INSERT INTO team_decision_events(workspace_id,project_id,decision_id,version,state,actor_user_id)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (workspace, project, decision, version, state, actor.user_id))

    @staticmethod
    def _audit_item(db, workspace, audit, project, decision, version, status=None):
        from psycopg.types.json import Jsonb

        states = {"result": status} if isinstance(status, str) else (status or {})
        db.execute("""
            INSERT INTO team_audit_items(workspace_id,event_id,project_id,decision_id,version,source_status)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (workspace, audit, project, decision, version, Jsonb(states)))

    def propose(self, workspace, project, credential, *, topic, rule, rationale=None, visibility="team",
                paths=None, terms=None, links=None, expires_hours=None, decision=None, repository=None):
        from .postgres_store import _contains_secret

        topic = bounded_text(topic, 80, "topic")
        rule = bounded_text(rule, 500, "rule")
        rationale = bounded_text(rationale, 600, "rationale") if rationale is not None else None
        if any(_contains_secret(value) for value in (topic, rule, rationale or "")):
            raise ValueError("Decision contains a credential")
        if visibility not in {"team", "private"}:
            raise ValueError("Invalid decision visibility")
        paths = [] if paths is None else paths
        terms = [] if terms is None else terms
        links = [] if links is None else links
        if not isinstance(paths, list) or len(paths) > 12 or not isinstance(terms, list) or len(terms) > 12:
            raise ValueError("Invalid decision scope")
        paths = [bounded_text(path, 240, "path") for path in paths]
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+:[^:]+", path) or
               any(part in {"", ".", ".."} for part in path.split(":", 1)[1].split("/"))
               for path in paths):
            raise ValueError("Paths must use repository:path")
        terms = [bounded_text(term, 80, "scope term") for term in terms]
        if any(_contains_secret(value) for value in paths + terms):
            raise ValueError("Decision scope contains a credential")
        if not paths and not terms:
            raise ValueError("Decision must have a task or path scope")
        if not isinstance(links, list) or not 1 <= len(links) <= 4:
            raise ValueError("Provide one to four source links")
        refs = [parse_source_reference(link) for link in links]
        if len(set(refs)) != len(refs):
            raise ValueError("Duplicate source link")
        if expires_hours is not None and (type(expires_hours) is not int or not 1 <= expires_hours <= 8760):
            raise ValueError("Invalid expiry")

        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, credential, "propose")
            if repository is not None:
                self._require_repository(db, workspace, project, repository_key(repository))
            self._check_create_quota(db, workspace, actor, "propose")
            if decision is None:
                decision = str(uuid4())
                version = 1
                db.execute("""
                    INSERT INTO team_decisions(workspace_id,project_id,id,created_by_user_id,visibility,topic)
                    VALUES(%s,%s,%s,%s,%s,%s)
                """, (workspace, project, decision, actor.user_id, visibility, topic))
            else:
                require_row(db.execute("""
                    SELECT id FROM team_decisions WHERE workspace_id=%s AND project_id=%s AND id=%s
                        AND created_by_user_id=%s AND visibility=%s AND topic=%s
                """, (workspace, project, decision, actor.user_id, visibility, topic)).fetchone())
                version = db.execute("""
                    SELECT max(version)+1 AS next FROM team_decision_versions
                    WHERE workspace_id=%s AND project_id=%s AND decision_id=%s
                """, (workspace, project, decision)).fetchone()["next"]
                for pending in self._decisions(db, workspace, project, actor.user_id, decision=decision,
                                               mode="review"):
                    self._record_state(db, workspace, project, decision, pending["version"], "retired", actor)
            db.execute("""
                INSERT INTO team_decision_versions(workspace_id,project_id,decision_id,version,rule,
                    rationale,scope_paths,scope_terms,expires_at,proposed_by_user_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp()+%s::interval,%s)
            """, (workspace, project, decision, version, rule, rationale, paths, terms,
                  timedelta(hours=expires_hours) if expires_hours else None, actor.user_id))
            for ref in refs:
                db.execute("""
                    INSERT INTO team_decision_sources(workspace_id,project_id,decision_id,version,
                        provider,resource_key,source_url,required)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,true)
                """, (workspace, project, decision, version, ref.provider, ref.resource_key, ref.canonical_url))
            self._record_state(db, workspace, project, decision, version, "proposed", actor)
            self._advance(db, workspace)
            event = self._audit(db, workspace, actor, "propose", project=project)
            self._audit_item(db, workspace, event, project, decision, version)
        return {"decision_id": decision, "version": version, "status": "proposed"}

    @staticmethod
    def _decisions(db, workspace, project, user, *, decision=None, version=None, mode="active", pairs=None,
                   only_own_proposals=False):
        # Payload access is narrower than administration. The review queue cannot
        # select another person's private proposal without a reviewer grant.
        lifecycle = {
            "active": "state.state='approved'",
            "replaced": "state.state='replaced'",
            "history": "state.state IN ('approved','replaced','expired','retired','revoked')",
            "historical": "(state.state IN ('replaced','expired','retired','revoked') OR "
                          "(state.state='approved' AND v.expires_at <= statement_timestamp()))",
            "review": "state.state='proposed'",
            "audit": "state.state IN ('proposed','approved','replaced','expired','retired','revoked')",
        }[mode]
        pair_join = ""
        pair_args = ()
        if pairs is not None:
            if not pairs:
                return []
            ids, versions = zip(*pairs)
            pair_join = """JOIN unnest(%s::uuid[], %s::integer[]) AS requested(id, version)
                             ON (requested.id,requested.version)=(v.decision_id,v.version)"""
            pair_args = (list(ids), list(versions))
        return db.execute(f"""
            SELECT d.id,d.topic,d.visibility,d.created_by_user_id,v.version,v.rule,v.rationale,
                   v.scope_paths,v.scope_terms,v.expires_at,v.proposed_by_user_id,state.state,
                   s.replaces_decision_id,s.replaces_version
            FROM team_decisions d
            JOIN team_decision_versions v ON (v.workspace_id,v.project_id,v.decision_id)
                =(d.workspace_id,d.project_id,d.id)
            {pair_join}
            JOIN LATERAL (
                SELECT e.state FROM team_decision_events e
                WHERE (e.workspace_id,e.project_id,e.decision_id,e.version)
                    =(v.workspace_id,v.project_id,v.decision_id,v.version)
                ORDER BY e.sequence DESC LIMIT 1
            ) state ON true
            LEFT JOIN team_supersessions s ON (s.workspace_id,s.project_id,s.decision_id,s.version)
                =(v.workspace_id,v.project_id,v.decision_id,v.version)
            WHERE d.workspace_id=%s AND d.project_id=%s AND {lifecycle}
              AND (%s::uuid IS NULL OR d.id=%s) AND (%s::integer IS NULL OR v.version=%s)
              AND (NOT %s OR v.proposed_by_user_id=%s)
              AND (d.visibility='team' OR d.created_by_user_id=%s OR EXISTS (
                   SELECT 1 FROM team_decision_reviewers r
                   WHERE (r.workspace_id,r.project_id,r.decision_id)=(d.workspace_id,d.project_id,d.id)
                     AND r.user_id=%s AND r.revoked_at IS NULL))
            ORDER BY v.sequence DESC
        """, (*pair_args, workspace, project, decision, decision, version, version,
              only_own_proposals, user, user, user)).fetchall()

    @staticmethod
    def _sources(db, workspace, project, rows):
        if not rows:
            return {}
        ids, versions = zip(*{(row["id"], row["version"]) for row in rows})
        source_rows = db.execute("""
            SELECT s.id,s.decision_id,s.version,s.provider,s.resource_key,s.source_url,s.required,
                   p.fingerprint AS expected_fingerprint
            FROM team_decision_sources s
            JOIN unnest(%s::uuid[], %s::integer[]) AS requested(id, version)
              ON (requested.id,requested.version)=(s.decision_id,s.version)
            LEFT JOIN team_source_pins p
              ON (p.workspace_id,p.project_id,p.decision_id,p.version,p.source_id)
                =(s.workspace_id,s.project_id,s.decision_id,s.version,s.id)
            WHERE s.workspace_id=%s AND s.project_id=%s
            ORDER BY s.id
        """, (list(ids), list(versions), workspace, project)).fetchall()
        results = {}
        for row in source_rows:
            pair = row["decision_id"], row["version"]
            results.setdefault(pair, []).append(row)
        return results

    def _proofs(self, workspace, project, actor, epoch, sources, request_id):
        from .team_sources import SourceReference, SourceRequest

        results = {}
        checked = {}
        for group in sources.values():
            for source in group:
                ref = SourceReference(source["provider"], source["resource_key"], source["source_url"])
                request = SourceRequest(workspace, project, actor.user_id, actor.binding_id,
                                        epoch, ref, source["expected_fingerprint"], request_id)
                if request not in checked:
                    checked[request] = self.verifier.verify(request) if self.verifier else None
                results[source["decision_id"], source["version"], source["id"]] = (request, checked[request])
        return results

    @staticmethod
    def _clock(db):
        return db.execute("SELECT clock_timestamp() AS now").fetchone()["now"]

    def assign_reviewer(self, workspace, project, human, *, decision, user, active):
        if type(active) is not bool:
            raise ValueError("Invalid reviewer scope")
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, human, "propose")
            self._project(db, workspace, project, user)
            require_row(db.execute("""
                SELECT id FROM team_decisions WHERE workspace_id=%s AND project_id=%s AND id=%s
                    AND created_by_user_id=%s AND visibility='private'
            """, (workspace, project, decision, actor.user_id)).fetchone())
            require_row(db.execute("""
                SELECT user_id FROM team_members WHERE workspace_id=%s AND user_id=%s AND revoked_at IS NULL
            """, (workspace, user)).fetchone())
            if active:
                db.execute("""
                    INSERT INTO team_decision_reviewers(workspace_id,project_id,decision_id,user_id)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(workspace_id,project_id,decision_id,user_id)
                    DO UPDATE SET revoked_at=NULL
                """, (workspace, project, decision, user))
            else:
                db.execute("""
                    UPDATE team_decision_reviewers SET revoked_at=clock_timestamp()
                    WHERE workspace_id=%s AND project_id=%s AND decision_id=%s AND user_id=%s
                """, (workspace, project, decision, user))
            self._advance(db, workspace)
            self._audit(db, workspace, actor, "private-reviewer", project=project, reason=user)
        return {"updated": True}

    def review(self, workspace, project, human, *, decision, version, replaces=None, replaces_version=None):
        from .team_sources import proof_status, verified_fingerprint

        if type(version) is not int or version < 1 or (
                (replaces is None) != (replaces_version is None)) or (
                replaces_version is not None and (type(replaces_version) is not int or replaces_version < 1)):
            raise ValueError("Invalid decision versions")
        request_id = str(uuid4())
        with self._tenant(workspace) as db:
            actor = self._authorize(db, workspace, project, human, "review")
            epoch = self._workspace(db, workspace)["authorization_epoch"]
            rows = self._decisions(db, workspace, project, actor.user_id, decision=decision, version=version,
                                   mode="review")
            if replaces:
                rows += self._decisions(db, workspace, project, actor.user_id, decision=replaces,
                                        version=replaces_version)
            if len(rows) != 1 + bool(replaces):
                raise AuthorizationError(DENIED)
            sources = self._sources(db, workspace, project, rows)

        proofs = self._proofs(workspace, project, actor, epoch, sources, request_id)
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, human, "review")
            if self._workspace(db, workspace)["authorization_epoch"] != epoch:
                raise AuthorizationError(DENIED)
            now = self._clock(db)
            proposal = require_row(self._decisions(db, workspace, project, actor.user_id, decision=decision,
                                                  version=version, mode="review"))[0]
            if proposal["expires_at"] is not None and proposal["expires_at"] <= now:
                raise AuthorizationError(DENIED)
            require_row(db.execute("""
                SELECT user_id FROM team_members WHERE workspace_id=%s AND user_id=%s AND revoked_at IS NULL
            """, (workspace, proposal["proposed_by_user_id"])).fetchone())
            current = self._decisions(db, workspace, project, actor.user_id, decision=decision)
            if any(row["state"] == "approved" and
                   (str(row["id"]), row["version"]) != (replaces, replaces_version) for row in current):
                raise AuthorizationError(DENIED)
            predecessor = None
            if replaces:
                predecessor = require_row(self._decisions(db, workspace, project, actor.user_id, decision=replaces,
                                                          version=replaces_version))[0]
                if predecessor["state"] != "approved" or predecessor["topic"] != proposal["topic"] or (
                    predecessor["visibility"] != proposal["visibility"] or (
                        proposal["visibility"] == "private" and
                        predecessor["created_by_user_id"] != proposal["created_by_user_id"]
                    )
                ):
                    raise AuthorizationError(DENIED)
            current_rows = [proposal] + ([predecessor] if predecessor else [])
            if self._sources(db, workspace, project, current_rows) != sources:
                raise AuthorizationError(DENIED)
            # Provider checks are timestamped by this process. Use its clock
            # for proof freshness and PostgreSQL's clock for stored expirations.
            proof_now = datetime.now(timezone.utc)
            for row in current_rows:
                linked = require_row(sources.get((row["id"], row["version"])))
                for source in linked:
                    request, proof = proofs[row["id"], row["version"], source["id"]]
                    if row is predecessor:
                        if proof_status(request, proof, now=proof_now) != "verified":
                            raise AuthorizationError(DENIED)
                        continue
                    fingerprint = verified_fingerprint(request, proof, now=proof_now)
                    if not fingerprint:
                        raise AuthorizationError(DENIED)
                    db.execute("""
                        INSERT INTO team_source_pins(workspace_id,project_id,decision_id,version,source_id,fingerprint)
                        VALUES(%s,%s,%s,%s,%s,%s)
                    """, (workspace, project, decision, version, source["id"], fingerprint))
            if predecessor:
                db.execute("""
                    INSERT INTO team_supersessions(workspace_id,project_id,decision_id,version,
                        replaces_decision_id,replaces_version) VALUES(%s,%s,%s,%s,%s,%s)
                """, (workspace, project, decision, version, replaces, replaces_version))
                self._record_state(db, workspace, project, replaces, replaces_version, "replaced", actor)
            self._record_state(db, workspace, project, decision, version, "approved", actor)
            self._advance(db, workspace)
            event = self._audit(db, workspace, actor, "replace" if predecessor else "approve", project=project,
                                request_id=request_id)
            self._audit_item(db, workspace, event, project, decision, version, "verified")
            if predecessor:
                self._audit_item(db, workspace, event, project, replaces, replaces_version, "verified")
        return {"decision_id": decision, "version": version, "status": "approved"}

    def suppress(self, workspace, project, human, *, decision, version, state):
        if state not in {"retired", "revoked"} or type(version) is not int or version < 1:
            raise ValueError("Invalid decision transition")
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, human, "review")
            row = db.execute("""
                SELECT state FROM team_decision_events
                WHERE workspace_id=%s AND project_id=%s AND decision_id=%s AND version=%s
                ORDER BY sequence DESC LIMIT 1
            """, (workspace, project, decision, version)).fetchone()
            event = self._audit(db, workspace, actor, state, project=project)
            if row and row["state"] in {"approved", "proposed"}:
                self._record_state(db, workspace, project, decision, version, state, actor)
                self._audit_item(db, workspace, event, project, decision, version)
                self._advance(db, workspace)
        return {"recorded": True}

    @staticmethod
    def _packet_version(row, evidence=()):
        from .team_packet import DecisionVersion

        parent = row["replaces_decision_id"]
        parent_key = f"{parent}@{row['replaces_version']}" if parent else None
        return DecisionVersion(
            version_id=f"{row['id']}@{row['version']}", decision_id=str(row["id"]),
            version=row["version"], topic=row["topic"], rule=row["rule"], rationale=row["rationale"],
            status=row["state"], sources=tuple(evidence), scope_paths=tuple(row["scope_paths"]),
            scope_terms=tuple(row["scope_terms"]), expires_at=row["expires_at"], replaces_version_id=parent_key,
        )

    def _context_snapshot(self, db, workspace, project, credential, context, history_only, repository):
        from .team_packet import matches_task

        action = "view-history" if history_only else "read"
        actor = self._authorize(db, workspace, project, credential, action)
        if repository is not None:
            self._require_repository(db, workspace, project, repository)
        epoch = self._workspace(db, workspace)["authorization_epoch"]
        can_view_history = isinstance(credential, TeamHuman) or history_only
        if not can_view_history:
            can_view_history = bool(db.execute("""
                SELECT 1 FROM team_binding_actions
                WHERE workspace_id=%s AND project_id=%s AND binding_id=%s
                  AND action='view-history' AND revoked_at IS NULL
            """, (workspace, project, actor.binding_id)).fetchone())
        mode = "historical" if history_only else "active"
        rows = self._decisions(db, workspace, project, actor.user_id, mode=mode)
        now = self._clock(db)
        rows = [row for row in rows
                if (history_only or row["expires_at"] is None or row["expires_at"] > now)
                and matches_task(context, self._packet_version(row))]
        if can_view_history and not history_only:
            predecessors = {(row["replaces_decision_id"], row["replaces_version"]) for row in rows
                            if row["replaces_decision_id"] is not None}
            rows += [row for row in self._decisions(db, workspace, project, actor.user_id,
                                                    mode="replaced", pairs=predecessors)
                     if matches_task(context, self._packet_version(row))]
        return actor, epoch, can_view_history, rows, self._sources(db, workspace, project, rows)

    def context(self, workspace, project, credential, *, task, paths=None, max_items=6, max_tokens=DEFAULT_PACKET_TOKENS,
                history_only=False, repository=None, project_overview=False):
        from .team_packet import MAX_PACKET_ITEMS, MAX_PACKET_TOKENS, SourceEvidence, TaskContext, compose_task_packet
        from .team_sources import proof_status

        task = bounded_text(task, 1600, "task")
        paths = [] if paths is None else paths
        if not isinstance(paths, list) or len(paths) > 12 or type(history_only) is not bool:
            raise ValueError("Invalid task scope")
        paths = tuple(bounded_text(path, 240, "path") for path in paths)
        if type(max_items) is not int or not 1 <= max_items <= MAX_PACKET_ITEMS or (
            type(max_tokens) is not int or not 1 <= max_tokens <= MAX_PACKET_TOKENS
        ):
            raise ValueError("Invalid context budget")
        request_id = str(uuid4())
        repository = repository_key(repository) if repository is not None else None
        if type(project_overview) is not bool or project_overview and history_only:
            raise ValueError("A project overview requires current guidance.")
        context = TaskContext(task, paths, project_overview)
        try:
            with self._tenant(workspace) as db:
                snapshot = self._context_snapshot(db, workspace, project, credential, context, history_only, repository)
            actor, epoch, can_view_history, rows, sources = snapshot
            proofs = self._proofs(workspace, project, actor, epoch, sources, request_id)
            with self._tenant(workspace, lock=True) as db:
                if self._context_snapshot(db, workspace, project, credential, context, history_only, repository) != snapshot:
                    raise AuthorizationError(DENIED)
                now = self._clock(db)
                proof_now = datetime.now(timezone.utc)
                versions = []
                for row in rows:
                    evidence = []
                    for source in sources.get((row["id"], row["version"]), []):
                        verification, proof = proofs[row["id"], row["version"], source["id"]]
                        status = proof_status(verification, proof, now=proof_now)
                        evidence.append(SourceEvidence(str(source["id"]), status, source["required"],
                                                       source["source_url"]))
                    versions.append(self._packet_version(row, evidence))
                packet = compose_task_packet(context, versions, now=now, can_view_history=can_view_history,
                                             history_only=history_only, max_items=max_items, max_tokens=max_tokens)
                event = self._audit(db, workspace, actor, "view-history" if history_only else "read",
                                    project=project, outcome=packet.outcome, request_id=request_id)
                released = set(packet.released_versions)
                lineage = {edge["replaces"] for edge in (packet.payload or {}).get("lineage", [])}
                for version in versions:
                    if version.version_id in released:
                        if version.version_id in lineage:
                            status = {"delivery": "lineage"}
                        else:
                            status = {item.source_id: str(item.status) for item in version.sources
                                      if str(item.status) == "verified"}
                        self._audit_item(db, workspace, event, project, version.decision_id, version.version, status)
            return packet
        except AuthorizationError:
            self._record_context_denial(workspace, project, credential, history_only, request_id)
            raise

    def _record_context_denial(self, workspace, project, credential, history_only, request_id):
        """Record the first scoped denial in a minute without retaining unverified selectors."""
        action = "view-history" if history_only else "read"
        human = isinstance(credential, TeamHuman)
        if not human and (not isinstance(credential, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", credential)):
            return
        try:
            with self._tenant(workspace) as db:
                if human:
                    actor = self._human(db, workspace, credential)
                    authenticated_project = None
                else:
                    self._workspace(db, workspace)
                    row = require_row(db.execute("""
                        SELECT id,sponsor_user_id FROM team_bindings
                        WHERE workspace_id=%s AND project_id=%s AND token_hash=%s
                    """, (workspace, project, digest(credential))).fetchone())
                    actor = TeamPrincipal(str(row["sponsor_user_id"]), "", str(row["id"]))
                    authenticated_project = project
                # A per-actor/binding audit fence serializes coalescing across
                # processes without blocking unrelated revocations or writes.
                key = f"{workspace}:{actor.user_id}:{actor.binding_id}:{action}"
                locked = db.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 1)) AS locked",
                                    (key,)).fetchone()["locked"]
                if not locked:
                    return
                recent = db.execute("""
                    SELECT 1 FROM team_audit_events
                    WHERE workspace_id=%s AND actor_user_id=%s AND action=%s AND outcome='denied'
                      AND binding_id IS NOT DISTINCT FROM %s::uuid
                      AND recorded_at>statement_timestamp()-interval '1 minute'
                    LIMIT 1
                """, (workspace, actor.user_id, action, actor.binding_id)).fetchone()
                if not recent:
                    self._audit(db, workspace, actor, action, project=authenticated_project,
                                outcome="denied", reason="policy", request_id=request_id)
        except AuthorizationError:
            pass

    def overview(self, workspace, human):
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human)
            projects = self._projects(db, workspace, actor.user_id, include_unassigned=actor.role in ADMIN).fetchall()
            result = {"role": actor.role, "projects": projects}
            if actor.role in ADMIN:
                result["members"] = db.execute("""
                    SELECT m.user_id,m.role,u.display_name FROM team_members m JOIN users u ON u.id=m.user_id
                    WHERE m.workspace_id=%s AND m.revoked_at IS NULL AND u.deleted_at IS NULL
                    ORDER BY m.created_at,m.user_id LIMIT 250
                """, (workspace,)).fetchall()
                result["groups"] = db.execute("""
                    SELECT id,name FROM team_groups WHERE workspace_id=%s AND archived_at IS NULL
                    ORDER BY name,id LIMIT 250
                """, (workspace,)).fetchall()
            return result

    def create_project(self, workspace, human, *, name, repository=None, assign_creator=False):
        name = bounded_text(name, 100, "project name")
        if type(assign_creator) is not bool:
            raise ValueError("Invalid maintainer assignment")
        repository = repository_key(repository) if repository is not None else None
        project = str(uuid4())
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            self._check_create_quota(db, workspace, actor, "create-project")
            db.execute("""
                INSERT INTO team_projects(id,workspace_id,name,slug,repository) VALUES(%s,%s,%s,%s,%s)
            """, (project, workspace, name, f"team-{project}", repository))
            if assign_creator:
                db.execute("""
                    INSERT INTO team_project_members(workspace_id,project_id,user_id,role)
                    VALUES(%s,%s,%s,'maintainer')
                """, (workspace, project, actor.user_id))
            self._audit(db, workspace, actor, "create-project", project=project)
        return {"project_id": project}

    def connect_repository(self, workspace, human, *, project, repository):
        repository = repository_key(repository)
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            row = require_row(db.execute("""
                SELECT repository FROM team_projects WHERE workspace_id=%s AND id=%s AND archived_at IS NULL
            """, (workspace, project)).fetchone())
            if row["repository"] is None:
                db.execute("UPDATE team_projects SET repository=%s WHERE workspace_id=%s AND id=%s",
                           (repository, workspace, project))
                self._audit(db, workspace, actor, "connect-repository", project=project)
            elif row["repository"] != repository:
                raise AuthorizationError(DENIED)
        return {"updated": True}

    def publish_handoff(self, workspace, project, credential, *, request_key,
                        topic, status, summary, next_step=None, repository=None):
        from .postgres_store import _contains_secret

        repository = repository_key(repository) if repository is not None else None
        request_key = identifier(request_key)
        topic = bounded_text(topic, 80, "handoff topic")
        summary = bounded_text(summary, 400, "handoff summary")
        next_step = bounded_text(next_step, 240, "next step") if next_step is not None else None
        if status not in ("working", "blocked", "done") or any(
            _contains_secret(text) for text in (topic, summary, next_step or "")
        ):
            raise ValueError("Invalid handoff")
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, credential, "publish-handoff")
            if repository is not None:
                self._require_repository(db, workspace, project, repository)
            existing = db.execute("""
                SELECT id,topic,status,summary,next_step FROM team_handoffs
                WHERE workspace_id=%s AND project_id=%s AND author_user_id=%s AND request_key=%s
            """, (workspace, project, actor.user_id, request_key)).fetchone()
            if existing:
                if (existing["topic"], existing["status"], existing["summary"], existing["next_step"]) != (
                    topic, status, summary, next_step
                ):
                    raise ValueError("Handoff request key already used with different content")
                return {"id": str(existing["id"])}
            self._check_create_quota(db, workspace, actor, "publish-handoff")
            handoff = str(uuid4())
            db.execute("""
                INSERT INTO team_handoffs(workspace_id,project_id,id,author_user_id,request_key,topic,status,
                                          summary,next_step) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (workspace, project, handoff, actor.user_id, request_key, topic, status, summary, next_step))
            self._audit(db, workspace, actor, "publish-handoff", project=project, reason=handoff)
        return {"id": handoff}

    def handoffs(self, workspace, project, credential, *, repository=None):
        repository = repository_key(repository) if repository is not None else None
        request_id = str(uuid4())
        with self._tenant(workspace, lock=True) as db:
            actor = self._authorize(db, workspace, project, credential, "read-handoffs")
            if repository is not None:
                self._require_repository(db, workspace, project, repository)
            rows = db.execute("""
                SELECT latest.*,u.display_name FROM (
                    SELECT DISTINCT ON (author_user_id,lower(topic))
                        id,author_user_id,topic,status,summary,next_step,recorded_at
                    FROM team_handoffs WHERE workspace_id=%s AND project_id=%s
                        AND recorded_at>statement_timestamp()-interval '14 days'
                    ORDER BY author_user_id,lower(topic),recorded_at DESC,id DESC
                ) latest LEFT JOIN users u ON u.id=latest.author_user_id AND u.deleted_at IS NULL
                ORDER BY recorded_at DESC,id DESC LIMIT 8
            """, (workspace, project)).fetchall()
            items = []
            for row in rows:
                handoff = str(row["id"])
                item = {"id": handoff, "author": (row["display_name"] or "Team member")[:80],
                        "topic": row["topic"], "status": row["status"], "summary": row["summary"],
                        "next_step": row["next_step"], "recorded_at": row["recorded_at"].isoformat(),
                        "source_uri": f"ninai://team/{workspace}/projects/{project}/handoffs/{handoff}"}
                candidate = json.dumps({"items": [*items, item]}, ensure_ascii=True).encode("utf-8")
                if len(candidate) > 2048:
                    break
                items.append(item)
                self._audit(db, workspace, actor, "read-handoffs", project=project, outcome="released",
                            request_id=request_id, reason=handoff)
            if not items:
                self._audit(db, workspace, actor, "read-handoffs", project=project, outcome="empty",
                            request_id=request_id)
        return {"items": items}

    def archive_project(self, workspace, human, *, project):
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            archived = db.execute("""
                UPDATE team_projects SET archived_at=clock_timestamp()
                WHERE workspace_id=%s AND id=%s AND archived_at IS NULL RETURNING id
            """, (workspace, project)).fetchone()
            if archived:
                db.execute("""
                    UPDATE team_bindings SET revoked_at=clock_timestamp()
                    WHERE workspace_id=%s AND project_id=%s AND revoked_at IS NULL
                """, (workspace, project))
                self._advance(db, workspace)
                self._audit(db, workspace, actor, "archive-project", project=project)
        return {"updated": True}

    def proposals(self, workspace, project, human):
        return self._inspect_decisions(workspace, project, human, mode="review")

    def export_project(self, workspace, project, human):
        return self._inspect_decisions(workspace, project, human, mode="history")

    @staticmethod
    def _visible_sources(row, sources, proofs, now, *, review=False):
        from .team_sources import proof_status, verified_fingerprint

        pair = row["id"], row["version"]
        visible = []
        has_required_evidence = False
        for source in sources.get(pair, []):
            request, proof = proofs[(*pair, source["id"])]
            verified = (bool(verified_fingerprint(request, proof, now=now)) if review
                        else proof_status(request, proof, now=now) == "verified")
            if source["required"] and not verified:
                return None
            if verified:
                visible.append({"id": str(source["id"]), "url": source["source_url"]})
                has_required_evidence |= source["required"]
        return visible if has_required_evidence else None

    def _inspect_decisions(self, workspace, project, human, *, mode):
        if not isinstance(human, TeamHuman):
            raise AuthorizationError(DENIED)
        action = "inspect-proposals" if mode == "review" else "export-project"
        request_id = str(uuid4())

        def snapshot(db):
            actor = self._human(db, workspace, human)
            role = self._project(db, workspace, project, actor.user_id)
            if mode != "review" and actor.role not in ADMIN:
                raise AuthorizationError(DENIED)
            epoch = self._workspace(db, workspace)["authorization_epoch"]
            can_manage = actor.role in ADMIN or role["maintainer"]
            rows = self._decisions(db, workspace, project, actor.user_id, mode=mode,
                                   only_own_proposals=not can_manage)
            return actor, epoch, can_manage, rows, self._sources(db, workspace, project, rows)

        with self._tenant(workspace) as db:
            initial = snapshot(db)
        actor, epoch, _, rows, sources = initial
        proofs = self._proofs(workspace, project, actor, epoch, sources, request_id)
        with self._tenant(workspace, lock=True) as db:
            if snapshot(db) != initial:
                raise AuthorizationError(DENIED)
            now = self._clock(db)
            proof_now = datetime.now(timezone.utc)
            output = []
            event = self._audit(db, workspace, actor, action, project=project, request_id=request_id)
            for row in rows:
                visible_sources = self._visible_sources(row, sources, proofs, proof_now, review=mode == "review")
                if visible_sources is None:
                    continue
                output.append({
                    "decision_id": row["id"], "version": row["version"], "topic": row["topic"],
                    "rule": row["rule"], "rationale": row["rationale"], "visibility": row["visibility"],
                    "expires_at": row["expires_at"],
                    "status": "expired" if row["state"] == "approved" and row["expires_at"]
                    and row["expires_at"] <= now else row["state"],
                    "sources": visible_sources,
                })
                self._audit_item(db, workspace, event, project, row["id"], row["version"],
                                 {source["id"]: "verified" for source in visible_sources})
                if len(output) == MAX_INSPECTION_ITEMS:
                    break
        return {"items": output}

    @staticmethod
    def _project_audit_items(db, workspace, project, visible_versions):
        if not visible_versions:
            return []
        ids, versions = zip(*visible_versions)
        rows = db.execute("""
            SELECT e.id,e.actor_user_id,e.binding_id,e.request_id,e.recorded_at,e.action,
                   i.decision_id,i.version,i.source_status
            FROM team_audit_items i
            JOIN unnest(%s::uuid[], %s::integer[]) AS visible(decision_id, version) USING(decision_id,version)
            JOIN team_audit_events e ON (e.workspace_id,e.project_id,e.id)=(i.workspace_id,i.project_id,i.event_id)
            WHERE i.workspace_id=%s AND i.project_id=%s
              AND e.action IN ('read','view-history','inspect-proposals','export-project',
                               'propose','approve','replace','retired','revoked')
              AND (i.source_status->>'delivery') IS DISTINCT FROM 'lineage'
              AND (e.action<>'replace' OR EXISTS (
                    SELECT 1 FROM team_supersessions s
                    JOIN team_audit_items predecessor
                      ON (predecessor.workspace_id,predecessor.project_id,predecessor.event_id,
                          predecessor.decision_id,predecessor.version)
                       = (s.workspace_id,s.project_id,i.event_id,s.replaces_decision_id,s.replaces_version)
                    WHERE (s.workspace_id,s.project_id,s.decision_id,s.version)
                        =(i.workspace_id,i.project_id,i.decision_id,i.version)))
            ORDER BY e.recorded_at DESC,e.id DESC,i.decision_id,i.version
            LIMIT %s
        """, (list(ids), list(versions), workspace, project, MAX_AUDIT_ITEMS)).fetchall()
        for row in rows:
            action = row["action"]
            # Packet-level results can describe other items in the original event.
            # Each row exposes only the action as it relates to this visible item.
            row["outcome"] = ("released" if action in {"read", "view-history", "inspect-proposals", "export-project"}
                              else "applied")
            row["action"] = "review" if action in {"approve", "replace"} else action
            visible_ids = visible_versions[row["decision_id"], row["version"]]
            logged = row["source_status"]
            row["source_status"] = {source_id: "verified" for source_id in sorted(visible_ids)
                                    if logged.get(source_id) == "verified"}
            if row["action"] == "review" and logged.get("result") == "verified":
                row["source_status"]["result"] = "verified"
        return rows

    def export_project_audit(self, workspace, project, human):
        if not isinstance(human, TeamHuman):
            raise AuthorizationError(DENIED)
        request_id = str(uuid4())

        def snapshot(db):
            actor = self._human(db, workspace, human, admin=True)
            self._project(db, workspace, project, actor.user_id)
            epoch = self._workspace(db, workspace)["authorization_epoch"]
            rows = self._decisions(db, workspace, project, actor.user_id, mode="audit")
            return actor, epoch, rows, self._sources(db, workspace, project, rows)

        with self._tenant(workspace) as db:
            initial = snapshot(db)
        actor, epoch, rows, sources = initial
        proofs = self._proofs(workspace, project, actor, epoch, sources, request_id)
        with self._tenant(workspace, lock=True) as db:
            if snapshot(db) != initial:
                raise AuthorizationError(DENIED)
            proof_now = datetime.now(timezone.utc)
            visible_versions = {}
            for row in rows:
                visible = self._visible_sources(row, sources, proofs, proof_now, review=row["state"] == "proposed")
                if visible is not None:
                    visible_versions[row["id"], row["version"]] = {source["id"] for source in visible}
            items = self._project_audit_items(db, workspace, project, visible_versions)
            event = self._audit(db, workspace, actor, "export-project-audit", project=project,
                                outcome="released", request_id=request_id)
            released = {}
            for item in items:
                released.setdefault((item["decision_id"], item["version"]), {}).update(item["source_status"])
            for (decision, version), status in released.items():
                self._audit_item(db, workspace, event, project, decision, version, status)
        return {"items": items}

    def audit(self, workspace, human):
        with self._tenant(workspace, lock=True) as db:
            actor = self._human(db, workspace, human, admin=True)
            # Workspace membership administration is distinct from decision
            # evidence, whose access can change after an event was recorded.
            items = db.execute("""
                SELECT id,actor_user_id,request_id,action,outcome,reason,recorded_at
                FROM team_audit_events WHERE workspace_id=%s AND project_id IS NULL
                  AND action IN ('enable','invite','accept-invite','workspace-role',
                                 'offboard','create-group','group-member','audit')
                ORDER BY recorded_at DESC,id DESC LIMIT 100
            """, (workspace,)).fetchall()
            self._audit(db, workspace, actor, "audit")
        return {"items": items}
