"""Authenticated Streamable HTTP MCP transport for the opt-in hosted store."""
from __future__ import annotations

import os
import math
from dataclasses import asdict
from typing import Any, Protocol

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings as MCPAuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from .postgres_store import (AuthorizationError, HostedMemory, HostedSession,
                             IdempotencyConflict, PostgresStore, Principal)
from .policy import validate_memory_type
from .control_api import ControlService, create_control_app
from .auth import AuthSettings as HostedAuthSettings
from .rate_limit import (MAX_REQUEST_BODY_BYTES, RateLimitError, RequestBodyLimitMiddleware,
                         SlidingWindowRateLimiter)

MAX_QUERY_CHARS = 1_000
MAX_PURPOSE_CHARS = 500
MAX_SEARCH_ITEMS = 50
MAX_RECALL_ITEMS = 12
MAX_RECALL_TOKENS = 2_000
MAX_CONTENT_CHARS = 4_000
MAX_SOURCE_URI_CHARS = 1_000
MAX_IDEMPOTENCY_KEY_CHARS = 200
MAX_IDENTIFIER_CHARS = 100
DEFAULT_READ_CALLS_PER_MINUTE = 120
DEFAULT_WRITE_CALLS_PER_MINUTE = 30

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 64 64" role="img" aria-label="ninai app icon — the return"><rect width="64" height="64" rx="14.5" fill="#0B0B0C"/><g transform="translate(3.2,3.2) scale(0.9)" fill="#FFFFFF"><path d="M18.07 45.75 L17.28 44.97 L16.61 44.10 L16.02 43.16 L15.50 42.17 L15.05 41.14 L14.67 40.08 L14.37 38.99 L14.14 37.88 L13.99 36.75 L13.92 35.61 L13.92 34.46 L14.01 33.31 L14.17 32.17 L14.41 31.04 L14.73 29.93 L15.12 28.83 L15.58 27.77 L16.12 26.74 L16.72 25.74 L17.39 24.79 L18.13 23.89 L18.92 23.04 L19.77 22.24 L20.67 21.50 L21.62 20.83 L22.61 20.22 L23.64 19.68 L24.70 19.21 L25.79 18.82 L26.90 18.50 L28.03 18.26 L29.16 18.10 L30.31 18.02 L31.45 18.01 L32.59 18.08 L33.71 18.23 L34.82 18.45 L35.90 18.75 L36.96 19.12 L37.99 19.56 L38.97 20.06 L39.92 20.63 L40.81 21.26 L41.66 21.94 L42.45 22.68 L43.19 23.47 L43.86 24.29 L44.47 25.16 L45.01 26.06 L45.49 26.99 L45.90 27.94 L46.23 28.90 L46.50 29.88 L46.69 30.87 L46.81 31.86 L46.87 32.84 L46.85 33.81 L46.76 34.77 L46.61 35.71 L46.40 36.63 L46.12 37.52 L45.78 38.37 L45.39 39.18 L44.95 39.96 L44.46 40.69 L43.92 41.37 L43.35 42.00 L42.74 42.58 L42.09 43.10 L41.43 43.57 L40.74 43.97 L40.03 44.31 L39.31 44.60 L38.58 44.82 L37.86 44.98 L37.13 45.07 L36.41 45.10 L35.71 45.06 L35.01 44.94 L34.33 44.69 L34.33 44.69 L34.80 44.30 L35.26 43.97 L35.70 43.64 L36.13 43.29 L36.53 42.94 L36.90 42.57 L37.26 42.18 L37.59 41.78 L37.89 41.37 L38.17 40.95 L38.43 40.52 L38.66 40.08 L38.86 39.63 L39.04 39.17 L39.20 38.71 L39.32 38.24 L39.43 37.77 L39.50 37.29 L39.56 36.81 L39.58 36.33 L39.58 35.85 L39.56 35.37 L39.51 34.89 L39.44 34.42 L39.34 33.95 L39.21 33.48 L39.06 33.02 L38.89 32.57 L38.69 32.12 L38.47 31.68 L38.22 31.25 L37.94 30.83 L37.65 30.43 L37.33 30.03 L36.98 29.65 L36.61 29.29 L36.22 28.94 L35.81 28.61 L35.37 28.30 L34.91 28.01 L34.43 27.75 L33.92 27.50 L33.40 27.29 L32.86 27.10 L32.30 26.94 L31.72 26.80 L31.13 26.71 L30.52 26.64 L29.90 26.61 L29.26 26.61 L28.62 26.66 L27.97 26.74 L27.32 26.86 L26.66 27.03 L26.01 27.24 L25.35 27.49 L24.70 27.78 L24.06 28.13 L23.42 28.51 L22.81 28.94 L22.20 29.42 L21.62 29.95 L21.06 30.52 L20.53 31.13 L20.03 31.79 L19.56 32.49 L19.13 33.24 L18.74 34.02 L18.39 34.84 L18.09 35.70 L17.84 36.59 L17.64 37.51 L17.49 38.46 L17.40 39.44 L17.38 40.44 L17.41 41.46 L17.50 42.49 L17.65 43.55 L17.86 44.62 L18.07 45.75 Z"/><circle cx="32" cy="36" r="5.2"/></g></svg>"""


