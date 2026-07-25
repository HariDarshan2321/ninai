"""Small, framework-free hosted control API and WSGI application.

Authentication is deliberately injected: production should pass ``identity_resolver``
from the OAuth layer.  User/workspace identity is never accepted from request JSON.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, ContextManager, Mapping
from urllib.parse import parse_qs

from .postgres_store import AuthorizationError
from .control_ui import CONTROL_CENTER_HTML


@dataclass(frozen=True, slots=True)
class ControlIdentity:
    user_id: str
    workspace_id: str


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


class ControlService:
    def __init__(self, connect: Callable[[], ContextManager[Any]]) -> None:
        self._connect = connect

    @staticmethod
    def _member(db: Any, identity: ControlIdentity, *, admin: bool = False) -> Mapping[str, Any]:
        roles = "AND m.role IN ('owner','admin')" if admin else ""
        row = db.execute(
            f"""SELECT w.id,w.name,w.slug,m.role FROM workspaces w JOIN workspace_members m
                ON m.workspace_id=w.id WHERE w.id=%s AND m.user_id=%s AND m.revoked_at IS NULL
                AND w.deleted_at IS NULL {roles}""", (identity.workspace_id, identity.user_id)
        ).fetchone()
        if not row:
            raise AuthorizationError("Active workspace membership required" if not admin else "Owner or admin role required")
        return row

    def overview(self, identity: ControlIdentity) -> dict[str, Any]:
        with self._connect() as db:
            workspace = self._member(db, identity)
            counts = db.execute("""SELECT
              count(*) FILTER (WHERE status='active' AND deleted_at IS NULL) active_memories,
              count(*) FILTER (WHERE status='proposed' AND deleted_at IS NULL) proposals
              FROM memories WHERE workspace_id=%s""", (identity.workspace_id,)).fetchone()
            connections = db.execute("SELECT count(*) n FROM client_connections WHERE workspace_id=%s AND status='active' AND revoked_at IS NULL", (identity.workspace_id,)).fetchone()
            disclosures = db.execute("SELECT count(*) n FROM disclosure_logs WHERE workspace_id=%s", (identity.workspace_id,)).fetchone()
            return {"workspace": dict(workspace), "counts": {**dict(counts), "active_connections": connections["n"], "disclosures": disclosures["n"]}}

    def memories(self, identity: ControlIdentity, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if status and status not in {"proposed", "active", "superseded", "deleted"}:
            raise ValueError("Unsupported memory status")
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT m.id,m.content,m.memory_type,m.scope_kind,m.scope_id,m.status,
              m.importance,m.confidence,m.created_at,m.updated_at,s.source_uri
              FROM memories m LEFT JOIN LATERAL (SELECT source_uri FROM memory_sources s
              WHERE s.workspace_id=m.workspace_id AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
              WHERE m.workspace_id=%s AND (%s IS NULL OR m.status=%s) ORDER BY m.updated_at DESC LIMIT %s""",
              (identity.workspace_id, status, status, max(1, min(int(limit), 200)))).fetchall()
            return [dict(row) for row in rows]

    def review(self, identity: ControlIdentity, memory_id: str, *, approve: bool) -> dict[str, Any] | None:
        with self._connect() as db:
            self._member(db, identity, admin=True)
            status = "active" if approve else "deleted"
            row = db.execute("""UPDATE memories SET status=%s,updated_at=now(),
              deleted_at=CASE WHEN %s='deleted' THEN now() ELSE NULL END
              WHERE workspace_id=%s AND id=%s AND status='proposed' RETURNING id,status,updated_at""",
              (status, status, identity.workspace_id, memory_id)).fetchone()
            return dict(row) if row else None

    def connections(self, identity: ControlIdentity) -> list[dict[str, Any]]:
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT id,provider,client_type,display_name,status,created_at,last_seen_at,revoked_at
              FROM client_connections WHERE workspace_id=%s ORDER BY created_at DESC""", (identity.workspace_id,)).fetchall()
            return [dict(row) for row in rows]

    def grants(self, identity: ControlIdentity, connection_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT g.id,g.client_connection_id,g.scope_kind,g.scope_id,g.can_read,
              g.can_propose,g.can_auto_activate,g.memory_types,g.expires_at,g.created_at,g.revoked_at
              FROM client_scope_grants g JOIN client_connections c
                ON c.workspace_id=g.workspace_id AND c.id=g.client_connection_id
              WHERE g.workspace_id=%s AND g.client_connection_id=%s ORDER BY g.created_at DESC""",
              (identity.workspace_id, connection_id)).fetchall()
            return [dict(row) for row in rows]

    def create_grant(self, identity: ControlIdentity, connection_id: str, data: Mapping[str, Any]) -> dict[str, Any]:
        kind, scope_id = data.get("scope_kind"), data.get("scope_id")
        if kind not in {"workspace", "project", "user"} or not scope_id:
            raise ValueError("scope_kind and scope_id are required")
        with self._connect() as db:
            self._member(db, identity, admin=True)
            row = db.execute("""INSERT INTO client_scope_grants(id,workspace_id,client_connection_id,scope_kind,scope_id,
              can_read,can_propose,can_auto_activate,memory_types,expires_at,created_by_user_id)
              SELECT %s,%s,c.id,%s,%s,%s,%s,%s,%s,%s,%s FROM client_connections c
              WHERE c.workspace_id=%s AND c.id=%s AND c.revoked_at IS NULL
              RETURNING id,client_connection_id,scope_kind,scope_id,can_read,can_propose,can_auto_activate,expires_at""",
              (str(uuid.uuid4()), identity.workspace_id, kind, scope_id, bool(data.get("can_read")),
               bool(data.get("can_propose")), bool(data.get("can_auto_activate")), data.get("memory_types"),
               data.get("expires_at"), identity.user_id, identity.workspace_id, connection_id)).fetchone()
            if not row:
                raise KeyError("Connection not found")
            return dict(row)

    def revoke_connection(self, identity: ControlIdentity, connection_id: str) -> bool:
        with self._connect() as db:
            self._member(db, identity, admin=True)
            changed = db.execute("UPDATE client_connections SET status='revoked',revoked_at=now() WHERE workspace_id=%s AND id=%s AND revoked_at IS NULL", (identity.workspace_id, connection_id))
            db.execute("UPDATE client_scope_grants SET revoked_at=now() WHERE workspace_id=%s AND client_connection_id=%s AND revoked_at IS NULL", (identity.workspace_id, connection_id))
            return changed.rowcount == 1

    def revoke_grant(self, identity: ControlIdentity, grant_id: str) -> bool:
        with self._connect() as db:
            self._member(db, identity, admin=True)
            changed = db.execute("UPDATE client_scope_grants SET revoked_at=now() WHERE workspace_id=%s AND id=%s AND revoked_at IS NULL", (identity.workspace_id, grant_id))
            return changed.rowcount == 1

    def activity(self, identity: ControlIdentity, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT id,client_connection_id,tool_name,purpose,returned_memory_ids,
              denied_memory_count,estimated_tokens,decision,denial_reason,request_id,created_at
              FROM disclosure_logs WHERE workspace_id=%s ORDER BY created_at DESC LIMIT %s""",
              (identity.workspace_id, max(1, min(int(limit), 200)))).fetchall()
            return [dict(row) for row in rows]

    def export(self, identity: ControlIdentity) -> dict[str, Any]:
        with self._connect() as db:
            workspace = self._member(db, identity, admin=True)
            exported: dict[str, Any] = {
                "format": "ninai-export-v1", "exported_at": datetime.now().astimezone(),
                "workspace": dict(workspace),
            }
            for key, table in (
                ("projects", "projects"), ("connections", "client_connections"),
                ("grants", "client_scope_grants"), ("memories", "memories"),
                ("sources", "memory_sources"), ("relations", "memory_relations"),
                ("feedback", "memory_feedback"), ("disclosures", "disclosure_logs"),
            ):
                rows = db.execute(f"SELECT * FROM {table} WHERE workspace_id=%s ORDER BY created_at", (identity.workspace_id,)).fetchall()
                exported[key] = [dict(row) for row in rows]
            return exported

    def delete_workspace(self, identity: ControlIdentity, confirmation: str) -> bool:
        with self._connect() as db:
            workspace = self._member(db, identity, admin=True)
            if workspace["role"] != "owner":
                raise AuthorizationError("Workspace owner role required")
            if confirmation != workspace["slug"]:
                raise ValueError("confirmation must exactly match the workspace slug")
            db.execute("UPDATE client_scope_grants SET revoked_at=COALESCE(revoked_at,now()) WHERE workspace_id=%s", (identity.workspace_id,))
            db.execute("UPDATE client_connections SET status='revoked',revoked_at=COALESCE(revoked_at,now()) WHERE workspace_id=%s", (identity.workspace_id,))
            db.execute("UPDATE memories SET status='deleted',deleted_at=COALESCE(deleted_at,now()),updated_at=now() WHERE workspace_id=%s", (identity.workspace_id,))
            changed = db.execute("UPDATE workspaces SET deleted_at=now() WHERE id=%s AND deleted_at IS NULL", (identity.workspace_id,))
            return changed.rowcount == 1


class ControlApp:
    def __init__(self, service: ControlService, identity_resolver: Callable[[Mapping[str, Any]], ControlIdentity]) -> None:
        self.service, self.identity_resolver = service, identity_resolver

    def __call__(self, environ: Mapping[str, Any], start_response: Callable[..., Any]):
        try:
            status, content_type, body = self._dispatch(environ)
        except AuthorizationError as exc:
            status, content_type, body = "403 Forbidden", "application/json", {"error": str(exc)}
        except (ValueError, json.JSONDecodeError) as exc:
            status, content_type, body = "400 Bad Request", "application/json", {"error": str(exc)}
        except KeyError as exc:
            status, content_type, body = "404 Not Found", "application/json", {"error": str(exc.args[0])}
        payload = body.encode() if isinstance(body, str) else json.dumps(body, default=_jsonable).encode()
        start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(payload))), ("Cache-Control", "no-store")])
        return [payload]

    def _dispatch(self, env: Mapping[str, Any]):
        path, method = env.get("PATH_INFO", "/"), env.get("REQUEST_METHOD", "GET").upper()
        if path in {"/", "/control"} and method == "GET":
            return "200 OK", "text/html; charset=utf-8", CONTROL_CENTER_HTML
        if not path.startswith("/api/control/"):
            raise KeyError("Route not found")
        identity = self.identity_resolver(env)
        query = parse_qs(env.get("QUERY_STRING", ""))
        length = int(env.get("CONTENT_LENGTH") or 0)
        data = json.loads(env["wsgi.input"].read(length) or b"{}") if length else {}
        suffix = path.removeprefix("/api/control")
        if method == "GET" and suffix == "/overview": result = self.service.overview(identity)
        elif method == "GET" and suffix == "/memories": result = {"items": self.service.memories(identity, query.get("status", [None])[0], query.get("limit", [100])[0])}
        elif method == "GET" and suffix == "/connections": result = {"items": self.service.connections(identity)}
        elif method == "GET" and (m := re.fullmatch(r"/connections/([^/]+)/grants", suffix)): result = {"items": self.service.grants(identity, m[1])}
        elif method == "GET" and suffix == "/activity": result = {"items": self.service.activity(identity, query.get("limit", [100])[0])}
        elif method == "GET" and suffix == "/export": result = self.service.export(identity)
        elif method == "POST" and (m := re.fullmatch(r"/memories/([^/]+)/(approve|reject)", suffix)): result = self.service.review(identity, m[1], approve=m[2] == "approve")
        elif method == "POST" and (m := re.fullmatch(r"/connections/([^/]+)/grants", suffix)): result = self.service.create_grant(identity, m[1], data)
        elif method == "POST" and (m := re.fullmatch(r"/connections/([^/]+)/revoke", suffix)): result = {"revoked": self.service.revoke_connection(identity, m[1])}
        elif method == "POST" and (m := re.fullmatch(r"/grants/([^/]+)/revoke", suffix)): result = {"revoked": self.service.revoke_grant(identity, m[1])}
        elif method == "POST" and suffix == "/delete-workspace": result = {"deleted": self.service.delete_workspace(identity, data.get("confirmation", ""))}
        else: raise KeyError("Route not found")
        if result is None:
            raise KeyError("Resource not found or no longer reviewable")
        return "200 OK", "application/json", result


def create_control_app(service: ControlService, identity_resolver: Callable[[Mapping[str, Any]], ControlIdentity]) -> ControlApp:
    return ControlApp(service, identity_resolver)
