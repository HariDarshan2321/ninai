"""OAuth protected-resource authentication for the hosted Ninai service.

Ninai is a resource server, not an authorization server.  Tokens are issued by
the configured external issuer and this module maps signed claims to database
identities before any hosted operation is allowed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, ContextManager, Mapping

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .postgres_store import AuthorizationError, Principal


class AuthenticationError(AuthorizationError):
    """A bearer credential is absent, invalid, or cannot identify a client."""


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


@dataclass(frozen=True, slots=True)
class AuthSettings:
    issuer: str
    audience: str
    resource: str
    jwks_uri: str
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    workspace_claim: str = "ninai_workspace_id"
    client_connection_claim: str = "ninai_client_connection_id"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AuthSettings":
        values = os.environ if env is None else env
        return cls(
            issuer=_required(values, "NINAI_OAUTH_ISSUER"),
            audience=_required(values, "NINAI_OAUTH_AUDIENCE"),
            resource=_required(values, "NINAI_PUBLIC_RESOURCE_URL"),
            jwks_uri=_required(values, "NINAI_OAUTH_JWKS_URI"),
            authorization_endpoint=values.get("NINAI_OAUTH_AUTHORIZATION_ENDPOINT") or None,
            token_endpoint=values.get("NINAI_OAUTH_TOKEN_ENDPOINT") or None,
            workspace_claim=values.get("NINAI_OAUTH_WORKSPACE_CLAIM", "ninai_workspace_id"),
            client_connection_claim=values.get(
                "NINAI_OAUTH_CLIENT_CONNECTION_CLAIM", "ninai_client_connection_id"
            ),
        )

    def protected_resource_metadata(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "authorization_servers": [self.issuer],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["ninai:read", "ninai:propose", "ninai:remember"],
        }

    def authorization_server_metadata(self) -> dict[str, Any]:
        """Configured issuer metadata; this must not be presented as Ninai-owned."""
        result: dict[str, Any] = {"issuer": self.issuer, "jwks_uri": self.jwks_uri}
        if self.authorization_endpoint:
            result["authorization_endpoint"] = self.authorization_endpoint
        if self.token_endpoint:
            result["token_endpoint"] = self.token_endpoint
        return result


class JWTValidator:
    """Validate asymmetric JWTs using the external issuer's JWKS."""

    def __init__(self, settings: AuthSettings) -> None:
        self.settings = settings
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install ninai-cloud to validate hosted bearer tokens") from exc
        self._jwt = jwt
        self._keys = jwt.PyJWKClient(settings.jwks_uri)

    def validate(self, token: str) -> Mapping[str, Any]:
        try:
            key = self._keys.get_signing_key_from_jwt(token)
            claims = self._jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                options={"require": ["exp", "iss", "aud", "sub", "resource"]},
            )
        except Exception as exc:
            raise AuthenticationError("Bearer token validation failed") from exc
        resource = claims.get("resource")
        resources = resource if isinstance(resource, list) else [resource]
        if self.settings.resource not in resources:
            raise AuthenticationError("Bearer token is not valid for this resource")
        return claims


class PrincipalResolver:
    """Resolve signed token claims and re-check live database revocation state."""

    def __init__(self, connect: Callable[[], ContextManager[Any]], settings: AuthSettings) -> None:
        self._connect = connect
        self.settings = settings

    def resolve(self, claims: Mapping[str, Any]) -> Principal:
        values = {
            "user_id": claims.get("sub"),
            "workspace_id": claims.get(self.settings.workspace_claim),
            "client_connection_id": claims.get(self.settings.client_connection_claim),
        }
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise AuthenticationError("Bearer token is missing Ninai identity claims")
        principal = Principal(**values)  # type: ignore[arg-type]
        with self._connect() as db:
            row = db.execute(
                """SELECT 1 FROM client_connections c
                   JOIN workspace_members m ON m.workspace_id=c.workspace_id AND m.user_id=%s
                   JOIN workspaces w ON w.id=c.workspace_id
                   JOIN users u ON u.id=m.user_id
                   WHERE c.id=%s AND c.workspace_id=%s AND c.user_id=%s
                     AND c.status='active' AND c.revoked_at IS NULL
                     AND m.revoked_at IS NULL AND w.deleted_at IS NULL AND u.deleted_at IS NULL""",
                (principal.user_id, principal.client_connection_id,
                 principal.workspace_id, principal.user_id),
            ).fetchone()
        if not row:
            raise AuthenticationError("Client, membership, or workspace is revoked or unknown")
        return principal


class BearerAuthenticator:
    def __init__(self, validator: JWTValidator, resolver: PrincipalResolver) -> None:
        self.validator = validator
        self.resolver = resolver

    def authenticate(self, authorization: str | None) -> Principal:
        scheme, separator, token = (authorization or "").partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("A Bearer authorization header is required")
        return self.resolver.resolve(self.validator.validate(token.strip()))


class NinaiAccessToken(AccessToken):
    """MCP access token enriched only from issuer-signed, database-checked data."""

    user_id: str
    workspace_id: str
    client_connection_id: str


class MCPTokenVerifier(TokenVerifier):
    """Adapter consumed by MCP's bearer-auth middleware."""

    def __init__(self, validator: JWTValidator, resolver: PrincipalResolver) -> None:
        self.validator = validator
        self.resolver = resolver

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = self.validator.validate(token)
            principal = self.resolver.resolve(claims)
        except AuthenticationError:
            return None
        raw_scopes = claims.get("scope", "")
        scopes = raw_scopes.split() if isinstance(raw_scopes, str) else list(raw_scopes or [])
        return NinaiAccessToken(
            token=token,
            client_id=principal.client_connection_id,
            scopes=scopes,
            expires_at=int(claims["exp"]) if claims.get("exp") is not None else None,
            resource=self.resolver.settings.resource,
            subject=principal.user_id,
            claims={
                "user_id": principal.user_id,
                "workspace_id": principal.workspace_id,
                "client_connection_id": principal.client_connection_id,
            },
            user_id=principal.user_id,
            workspace_id=principal.workspace_id,
            client_connection_id=principal.client_connection_id,
        )


def build_token_verifier(database_url: str, settings: AuthSettings | None = None) -> MCPTokenVerifier:
    """Build the verifier used by the hosted MCP entry point."""
    from .postgres_store import PostgresStore

    configured = settings or AuthSettings.from_env()
    store = PostgresStore(database_url)
    return MCPTokenVerifier(JWTValidator(configured), PrincipalResolver(store._connection, configured))