class PrincipalResolver(Protocol):
    def __call__(self) -> Principal: ...


def _principal_from_access_token() -> Principal:
    token = get_access_token()
    if token is None:
        raise AuthorizationError("A valid bearer token is required")
    claims = token.claims or {}
    try:
        return Principal(
            user_id=str(getattr(token, "user_id", None) or claims["user_id"]),
            workspace_id=str(getattr(token, "workspace_id", None) or claims["workspace_id"]),
            client_connection_id=str(getattr(token, "client_connection_id", None)
                                     or claims.get("client_connection_id") or token.client_id),
        )
    except KeyError as exc:
        raise AuthorizationError(f"Access token is missing required claim: {exc.args[0]}") from exc


def _memory_result(memory: HostedMemory) -> dict[str, Any]:
    result = asdict(memory)
    result["created_at"] = memory.created_at.isoformat()
    result["updated_at"] = memory.updated_at.isoformat()
    result["scope"] = {"kind": memory.scope_kind, "id": memory.scope_id}
    result["source"] = {"uri": memory.source_uri}
    return result


def _session_result(session: HostedSession) -> dict[str, Any]:
    result = asdict(session)
    for field in ("started_at", "ended_at", "last_checkpoint_at", "updated_at"):
        value = result[field]
        result[field] = value.isoformat() if value else None
    return result


def _estimate_tokens(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 3) // 4)


def _required_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    clean = " ".join(value.split()).strip()
    if not clean:
        raise ValueError(f"{field} is required")
    if len(clean) > maximum:
        raise ValueError(f"{field} must be at most {maximum:,} characters")
    return clean


