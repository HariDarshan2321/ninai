from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, ContextManager, Mapping

from .policy import WriteDisposition, classify_write, validate_memory_type


class AuthorizationError(PermissionError):
    """The principal is not active or lacks the required scope capability."""


class IdempotencyConflict(ValueError):
    """An idempotency key was reused for a different request."""


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    workspace_id: str
    client_connection_id: str


@dataclass(frozen=True, slots=True)
class HostedMemory:
    id: str
    workspace_id: str
    project_id: str | None
    memory_type: str
    scope_kind: str
    scope_id: str
    content: str
    status: str
    source_uri: str
    importance: float
    confidence: float
    created_at: datetime
    updated_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    last_verified_at: datetime | None = None
    freshness_policy: str = "type_default"
    supersedes_memory_id: str | None = None
    conflict_group_id: str | None = None

    @property
    def is_expired(self) -> bool:
        return self.valid_until is not None and self.valid_until <= datetime.now(timezone.utc)


def _normalize(content: str) -> str:
    return " ".join(content.split()).strip()


def _request_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _looks_conflicting(left: str, right: str) -> bool:
    """Conservatively identify competing claims without pretending semantic certainty."""
    left_tokens = set(re.findall(r"[\w-]+", left.lower()))
    right_tokens = set(re.findall(r"[\w-]+", right.lower()))
    if left_tokens == right_tokens or min(len(left_tokens), len(right_tokens)) < 3:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.6


_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:sk|pk)-(?:live|test)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.I),
)


def _contains_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


