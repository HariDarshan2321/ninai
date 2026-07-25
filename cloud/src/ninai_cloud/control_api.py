"""Hosted control service and authenticated ASGI transport.

The transport verifies the bearer credential on every API request and derives
user/workspace identity only from the resulting access token. Request headers
other than ``Authorization`` and request JSON can never select an identity.
"""
from __future__ import annotations

import json
import hashlib
import base64
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, ContextManager, Mapping
from urllib.parse import parse_qs, urlencode

from mcp.server.auth.provider import TokenVerifier
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from .postgres_store import AuthorizationError
from .auth import AuthSettings
from .control_ui import render_control_center


@dataclass(frozen=True, slots=True)
class ControlIdentity:
    user_id: str
    workspace_id: str | None
    email: str | None = None
    display_name: str | None = None


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


class ControlService:
    def __init__(self, connect: Callable[[], ContextManager[Any]], *, self_hosted: bool = False,
                 public_mcp_url: str = "/mcp", oauth_issuer: str | None = None) -> None:
        self._connect = connect
        self.self_hosted = self_hosted
        self.public_mcp_url = public_mcp_url
        self.oauth_issuer = oauth_issuer

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:40]
        return slug or "ninai"

    def create_workspace(self, identity: ControlIdentity, data: Mapping[str, Any]) -> dict[str, Any]:
        """Create the first tenant using only the verified token subject as owner."""
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        workspace_id = str(uuid.uuid4())
        slug = f"{self._slug(name)}-{workspace_id.split('-')[0]}"
        email = identity.email or f"{identity.user_id}@identity.invalid"
        display_name = identity.display_name or email.split("@", 1)[0]
        with self._connect() as db:
            db.execute("""INSERT INTO users(id,email,display_name) VALUES(%s,%s,%s)
              ON CONFLICT(id) DO UPDATE SET display_name=EXCLUDED.display_name""",
              (identity.user_id, email, display_name))
            row = db.execute("""INSERT INTO workspaces(id,name,slug,owner_user_id)
              VALUES(%s,%s,%s,%s) RETURNING id,name,slug,plan,default_write_mode,created_at""",
              (workspace_id, name, slug, identity.user_id)).fetchone()
            db.execute("INSERT INTO workspace_members(workspace_id,user_id,role) VALUES(%s,%s,'owner')",
                       (workspace_id, identity.user_id))
            return dict(row)

    def create_project(self, identity: ControlIdentity, data: Mapping[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        with self._connect() as db:
            self._member(db, identity, admin=True)
            row = db.execute("""INSERT INTO projects(id,workspace_id,name,slug,description)
              VALUES(%s,%s,%s,%s,%s) RETURNING id,name,slug,description,created_at""",
              (str(uuid.uuid4()), identity.workspace_id, name,
               f"{self._slug(name)}-{secrets.token_hex(3)}", str(data.get("description", "")).strip())).fetchone()
            return dict(row)

    def projects(self, identity: ControlIdentity) -> list[dict[str, Any]]:
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT id,name,slug,description,created_at,archived_at FROM projects
              WHERE workspace_id=%s ORDER BY created_at""", (identity.workspace_id,)).fetchall()
            return [dict(row) for row in rows]

    def create_connection(self, identity: ControlIdentity, data: Mapping[str, Any]) -> dict[str, Any]:
        provider = str(data.get("provider", "")).strip().lower()
        client_type = str(data.get("client_type", "")).strip().lower()
        display_name = str(data.get("display_name", "")).strip()
        oauth_client_id = str(data.get("oauth_client_id", "")).strip() or None
        if provider not in {"anthropic", "openai"} or not client_type or not display_name:
            raise ValueError("provider (anthropic or openai), client_type, and display_name are required")
        if not self.self_hosted and not oauth_client_id:
            raise ValueError("oauth_client_id is required for an OAuth connection")
        connection_id = str(uuid.uuid4())
        raw_token = "ninai_pat_" + secrets.token_urlsafe(32) if self.self_hosted else None
        expires_at = datetime.now(timezone.utc) + timedelta(days=90)
        with self._connect() as db:
            self._member(db, identity, admin=True)
            row = db.execute("""INSERT INTO client_connections
              (id,workspace_id,user_id,provider,client_type,display_name,metadata_json)
              VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id,provider,client_type,display_name,status,created_at""",
              (connection_id, identity.workspace_id, identity.user_id, provider, client_type,
               display_name, json.dumps({"setup_status": "created", "mcp_url": self.public_mcp_url}))).fetchone()
            if raw_token:
                db.execute("""INSERT INTO personal_access_tokens
                  (id,workspace_id,user_id,client_connection_id,token_hash,label,expires_at)
                  VALUES(%s,%s,%s,%s,%s,%s,%s)""", (str(uuid.uuid4()), identity.workspace_id,
                  identity.user_id, connection_id, hashlib.sha256(raw_token.encode()).hexdigest(),
                  display_name, expires_at))
            elif oauth_client_id:
                if not self.oauth_issuer:
                    raise ValueError("OAuth issuer is not configured")
                db.execute("""INSERT INTO oauth_client_bindings
                  (id,issuer,oauth_client_id,user_id,workspace_id,client_connection_id)
                  VALUES(%s,%s,%s,%s,%s,%s)""", (str(uuid.uuid4()),
                  self.oauth_issuer, oauth_client_id, identity.user_id,
                  identity.workspace_id, connection_id))
        result = dict(row)
        result["setup"] = {"mcp_url": self.public_mcp_url, "auth_mode": "pat" if raw_token else "oauth"}
        if raw_token:
            result["personal_access_token"] = raw_token
            result["token_expires_at"] = expires_at
        return result

    def test_connection(self, identity: ControlIdentity, connection_id: str) -> dict[str, Any]:
        checked_at = datetime.now(timezone.utc)
        with self._connect() as db:
            self._member(db, identity, admin=True)
            row = db.execute("""UPDATE client_connections SET metadata_json=metadata_json || %s::jsonb
              WHERE workspace_id=%s AND id=%s AND status='active' AND revoked_at IS NULL
              RETURNING id,provider,client_type,status,metadata_json""",
              (json.dumps({"connection_test": {"status": "ready", "checked_at": checked_at.isoformat(),
                           "mcp_url": self.public_mcp_url}}), identity.workspace_id, connection_id)).fetchone()
            if not row:
                raise KeyError("Connection not found")
            return dict(row)

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
        if status and status not in {"proposed", "active", "conflicted", "superseded", "rejected", "deleted"}:
            raise ValueError("Unsupported memory status")
        with self._connect() as db:
            self._member(db, identity)
            rows = db.execute("""SELECT m.id,m.content,m.memory_type,m.scope_kind,m.scope_id,m.status,
              m.importance,m.confidence,m.created_at,m.updated_at,s.source_uri
              FROM memories m LEFT JOIN LATERAL (SELECT source_uri FROM memory_sources s
              WHERE s.workspace_id=m.workspace_id AND s.memory_id=m.id ORDER BY s.created_at LIMIT 1) s ON true
              WHERE m.workspace_id=%s AND (%s::text IS NULL OR m.status=%s) ORDER BY m.updated_at DESC LIMIT %s""",
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
        can_read, can_propose = bool(data.get("can_read")), bool(data.get("can_propose"))
        can_auto_activate = bool(data.get("can_auto_activate"))
        if not any((can_read, can_propose, can_auto_activate)):
            raise ValueError("At least one permission is required")
        if can_auto_activate and not can_propose:
            raise ValueError("can_auto_activate requires can_propose")
        with self._connect() as db:
            self._member(db, identity, admin=True)
            row = db.execute("""INSERT INTO client_scope_grants(id,workspace_id,client_connection_id,scope_kind,scope_id,
              can_read,can_propose,can_auto_activate,memory_types,expires_at,created_by_user_id)
              SELECT %s,%s,c.id,%s,%s,%s,%s,%s,%s,%s,%s FROM client_connections c
              WHERE c.workspace_id=%s AND c.id=%s AND c.revoked_at IS NULL
                AND ((%s='workspace' AND %s=%s)
                  OR (%s='project' AND EXISTS (SELECT 1 FROM projects p WHERE p.workspace_id=%s AND p.id=%s AND p.archived_at IS NULL))
                  OR (%s='user' AND EXISTS (SELECT 1 FROM workspace_members m WHERE m.workspace_id=%s AND m.user_id=%s AND m.revoked_at IS NULL)))
              RETURNING id,client_connection_id,scope_kind,scope_id,can_read,can_propose,can_auto_activate,expires_at""",
              (str(uuid.uuid4()), identity.workspace_id, kind, scope_id, can_read,
               can_propose, can_auto_activate, data.get("memory_types"), data.get("expires_at"),
               identity.user_id, identity.workspace_id, connection_id, kind, scope_id,
               identity.workspace_id, kind, identity.workspace_id, scope_id, kind,
               identity.workspace_id, scope_id)).fetchone()
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
    """ASGI endpoint used both standalone and as FastMCP custom routes."""

    def __init__(self, service: ControlService, token_verifier: TokenVerifier,
                 oauth_settings: AuthSettings | None = None) -> None:
        self.service, self.token_verifier = service, token_verifier
        self.oauth_settings = oauth_settings

    @staticmethod
    def _security_headers() -> dict[str, str]:
        return {
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'"
            ),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }

    async def handle(self, request: Request) -> Response:
        oauth_response = await self._oauth_route(request)
        if oauth_response is not None:
            return oauth_response
        try:
            status, content_type, body = await self._dispatch(request)
        except AuthenticationError as exc:
            return JSONResponse(
                {"error": str(exc)}, status_code=401,
                headers={**self._security_headers(),
                         "WWW-Authenticate": 'Bearer realm="ninai-control"'},
            )
        except AuthorizationError as exc:
            status, content_type, body = 403, "application/json", {"error": str(exc)}
        except (ValueError, json.JSONDecodeError) as exc:
            status, content_type, body = 400, "application/json", {"error": str(exc)}
        except KeyError as exc:
            status, content_type, body = 404, "application/json", {"error": str(exc.args[0])}
        headers = self._security_headers()
        if isinstance(body, str):
            return HTMLResponse(body, status_code=status, headers=headers)
        return Response(json.dumps(body, default=_jsonable), status_code=status,
                        media_type=content_type, headers=headers)

    def _oauth_ready(self) -> bool:
        settings = self.oauth_settings
        return bool(settings and settings.control_client_id and settings.control_base_url
                    and settings.authorization_endpoint and settings.token_endpoint)

    def _control_callback_url(self) -> str:
        assert self.oauth_settings and self.oauth_settings.control_base_url
        return self.oauth_settings.control_base_url.rstrip("/") + "/control"

    async def _oauth_route(self, request: Request) -> Response | None:
        path = request.url.path
        if path == "/control/login" and request.method == "GET":
            if not self._oauth_ready():
                return JSONResponse({"error": "Dashboard OAuth is not configured"}, status_code=503,
                                    headers=self._security_headers())
            assert self.oauth_settings and self.oauth_settings.authorization_endpoint
            verifier = secrets.token_urlsafe(64)
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode()).digest()
            ).rstrip(b"=").decode()
            state = secrets.token_urlsafe(32)
            params = {
                "response_type": "code", "client_id": self.oauth_settings.control_client_id,
                "redirect_uri": self._control_callback_url(),
                "scope": "openid profile email",
                "audience": self.oauth_settings.audience, "resource": self.oauth_settings.resource,
                "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
            }
            if request.query_params.get("screen_hint") == "signup":
                params["screen_hint"] = "signup"
            response = RedirectResponse(
                self.oauth_settings.authorization_endpoint + "?" + urlencode(params), status_code=302,
                headers=self._security_headers(),
            )
            response.set_cookie("ninai_oauth_state", state, max_age=600, httponly=True,
                                secure=True, samesite="lax", path="/control")
            response.set_cookie("ninai_pkce_verifier", verifier, max_age=600, httponly=True,
                                secure=True, samesite="lax", path="/control")
            return response
        if path == "/control/logout" and request.method == "GET":
            response = RedirectResponse("/control", status_code=302, headers=self._security_headers())
            response.delete_cookie("ninai_access_token", path="/")
            return response
        if path == "/control" and request.method == "GET" and request.query_params.get("code"):
            return await self._oauth_callback(request)
        return None

    async def _oauth_callback(self, request: Request) -> Response:
        if not self._oauth_ready():
            return JSONResponse({"error": "Dashboard OAuth is not configured"}, status_code=503,
                                headers=self._security_headers())
        settings = self.oauth_settings
        assert settings and settings.token_endpoint and settings.control_client_id and settings.control_base_url
        state = request.query_params.get("state")
        if not state or not secrets.compare_digest(state, request.cookies.get("ninai_oauth_state", "")):
            return JSONResponse({"error": "OAuth state validation failed"}, status_code=400,
                                headers=self._security_headers())
        verifier = request.cookies.get("ninai_pkce_verifier", "")
        if not verifier:
            return JSONResponse({"error": "OAuth PKCE verifier is missing"}, status_code=400,
                                headers=self._security_headers())
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                token_response = await client.post(settings.token_endpoint, data={
                    "grant_type": "authorization_code", "client_id": settings.control_client_id,
                    "code": request.query_params["code"], "code_verifier": verifier,
                    "redirect_uri": self._control_callback_url(),
                })
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise ValueError("token response omitted access_token")
        except Exception:
            return JSONResponse({"error": "OAuth code exchange failed"}, status_code=502,
                                headers=self._security_headers())
        response = RedirectResponse("/control", status_code=302, headers=self._security_headers())
        response.set_cookie("ninai_access_token", access_token,
                            max_age=max(60, min(int(token_data.get("expires_in", 3600)), 86_400)),
                            httponly=True, secure=True, samesite="lax", path="/")
        response.delete_cookie("ninai_oauth_state", path="/control")
        response.delete_cookie("ninai_pkce_verifier", path="/control")
        return response

    async def _identity(self, request: Request) -> ControlIdentity:
        authorization = request.headers.get("authorization", "")
        using_cookie = not authorization and bool(request.cookies.get("ninai_access_token"))
        if using_cookie and request.method.upper() != "GET":
            expected = f"{request.url.scheme}://{request.url.netloc}"
            if request.headers.get("origin") != expected:
                raise AuthenticationError("OAuth browser request failed origin validation")
        scheme, separator, credential = (
            authorization or f"Bearer {request.cookies.get('ninai_access_token', '')}"
        ).partition(" ")
        if not separator or scheme.lower() != "bearer" or not credential.strip():
            raise AuthenticationError("A Bearer authorization header is required")
        token = await self.token_verifier.verify_token(credential.strip())
        if token is None:
            raise AuthenticationError("Bearer token validation failed")
        claims = token.claims or {}
        user_id = getattr(token, "user_id", None) or claims.get("user_id")
        workspace_id = getattr(token, "workspace_id", None) or claims.get("workspace_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise AuthenticationError("Verified token is missing Ninai user identity")
        if workspace_id is not None and (not isinstance(workspace_id, str) or not workspace_id.strip()):
            raise AuthenticationError("Verified token has an invalid Ninai workspace identity")
        return ControlIdentity(user_id=user_id, workspace_id=workspace_id,
                               email=claims.get("email") if isinstance(claims.get("email"), str) else None,
                               display_name=claims.get("name") if isinstance(claims.get("name"), str) else None)

    async def _dispatch(self, request: Request):
        path, method = request.url.path, request.method.upper()
        if path in {"/", "/control"} and method == "GET":
            return 200, "text/html; charset=utf-8", render_control_center(
                oauth_enabled=self._oauth_ready(),
                signed_in=bool(request.cookies.get("ninai_access_token")),
            )
        if not path.startswith("/api/control/"):
            raise KeyError("Route not found")
        identity = await self._identity(request)
        query = parse_qs(request.url.query)
        raw = await request.body()
        data = json.loads(raw or b"{}") if raw else {}
        suffix = path.removeprefix("/api/control")
        if method == "POST" and suffix == "/workspaces": result = self.service.create_workspace(identity, data)
        elif method == "GET" and suffix == "/overview": result = self.service.overview(identity)
        elif method == "GET" and suffix == "/projects": result = {"items": self.service.projects(identity)}
        elif method == "POST" and suffix == "/projects": result = self.service.create_project(identity, data)
        elif method == "GET" and suffix == "/memories": result = {"items": self.service.memories(identity, query.get("status", [None])[0], query.get("limit", [100])[0])}
        elif method == "GET" and suffix == "/connections": result = {"items": self.service.connections(identity)}
        elif method == "POST" and suffix == "/connections": result = self.service.create_connection(identity, data)
        elif method == "GET" and (m := re.fullmatch(r"/connections/([^/]+)/grants", suffix)): result = {"items": self.service.grants(identity, m[1])}
        elif method == "GET" and suffix == "/activity": result = {"items": self.service.activity(identity, query.get("limit", [100])[0])}
        elif method == "GET" and suffix == "/export": result = self.service.export(identity)
        elif method == "POST" and (m := re.fullmatch(r"/memories/([^/]+)/(approve|reject)", suffix)): result = self.service.review(identity, m[1], approve=m[2] == "approve")
        elif method == "POST" and (m := re.fullmatch(r"/connections/([^/]+)/grants", suffix)): result = self.service.create_grant(identity, m[1], data)
        elif method == "POST" and (m := re.fullmatch(r"/connections/([^/]+)/revoke", suffix)): result = {"revoked": self.service.revoke_connection(identity, m[1])}
        elif method == "POST" and (m := re.fullmatch(r"/connections/([^/]+)/test", suffix)): result = self.service.test_connection(identity, m[1])
        elif method == "POST" and (m := re.fullmatch(r"/grants/([^/]+)/revoke", suffix)): result = {"revoked": self.service.revoke_grant(identity, m[1])}
        elif method == "POST" and suffix == "/delete-workspace": result = {"deleted": self.service.delete_workspace(identity, data.get("confirmation", ""))}
        else: raise KeyError("Route not found")
        if result is None:
            raise KeyError("Resource not found or no longer reviewable")
        return 200, "application/json", result


class AuthenticationError(AuthorizationError):
    """The request did not carry a valid bearer credential."""


def create_control_app(service: ControlService, token_verifier: TokenVerifier,
                       oauth_settings: AuthSettings | None = None) -> ControlApp:
    return ControlApp(service, token_verifier, oauth_settings)
