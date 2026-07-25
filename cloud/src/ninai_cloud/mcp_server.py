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
from starlette.requests import Request
from starlette.responses import JSONResponse

from .postgres_store import AuthorizationError, HostedMemory, IdempotencyConflict, PostgresStore, Principal
from .policy import validate_memory_type
from .control_api import ControlService, create_control_app
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


def create_mcp(store: PostgresStore, *, token_verifier: TokenVerifier,
               control_token_verifier: TokenVerifier | None = None,
               principal_resolver: PrincipalResolver = _principal_from_access_token,
               auth: MCPAuthSettings,
               host: str = "127.0.0.1", port: int = 8000,
               read_calls_per_minute: int = DEFAULT_READ_CALLS_PER_MINUTE,
               write_calls_per_minute: int = DEFAULT_WRITE_CALLS_PER_MINUTE,
               max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES,
               control_service: ControlService | None = None) -> FastMCP:
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

    @mcp.tool(description="Search active memories in this client's granted scopes. Results include provenance.", structured_output=True)
    def search(query: str, purpose: str, limit: int = 10) -> dict[str, Any]:
        return guarded(tools.search, query, purpose, limit)

    @mcp.tool(description="Fetch one active memory by ID if it is in this client's granted scopes.", structured_output=True)
    def fetch(memory_id: str, purpose: str) -> dict[str, Any]:
        return guarded(tools.fetch, memory_id, purpose)

    @mcp.tool(description="Return a compact, token-bounded context packet with provenance and disclosure audit.", structured_output=True)
    def recall(query: str, purpose: str, max_items: int = 6, max_tokens: int = 600) -> dict[str, Any]:
        return guarded(tools.recall, query, purpose, max_items, max_tokens)

    @mcp.tool(description="Propose source-backed durable memory for review; proposed items are not recalled.", structured_output=True)
    def propose_memory(content: str, memory_type: str, scope_kind: str, scope_id: str,
                       source_uri: str, idempotency_key: str, project_id: str | None = None,
                       importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return guarded(tools.propose_memory, content, memory_type, scope_kind, scope_id,
                       source_uri, idempotency_key, project_id, importance, confidence)

    @mcp.tool(description="Activate durable memory only with explicit auto-activate permission.", structured_output=True)
    def remember(content: str, memory_type: str, scope_kind: str, scope_id: str,
                 source_uri: str, idempotency_key: str, project_id: str | None = None,
                 importance: float = 0.6, confidence: float = 1.0) -> dict[str, Any]:
        return guarded(tools.remember, content, memory_type, scope_kind, scope_id,
                       source_uri, idempotency_key, project_id, importance, confidence)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "ninai-cloud-mcp"})

    connect = getattr(store, "_connection", None)
    if connect is None:  # Allows transport registration with contract-test stores.
        def connect():
            raise RuntimeError("The control center requires a PostgreSQL-backed store")
    control = create_control_app(control_service or ControlService(connect),
                                 control_token_verifier or token_verifier)

    @mcp.custom_route("/control", methods=["GET"])
    async def control_page(request: Request):
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
        sdk_auth = MCPAuthSettings(issuer_url=settings.issuer, resource_server_url=settings.resource,
                                   service_documentation_url=settings.resource, required_scopes=[])
    control_service = ControlService(
        store._connection, self_hosted=mode == "pat",
        public_mcp_url=str(sdk_auth.resource_server_url),
        oauth_issuer=settings.issuer if mode == "oauth" else None,
    )
    create_mcp(store, token_verifier=verifier, control_token_verifier=control_verifier,
               auth=sdk_auth, control_service=control_service,
               host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")),
               read_calls_per_minute=int(os.environ.get("NINAI_READ_CALLS_PER_MINUTE", DEFAULT_READ_CALLS_PER_MINUTE)),
               write_calls_per_minute=int(os.environ.get("NINAI_WRITE_CALLS_PER_MINUTE", DEFAULT_WRITE_CALLS_PER_MINUTE)),
               max_request_body_bytes=int(os.environ.get("NINAI_MAX_REQUEST_BODY_BYTES", MAX_REQUEST_BODY_BYTES))).run(
                   transport="streamable-http")


__all__ = ["HostedMCPTools", "PrincipalResolver", "RateLimitError", "RequestBodyLimitMiddleware",
           "SlidingWindowRateLimiter", "create_mcp", "main"]