class PostgresStore:
    """Tenant-scoped hosted store.

    Every externally reachable operation starts by checking that the principal's
    user and client are active in the workspace. Scope IDs are then derived from
    grants; callers cannot expand access by supplying another workspace ID.
    """

    def __init__(self, database_url: str, *, connect: Callable[[], ContextManager[Any]] | None = None) -> None:
        self.database_url = database_url
        self._connect_override = connect

    def _connection(self) -> ContextManager[Any]:
        if self._connect_override:
            return self._connect_override()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install ninai-cloud to use PostgresStore") from exc
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _validate_principal(db: Any, principal: Principal) -> None:
        row = db.execute(
            """
            SELECT 1 FROM client_connections c
            JOIN workspace_members m ON m.workspace_id=c.workspace_id AND m.user_id=%s
            JOIN workspaces w ON w.id=c.workspace_id
            JOIN users u ON u.id=m.user_id
            WHERE c.id=%s AND c.workspace_id=%s AND c.user_id=%s
              AND c.status='active' AND c.revoked_at IS NULL
              AND m.revoked_at IS NULL AND w.deleted_at IS NULL AND u.deleted_at IS NULL
            """,
            (principal.user_id, principal.client_connection_id, principal.workspace_id, principal.user_id),
        ).fetchone()
        if not row:
            raise AuthorizationError("Client, membership, or workspace is not active")

    @staticmethod
    def _grant(db: Any, principal: Principal, scope_kind: str, scope_id: str, capability: str,
               memory_type: str | None = None) -> None:
        if capability not in {"can_read", "can_propose", "can_auto_activate"}:
            raise ValueError("Unknown capability")
        row = db.execute(
            f"""
            SELECT 1 FROM client_scope_grants
            WHERE workspace_id=%s AND client_connection_id=%s
              AND scope_kind=%s AND scope_id=%s AND {capability}=true
              AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
              AND (%s::text IS NULL OR memory_types IS NULL OR %s = ANY(memory_types))
            """,
            (principal.workspace_id, principal.client_connection_id, scope_kind, scope_id,
             memory_type, memory_type),
        ).fetchone()
        if not row:
            raise AuthorizationError(f"Client lacks {capability} for requested scope")

    @staticmethod
    def _validate_scope_target(
        db: Any, principal: Principal, scope_kind: str, scope_id: str,
        project_id: str | None,
    ) -> str | None:
        """Resolve a write target inside the authenticated workspace.

        Grants are the capability boundary, but this separate check protects
        tenant integrity if a grant was inserted manually or by a future admin
        path. Polymorphic ``scope_id`` cannot be expressed as one PostgreSQL
        foreign key, so its workspace relationship is checked transactionally.
        """
        try:
            normalized_scope_id = str(uuid.UUID(scope_id))
            normalized_project_id = str(uuid.UUID(project_id)) if project_id else None
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("scope_id and project_id must be UUIDs") from exc

        if scope_kind == "workspace":
            if normalized_scope_id != principal.workspace_id or normalized_project_id is not None:
                raise AuthorizationError("Workspace scope must target the authenticated workspace")
            return None
        if scope_kind == "user":
            member = db.execute(
                """SELECT 1 FROM workspace_members WHERE workspace_id=%s AND user_id=%s
                   AND revoked_at IS NULL""",
                (principal.workspace_id, normalized_scope_id),
            ).fetchone()
            if not member or normalized_project_id is not None:
                raise AuthorizationError("User scope must target an active member of the workspace")
            return None

        # Project-scoped memories always carry the same project in both fields;
        # callers may omit project_id because scope_id already identifies it.
        if normalized_project_id is not None and normalized_project_id != normalized_scope_id:
            raise AuthorizationError("project_id must match the project scope_id")
        project = db.execute(
            """SELECT 1 FROM projects WHERE workspace_id=%s AND id=%s
               AND archived_at IS NULL""",
            (principal.workspace_id, normalized_scope_id),
        ).fetchone()
        if not project:
            raise AuthorizationError("Project scope is unavailable in the authenticated workspace")
        return normalized_scope_id

    def create_memory(
        self,
        principal: Principal,
        *,
        content: str,
        memory_type: str,
        scope_kind: str,
        scope_id: str,
        source_uri: str,
        idempotency_key: str,
        project_id: str | None = None,
        importance: float = 0.6,
        confidence: float = 1.0,
        activate: bool = False,
        source_type: str = "client",
        request_id: str | None = None,
        valid_until: datetime | None = None,
        freshness_policy: str = "type_default",
    ) -> HostedMemory:
        clean = _normalize(content)
        if not clean or len(clean) > 4000:
            raise ValueError("Memory content must be between 1 and 4,000 characters")
        if not source_uri.strip() or len(source_uri) > 1000:
            raise ValueError("source_uri is required and must be at most 1,000 characters")
        secret_detected = _contains_secret(clean) or _contains_secret(source_uri)
        if secret_detected:
            raise ValueError("Potential credential detected; Ninai refused to store it")
        validate_memory_type(memory_type)
        if scope_kind not in {"workspace", "project", "user"}:
            raise ValueError("Unsupported scope_kind")
        if not idempotency_key.strip() or len(idempotency_key) > 200:
            raise ValueError("A compact idempotency_key is required")
        if valid_until is not None and valid_until <= datetime.now(timezone.utc):
            raise ValueError("valid_until must be in the future")
        if not freshness_policy.strip() or len(freshness_policy) > 100:
            raise ValueError("freshness_policy is required and must be at most 100 characters")

        with self._connection() as db:
            self._validate_principal(db, principal)
            project_id = self._validate_scope_target(
                db, principal, scope_kind, scope_id, project_id
            )
            payload = {
                "content": clean, "memory_type": memory_type, "scope_kind": scope_kind,
                "scope_id": scope_id, "source_uri": source_uri, "project_id": project_id,
                "activate": activate, "valid_until": valid_until,
                "freshness_policy": freshness_policy,
            }
            digest = _request_hash(payload)
            policy = classify_write(
                content=clean, memory_type=memory_type, scope_kind=scope_kind, scope_id=scope_id,
                source_uri=source_uri, requested_auto=activate, contains_secret=secret_detected,
            )
            applied_activate = policy.disposition is WriteDisposition.ACTIVE
            capability = "can_auto_activate" if applied_activate else "can_propose"
            self._grant(db, principal, scope_kind, scope_id, capability, memory_type)
            existing = db.execute(
                """SELECT i.request_hash,m.*,s.source_uri FROM idempotency_keys i
                   JOIN memories m ON m.workspace_id=i.workspace_id AND m.id=i.memory_id
                   JOIN LATERAL (SELECT source_uri FROM memory_sources s WHERE s.workspace_id=m.workspace_id
                     AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
                   WHERE i.workspace_id=%s AND i.client_connection_id=%s AND i.idempotency_key=%s""",
                (principal.workspace_id, principal.client_connection_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing["request_hash"] != digest:
                    raise IdempotencyConflict("Idempotency key already represents another request")
                return self._memory(existing)

            # Exact duplicates are one durable claim with multiple immutable sources,
            # not multiple memories. This preserves provenance across clients/retries.
            duplicate = db.execute(
                """SELECT m.*,s.source_uri FROM memories m
                   JOIN LATERAL (SELECT source_uri FROM memory_sources s WHERE s.workspace_id=m.workspace_id
                     AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
                   WHERE m.workspace_id=%s AND m.scope_kind=%s AND m.scope_id=%s
                     AND m.memory_type=%s AND m.normalized_content=%s
                     AND m.status IN ('proposed','active','conflicted') AND m.deleted_at IS NULL
                   ORDER BY m.created_at LIMIT 1""",
                (principal.workspace_id, scope_kind, scope_id, memory_type, clean.lower()),
            ).fetchone()
            if duplicate:
                source_id = str(uuid.uuid4())
                db.execute(
                    """INSERT INTO memory_sources(id,workspace_id,memory_id,source_type,source_uri,
                         client_connection_id,request_id,content_hash)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (source_id, principal.workspace_id, duplicate["id"], source_type, source_uri.strip(),
                     principal.client_connection_id, request_id, hashlib.sha256(clean.encode()).hexdigest()),
                )
                db.execute(
                    "INSERT INTO idempotency_keys(workspace_id,client_connection_id,idempotency_key,request_hash,memory_id) VALUES(%s,%s,%s,%s,%s)",
                    (principal.workspace_id, principal.client_connection_id, idempotency_key, digest, duplicate["id"]),
                )
                return self._memory(duplicate)

            memory_id, source_id = str(uuid.uuid4()), str(uuid.uuid4())
            status = "active" if applied_activate else "proposed"
            conflict_group_id: str | None = None
            candidates = db.execute(
                """SELECT id,normalized_content FROM memories WHERE workspace_id=%s
                   AND scope_kind=%s AND scope_id=%s AND memory_type=%s AND status='active'
                   AND deleted_at IS NULL AND (valid_until IS NULL OR valid_until > now())""",
                (principal.workspace_id, scope_kind, scope_id, memory_type),
            ).fetchall()
            conflicts = [candidate for candidate in candidates
                         if _looks_conflicting(clean, candidate["normalized_content"])]
            if conflicts:
                conflict_group_id = str(uuid.uuid4())
                status = "conflicted"
                applied_activate = False
                policy = classify_write(
                    content=clean, memory_type=memory_type, scope_kind=scope_kind, scope_id=scope_id,
                    source_uri=source_uri, requested_auto=activate, has_active_conflict=True,
                )
                self._grant(db, principal, scope_kind, scope_id, "can_propose", memory_type)
                db.execute(
                    """UPDATE memories SET status='conflicted',conflict_group_id=%s,updated_at=now()
                       WHERE workspace_id=%s AND id = ANY(%s::uuid[])""",
                    (conflict_group_id, principal.workspace_id, [candidate["id"] for candidate in conflicts]),
                )
            requested = "auto_activate" if activate else "propose"
            applied = "auto_activate" if applied_activate else "propose"
            row = db.execute(
                """INSERT INTO memories(id,workspace_id,project_id,owner_user_id,memory_type,
                     scope_kind,scope_id,content,normalized_content,status,confidence,importance,
                     risk_level,write_mode_requested,write_mode_applied,created_by_user_id,created_by_client_connection_id,
                     valid_until,freshness_policy,conflict_group_id)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (memory_id, principal.workspace_id, project_id, principal.user_id, memory_type,
                 scope_kind, scope_id, clean, clean.lower(), status, max(0,min(1,float(confidence))),
                 max(0,min(1,float(importance))), policy.risk_level, requested, applied, principal.user_id,
                 principal.client_connection_id, valid_until, freshness_policy.strip(), conflict_group_id),
            ).fetchone()
            db.execute(
                """INSERT INTO memory_sources(id,workspace_id,memory_id,source_type,source_uri,
                     client_connection_id,request_id,content_hash)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (source_id, principal.workspace_id, memory_id, source_type, source_uri.strip(),
                 principal.client_connection_id, request_id, hashlib.sha256(clean.encode()).hexdigest()),
            )
            db.execute(
                "INSERT INTO idempotency_keys(workspace_id,client_connection_id,idempotency_key,request_hash,memory_id) VALUES(%s,%s,%s,%s,%s)",
                (principal.workspace_id, principal.client_connection_id, idempotency_key, digest, memory_id),
            )
            result = dict(row)
            result["source_uri"] = source_uri.strip()
            return self._memory(result)

    def get_memory(self, principal: Principal, memory_id: str) -> HostedMemory | None:
        with self._connection() as db:
            self._validate_principal(db, principal)
            row = db.execute(
                """SELECT m.*,s.source_uri FROM memories m
                   JOIN client_scope_grants g ON g.workspace_id=m.workspace_id
                     AND g.client_connection_id=%s AND g.scope_kind=m.scope_kind AND g.scope_id=m.scope_id
                     AND g.can_read=true AND g.revoked_at IS NULL
                     AND (g.expires_at IS NULL OR g.expires_at > now())
                   JOIN LATERAL (SELECT source_uri FROM memory_sources s WHERE s.workspace_id=m.workspace_id
                     AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
                   WHERE m.workspace_id=%s AND m.id=%s AND m.status='active' AND m.deleted_at IS NULL
                     AND (m.valid_until IS NULL OR m.valid_until > now())""",
                (principal.client_connection_id, principal.workspace_id, memory_id),
            ).fetchone()
            return self._memory(row) if row else None

    def search(self, principal: Principal, query: str, *, limit: int = 20) -> list[HostedMemory]:
        limit = max(1, min(100, int(limit)))
        lexemes = re.findall(r"[\w-]+", query.lower())[:20]
        # Candidate retrieval uses OR semantics so natural questions are not
        # forced to contain every filler word. Permission filtering still
        # happens in the same SQL query before ranking.
        terms = " | ".join(lexemes)
        with self._connection() as db:
            self._validate_principal(db, principal)
            rows = db.execute(
                """SELECT m.*,s.source_uri FROM memories m
                   JOIN client_scope_grants g ON g.workspace_id=m.workspace_id
                     AND g.client_connection_id=%s AND g.scope_kind=m.scope_kind AND g.scope_id=m.scope_id
                     AND g.can_read=true AND g.revoked_at IS NULL
                     AND (g.expires_at IS NULL OR g.expires_at > now())
                   JOIN LATERAL (SELECT source_uri FROM memory_sources s WHERE s.workspace_id=m.workspace_id
                     AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
                   WHERE m.workspace_id=%s AND m.status='active' AND m.deleted_at IS NULL
                     AND (m.valid_until IS NULL OR m.valid_until > now())
                     AND (%s='' OR to_tsvector('simple',m.normalized_content) @@ to_tsquery('simple',%s))
                   ORDER BY CASE WHEN %s='' THEN 0 ELSE ts_rank(to_tsvector('simple',m.normalized_content),to_tsquery('simple',%s)) END DESC,
                     m.importance DESC,m.updated_at DESC LIMIT %s""",
                (principal.client_connection_id, principal.workspace_id, terms, terms, terms, terms, limit),
            ).fetchall()
            return [self._memory(row) for row in rows]

    def transition(self, principal: Principal, memory_id: str, status: str) -> HostedMemory | None:
        if status not in {"proposed", "active", "conflicted", "rejected", "deleted"}:
            raise ValueError("Unsupported lifecycle status")
        with self._connection() as db:
            self._validate_principal(db, principal)
            row = db.execute(
                """UPDATE memories m SET status=%s,deleted_at=CASE WHEN %s='deleted' THEN now() ELSE NULL END,
                     updated_at=now() FROM memory_sources s
                   WHERE m.workspace_id=%s AND m.id=%s AND m.owner_user_id=%s
                     AND s.workspace_id=m.workspace_id AND s.memory_id=m.id
                   RETURNING m.*,s.source_uri""",
                (status, status, principal.workspace_id, memory_id, principal.user_id),
            ).fetchone()
            return self._memory(row) if row else None

    def supersede(self, principal: Principal, old_memory_id: str, new_memory_id: str) -> bool:
        with self._connection() as db:
            self._validate_principal(db, principal)
            new = db.execute(
                "SELECT 1 FROM memories WHERE workspace_id=%s AND id=%s AND status='active' AND deleted_at IS NULL",
                (principal.workspace_id, new_memory_id),
            ).fetchone()
            if not new:
                return False
            changed = db.execute(
                """UPDATE memories SET status='superseded',updated_at=now()
                   WHERE workspace_id=%s AND id=%s AND status IN ('active','conflicted','proposed')
                     AND deleted_at IS NULL""",
                (principal.workspace_id, old_memory_id),
            )
            if changed.rowcount == 1:
                db.execute(
                    "UPDATE memories SET supersedes_memory_id=%s,updated_at=now() WHERE workspace_id=%s AND id=%s",
                    (old_memory_id, principal.workspace_id, new_memory_id),
                )
            return changed.rowcount == 1

    def record_disclosure(self, principal: Principal, *, tool_name: str, query: str,
                          purpose: str, returned_memory_ids: list[str], denied_memory_count: int = 0,
                          estimated_tokens: int = 0, decision: str = "allow", denial_reason: str | None = None,
                          request_id: str | None = None) -> str:
        log_id = str(uuid.uuid4())
        with self._connection() as db:
            self._validate_principal(db, principal)
            scopes = db.execute(
                """SELECT scope_kind,scope_id FROM client_scope_grants WHERE workspace_id=%s
                   AND client_connection_id=%s AND can_read=true AND revoked_at IS NULL
                   AND (expires_at IS NULL OR expires_at > now()) ORDER BY scope_kind,scope_id""",
                (principal.workspace_id, principal.client_connection_id),
            ).fetchall()
            snapshot = [{"kind": row["scope_kind"], "id": str(row["scope_id"])} for row in scopes]
            db.execute(
                """INSERT INTO disclosure_logs(id,workspace_id,user_id,client_connection_id,tool_name,
                   query_hash,purpose,allowed_scope_snapshot,returned_memory_ids,denied_memory_count,
                   estimated_tokens,decision,denial_reason,request_id)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)""",
                (log_id, principal.workspace_id, principal.user_id, principal.client_connection_id,
                 tool_name, hashlib.sha256(query.encode()).hexdigest(), purpose, json.dumps(snapshot),
                 json.dumps(returned_memory_ids), denied_memory_count, estimated_tokens, decision,
                 denial_reason, request_id),
            )
        return log_id

    def revoke_client(self, workspace_id: str, client_connection_id: str, acting_user_id: str) -> bool:
        with self._connection() as db:
            role = db.execute(
                """SELECT role FROM workspace_members WHERE workspace_id=%s AND user_id=%s
                   AND revoked_at IS NULL AND role IN ('owner','admin')""",
                (workspace_id, acting_user_id),
            ).fetchone()
            if not role:
                raise AuthorizationError("Owner or admin role required")
            changed = db.execute(
                """UPDATE client_connections SET status='revoked',revoked_at=now()
                   WHERE workspace_id=%s AND id=%s AND revoked_at IS NULL""",
                (workspace_id, client_connection_id),
            )
            db.execute(
                """UPDATE client_scope_grants SET revoked_at=now() WHERE workspace_id=%s
                   AND client_connection_id=%s AND revoked_at IS NULL""",
                (workspace_id, client_connection_id),
            )
            return changed.rowcount == 1

    @staticmethod
    def _memory(row: Mapping[str, Any]) -> HostedMemory:
        return HostedMemory(
            id=str(row["id"]), workspace_id=str(row["workspace_id"]),
            project_id=str(row["project_id"]) if row.get("project_id") else None,
            memory_type=str(row["memory_type"]), scope_kind=str(row["scope_kind"]),
            scope_id=str(row["scope_id"]), content=str(row["content"]), status=str(row["status"]),
            source_uri=str(row["source_uri"]), importance=float(row["importance"]),
            confidence=float(row["confidence"]), created_at=row["created_at"], updated_at=row["updated_at"],
            valid_from=row.get("valid_from"), valid_until=row.get("valid_until"),
            last_verified_at=row.get("last_verified_at"),
            freshness_policy=str(row.get("freshness_policy") or "type_default"),
            supersedes_memory_id=str(row["supersedes_memory_id"]) if row.get("supersedes_memory_id") else None,
            conflict_group_id=str(row["conflict_group_id"]) if row.get("conflict_group_id") else None,
        )