class HostedMCPTools:
    """Transport-neutral MCP operations, suitable for direct contract testing."""

    def __init__(self, store: PostgresStore, principal: PrincipalResolver = _principal_from_access_token,
                 *, read_limiter: SlidingWindowRateLimiter | None = None,
                 write_limiter: SlidingWindowRateLimiter | None = None) -> None:
        self.store = store
        self.principal = principal
        self.read_limiter = read_limiter or SlidingWindowRateLimiter(DEFAULT_READ_CALLS_PER_MINUTE)
        self.write_limiter = write_limiter or SlidingWindowRateLimiter(DEFAULT_WRITE_CALLS_PER_MINUTE)

    def _authorized(self, *, write: bool = False) -> Principal:
        principal = self.principal()
        (self.write_limiter if write else self.read_limiter).check(principal)
        return principal

    def search(self, query: str, purpose: str, limit: int = 10) -> dict[str, Any]:
        query = _required_text(query, "query", MAX_QUERY_CHARS)
        purpose = _required_text(purpose, "purpose", MAX_PURPOSE_CHARS)
        limit = max(1, min(int(limit), MAX_SEARCH_ITEMS))
        principal = self._authorized()
        memories = self.store.search(principal, query, limit=limit)
        results = [_memory_result(memory) for memory in memories]
        self.store.record_disclosure(
            principal, tool_name="search", query=query, purpose=purpose,
            returned_memory_ids=[memory.id for memory in memories], estimated_tokens=_estimate_tokens(str(results)),
        )
        return {"ok": True, "query": query, "results": results, "count": len(results)}

    def fetch(self, memory_id: str, purpose: str) -> dict[str, Any]:
        memory_id = _required_text(memory_id, "memory_id", 100)
        purpose = _required_text(purpose, "purpose", MAX_PURPOSE_CHARS)
        principal = self._authorized()
        memory = self.store.get_memory(principal, memory_id)
        result = _memory_result(memory) if memory else None
        self.store.record_disclosure(
            principal, tool_name="fetch", query=memory_id, purpose=purpose,
            returned_memory_ids=[memory.id] if memory else [],
            estimated_tokens=_estimate_tokens(str(result)) if result else 0,
        )
        return {"ok": True, "memory": result, "found": memory is not None}

    def recall(self, query: str, purpose: str, max_items: int = 6, max_tokens: int = 600) -> dict[str, Any]:
        query = _required_text(query, "query", MAX_QUERY_CHARS)
        purpose = _required_text(purpose, "purpose", MAX_PURPOSE_CHARS)
        max_items = max(1, min(int(max_items), MAX_RECALL_ITEMS))
        max_tokens = max(100, min(int(max_tokens), MAX_RECALL_TOKENS))
        principal = self._authorized()
        candidates = self.store.search(principal, query, limit=max_items * 3)
        results: list[dict[str, Any]] = []
        estimated_tokens = 0
        for memory in candidates:
            result = _memory_result(memory)
            item_tokens = _estimate_tokens(str(result))
            if item_tokens > max_tokens - estimated_tokens:
                continue
            results.append(result)
            estimated_tokens += item_tokens
            if len(results) >= max_items:
                break
        self.store.record_disclosure(
            principal, tool_name="recall", query=query, purpose=purpose,
            returned_memory_ids=[result["id"] for result in results], estimated_tokens=estimated_tokens,
        )
        return {"ok": True, "query": query, "purpose": purpose, "facts": results,
                "count": len(results), "estimated_tokens": estimated_tokens, "max_tokens": max_tokens}

    def _write(self, *, activate: bool, content: str, memory_type: str, scope_kind: str,
               scope_id: str, source_uri: str, idempotency_key: str, project_id: str | None = None,
               importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        content = _required_text(content, "content", MAX_CONTENT_CHARS)
        memory_type = _required_text(memory_type, "memory_type", MAX_IDENTIFIER_CHARS)
        validate_memory_type(memory_type)
        scope_kind = _required_text(scope_kind, "scope_kind", MAX_IDENTIFIER_CHARS)
        scope_id = _required_text(scope_id, "scope_id", MAX_IDENTIFIER_CHARS)
        source_uri = _required_text(source_uri, "source_uri", MAX_SOURCE_URI_CHARS)
        idempotency_key = _required_text(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_CHARS)
        if project_id is not None:
            project_id = _required_text(project_id, "project_id", MAX_IDENTIFIER_CHARS)
        if not math.isfinite(importance) or not 0 <= importance <= 1:
            raise ValueError("importance must be between 0 and 1")
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        principal = self._authorized(write=True)
        memory = self.store.create_memory(
            principal, content=content, memory_type=memory_type, scope_kind=scope_kind,
            scope_id=scope_id, source_uri=source_uri, idempotency_key=idempotency_key,
            project_id=project_id, importance=importance, confidence=confidence, activate=activate,
        )
        return {"ok": True, "memory": _memory_result(memory), "stored": True}

    def propose_memory(self, content: str, memory_type: str, scope_kind: str, scope_id: str,
                       source_uri: str, idempotency_key: str, project_id: str | None = None,
                       importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return self._write(activate=False, content=content, memory_type=memory_type,
                           scope_kind=scope_kind, scope_id=scope_id, source_uri=source_uri,
                           idempotency_key=idempotency_key, project_id=project_id,
                           importance=importance, confidence=confidence)

    def remember(self, content: str, memory_type: str, scope_kind: str, scope_id: str,
                 source_uri: str, idempotency_key: str, project_id: str | None = None,
                 importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return self._write(activate=True, content=content, memory_type=memory_type,
                           scope_kind=scope_kind, scope_id=scope_id, source_uri=source_uri,
                           idempotency_key=idempotency_key, project_id=project_id,
                           importance=importance, confidence=confidence)

    def capture_session(
        self, *, status: str, provider: str, external_session_id: str, project_id: str,
        title: str, source_uri: str, cwd_or_repo: str = "", transcript: str | None = None,
    ) -> dict[str, Any]:
        provider = _required_text(provider, "provider", MAX_IDENTIFIER_CHARS)
        external_session_id = _required_text(external_session_id, "external_session_id", 300)
        project_id = _required_text(project_id, "project_id", MAX_IDENTIFIER_CHARS)
        title = _required_text(title, "title", 240)
        source_uri = _required_text(source_uri, "source_uri", MAX_SOURCE_URI_CHARS)
        if transcript is not None and (not isinstance(transcript, str) or len(transcript) > 1_000_000):
            raise ValueError("transcript must be text no larger than 1,000,000 characters")
        principal = self._authorized(write=True)
        session = self.store.capture_session(
            principal, provider=provider, external_session_id=external_session_id,
            project_id=project_id, title=title, source_uri=source_uri, status=status,
            cwd_or_repo=cwd_or_repo, transcript=transcript,
        )
        return {"ok": True, "session": _session_result(session)}

    def session_context(self, project_id: str, max_tokens: int = 600) -> dict[str, Any]:
        project_id = _required_text(project_id, "project_id", MAX_IDENTIFIER_CHARS)
        principal = self._authorized()
        return {"ok": True, **self.store.session_context(
            principal, project_id=project_id, max_tokens=max_tokens
        )}


def create_mcp(store: PostgresStore, *, token_verifier: TokenVerifier,
               control_token_verifier: TokenVerifier | None = None,
               principal_resolver: PrincipalResolver = _principal_from_access_token,
               auth: MCPAuthSettings,
               host: str = "127.0.0.1", port: int = 8000,
               read_calls_per_minute: int = DEFAULT_READ_CALLS_PER_MINUTE,
               write_calls_per_minute: int = DEFAULT_WRITE_CALLS_PER_MINUTE,
               max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES,
               control_service: ControlService | None = None,
               control_oauth_settings: HostedAuthSettings | None = None) -> FastMCP:
    """Build the authenticated, stateless hosted MCP application."""
    mcp = FastMCP(
        "Ninai Hosted",
        instructions=("Use approved, source-backed Ninai memory across AI clients. Search or recall with a "
                      "clear purpose. Use propose_memory for review-first writes. Use remember only when this "
                      "client was explicitly granted auto-activation. Never send credentials."),
        token_verifier=token_verifier, auth=auth, host=host, port=port, streamable_http_path="/mcp",
        stateless_http=True, json_response=True,
    )
    tools = HostedMCPTools(
        store, principal_resolver,
        read_limiter=SlidingWindowRateLimiter(read_calls_per_minute),
        write_limiter=SlidingWindowRateLimiter(write_calls_per_minute),
    )
    original_http_app = mcp.streamable_http_app

    def bounded_http_app() -> Any:
        app = original_http_app()
        app.add_middleware(RequestBodyLimitMiddleware, maximum=max_request_body_bytes)
        return app

    mcp.streamable_http_app = bounded_http_app  # type: ignore[method-assign]

    def guarded(operation: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return operation(*args, **kwargs)
        except AuthorizationError as exc:
            return {"ok": False, "error": {"code": "forbidden", "message": str(exc)}}
        except IdempotencyConflict as exc:
            return {"ok": False, "error": {"code": "idempotency_conflict", "message": str(exc)}}
        except RateLimitError as exc:
            return {"ok": False, "error": {"code": "rate_limited", "message": str(exc)}}
        except ValueError as exc:
            return {"ok": False, "error": {"code": "invalid_request", "message": str(exc)}}

    @mcp.tool(
        title="Search Ninai memory",
        description="Search active memories in this client's granted scopes. Results include provenance.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def search(query: str, purpose: str, limit: int = 10) -> dict[str, Any]:
        return guarded(tools.search, query, purpose, limit)

    @mcp.tool(
        title="Fetch Ninai memory",
        description="Fetch one active memory by ID if it is in this client's granted scopes.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def fetch(memory_id: str, purpose: str) -> dict[str, Any]:
        return guarded(tools.fetch, memory_id, purpose)

    @mcp.tool(
        title="Recall from Ninai",
        description="Return a compact, token-bounded context packet with provenance and disclosure audit.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def recall(query: str, purpose: str, max_items: int = 6, max_tokens: int = 600) -> dict[str, Any]:
        return guarded(tools.recall, query, purpose, max_items, max_tokens)

    @mcp.tool(
        title="Propose Ninai memory",
        description="Propose source-backed durable memory for review; proposed items are not recalled.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def propose_memory(content: str, memory_type: str, scope_kind: str, scope_id: str,
                       source_uri: str, idempotency_key: str, project_id: str | None = None,
                       importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return guarded(tools.propose_memory, content, memory_type, scope_kind, scope_id,
                       source_uri, idempotency_key, project_id, importance, confidence)

    @mcp.tool(
        title="Remember with Ninai",
        description="Activate durable memory only with explicit auto-activate permission.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def remember(content: str, memory_type: str, scope_kind: str, scope_id: str,
                 source_uri: str, idempotency_key: str, project_id: str | None = None,
                 importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return guarded(tools.remember, content, memory_type, scope_kind, scope_id,
                       source_uri, idempotency_key, project_id, importance, confidence)

    @mcp.tool(
        title="Start a Ninai session archive",
        description="Start an explicitly consented project session archive. Requires project propose permission.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def capture_session_start(provider: str, external_session_id: str, project_id: str,
                              title: str, source_uri: str, cwd_or_repo: str = "") -> dict[str, Any]:
        return guarded(tools.capture_session, status="started", provider=provider,
                       external_session_id=external_session_id, project_id=project_id,
                       title=title, source_uri=source_uri, cwd_or_repo=cwd_or_repo)

    @mcp.tool(
        title="Checkpoint a Ninai session archive",
        description="Idempotently checkpoint a connected-agent transcript after explicit archive consent.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def capture_session_checkpoint(provider: str, external_session_id: str, project_id: str,
                                   title: str, source_uri: str, transcript: str,
                                   cwd_or_repo: str = "") -> dict[str, Any]:
        return guarded(tools.capture_session, status="checkpointed", provider=provider,
                       external_session_id=external_session_id, project_id=project_id,
                       title=title, source_uri=source_uri, cwd_or_repo=cwd_or_repo,
                       transcript=transcript)

    @mcp.tool(
        title="Finalize a Ninai session archive",
        description="Finalize an idempotent connected-agent transcript archive.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def capture_session_end(provider: str, external_session_id: str, project_id: str,
                            title: str, source_uri: str, transcript: str,
                            cwd_or_repo: str = "") -> dict[str, Any]:
        return guarded(tools.capture_session, status="completed", provider=provider,
                       external_session_id=external_session_id, project_id=project_id,
                       title=title, source_uri=source_uri, cwd_or_repo=cwd_or_repo,
                       transcript=transcript)

    @mcp.tool(
        title="Load Ninai project handoff",
        description="Return a compact project-only session context packet after permission filtering.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
        structured_output=True,
    )
    def session_context(project_id: str, max_tokens: int = 600) -> dict[str, Any]:
        return guarded(tools.session_context, project_id, max_tokens)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "ninai-cloud-mcp"})

    @mcp.custom_route("/", methods=["GET"])
    async def root(_: Request) -> RedirectResponse:
        return RedirectResponse("/control", status_code=307)

    @mcp.custom_route("/favicon.svg", methods=["GET"])
    async def favicon(_: Request) -> Response:
        return Response(FAVICON_SVG, media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})

    connect = getattr(store, "_connection", None)
    if connect is None:  # Allows transport registration with contract-test stores.
        def connect():
            raise RuntimeError("The control center requires a PostgreSQL-backed store")
    control = create_control_app(control_service or ControlService(connect),
                                 control_token_verifier or token_verifier,
                                 control_oauth_settings)

    @mcp.custom_route("/control", methods=["GET"])
    async def control_page(request: Request):
        return await control.handle(request)

    @mcp.custom_route("/control/login", methods=["GET"])
    async def control_login(request: Request):
        return await control.handle(request)

    @mcp.custom_route("/control/logout", methods=["GET"])
    async def control_logout(request: Request):
        return await control.handle(request)

    @mcp.custom_route("/api/control/{path:path}", methods=["GET", "POST"])
    async def control_api(request: Request):
        return await control.handle(request)
    return mcp


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    from .auth import (AuthSettings, JWTValidator, MCPTokenVerifier, OAuthControlTokenVerifier, OAuthIdentityResolver, PATTokenVerifier,
                       PrincipalResolver as AuthPrincipalResolver, auth_mode)
    store = PostgresStore(database_url)
    mode = auth_mode()
    if mode == "pat":
        resource = os.environ.get("NINAI_PUBLIC_RESOURCE_URL", "").strip()
        if not resource:
            raise SystemExit("NINAI_PUBLIC_RESOURCE_URL is required in PAT mode")
        verifier = PATTokenVerifier(store._connection, resource)
        # PAT mode is deliberately self-hosted; no external issuer is contacted.
        sdk_auth = MCPAuthSettings(issuer_url=resource, resource_server_url=resource,
                                   service_documentation_url=resource, required_scopes=[])
        control_verifier = verifier
    else:
        settings = AuthSettings.from_env()
        validator = JWTValidator(settings)
        verifier = MCPTokenVerifier(validator, AuthPrincipalResolver(store._connection, settings))
        control_verifier = OAuthControlTokenVerifier(
            validator, settings, OAuthIdentityResolver(store._connection, settings)
        )
        sdk_auth = MCPAuthSettings(
            issuer_url=settings.issuer,
            resource_server_url=settings.resource,
            service_documentation_url=settings.resource,
            # Some MCP hosts (including Codex) currently request only OIDC
            # identity scopes even when the protected-resource document
            # advertises API scopes. Requiring those scopes here would reject a
            # correctly issued, audience-bound token before Ninai can apply its
            # stricter live database grants. Every read/write still validates
            # the active workspace/client and an explicit, revocable project
            # capability in Postgres; new clients start with no grants.
            required_scopes=[],
        )
    control_service = ControlService(
        store._connection, self_hosted=mode == "pat",
        public_mcp_url=str(sdk_auth.resource_server_url),
        oauth_issuer=settings.issuer if mode == "oauth" else None,
    )
    create_mcp(store, token_verifier=verifier, control_token_verifier=control_verifier,
               auth=sdk_auth, control_service=control_service,
               control_oauth_settings=settings if mode == "oauth" else None,
               host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")),
               read_calls_per_minute=int(os.environ.get("NINAI_READ_CALLS_PER_MINUTE", DEFAULT_READ_CALLS_PER_MINUTE)),
               write_calls_per_minute=int(os.environ.get("NINAI_WRITE_CALLS_PER_MINUTE", DEFAULT_WRITE_CALLS_PER_MINUTE)),
               max_request_body_bytes=int(os.environ.get("NINAI_MAX_REQUEST_BODY_BYTES", MAX_REQUEST_BODY_BYTES))).run(
                   transport="streamable-http")


__all__ = ["HostedMCPTools", "PrincipalResolver", "RateLimitError", "RequestBodyLimitMiddleware",
           "SlidingWindowRateLimiter", "create_mcp", "main"]
