"""OAuth protected-resource authentication for the hosted Ninai service.

Ninai is a resource server, not an authorization server.  Tokens are issued by
the configured external issuer and this module maps signed claims to database
identities before any hosted operation is allowed.
"""

from __future__ import annotations

import os
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Callable, ContextManager, Mapping

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .postgres_store import AuthorizationError, Principal

MAX_BEARER_TOKEN_CHARS = 8_192


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
    control_client_id: str | None = None
    control_base_url: str | None = None
    workspace_claim: str = "https://ninai.io/workspace_id"
    oauth_client_claim: str = "client_id"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AuthSettings":
        values = os.environ if env is None else env
        result = cls(
            issuer=_required(values, "NINAI_OAUTH_ISSUER"),
            audience=_required(values, "NINAI_OAUTH_AUDIENCE"),
            resource=_required(values, "NINAI_PUBLIC_RESOURCE_URL"),
            jwks_uri=_required(values, "NINAI_OAUTH_JWKS_URI"),
            authorization_endpoint=values.get("NINAI_OAUTH_AUTHORIZATION_ENDPOINT") or None,
            token_endpoint=values.get("NINAI_OAUTH_TOKEN_ENDPOINT") or None,
            control_client_id=values.get("NINAI_OAUTH_CONTROL_CLIENT_ID") or None,
            control_base_url=values.get("NINAI_CONTROL_BASE_URL") or None,
            workspace_claim=values.get(
                "NINAI_OAUTH_WORKSPACE_CLAIM", "https://ninai.io/workspace_id"
            ),
            oauth_client_claim=values.get("NINAI_OAUTH_CLIENT_ID_CLAIM", "client_id"),
        )

        if bool(result.control_client_id) != bool(result.control_base_url):
            raise ValueError(
                "NINAI_OAUTH_CONTROL_CLIENT_ID and NINAI_CONTROL_BASE_URL must be configured together"
            )
        return result

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
        if not isinstance(token, str) or not token or len(token) > MAX_BEARER_TOKEN_CHARS:
            raise AuthenticationError("Bearer token validation failed")
        try:
            key = self._keys.get_signing_key_from_jwt(token)
            claims = self._jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except Exception as exc:
            raise AuthenticationError("Bearer token validation failed") from exc
        resource = claims.get("resource")
        if resource is not None:
            resources = resource if isinstance(resource, list) else [resource]
            if self.settings.resource not in resources:
                raise AuthenticationError("Bearer token is not valid for this resource")
        elif self.settings.audience != self.settings.resource:
            raise AuthenticationError(
                "Bearer token has no resource claim and its audience is not the MCP resource"
            )
        return claims


class OAuthIdentityResolver:
    """Map an issuer subject to a stable internal UUID user."""

    def __init__(self, connect: Callable[[], ContextManager[Any]], settings: AuthSettings) -> None:
        self._connect = connect
        self.settings = settings

    def resolve_user(self, claims: Mapping[str, Any], *, create: bool = False) -> str:
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError("Bearer token is missing its subject")
        with self._connect() as db:
            row = db.execute(
                """SELECT user_id FROM oauth_identities
                   WHERE issuer=%s AND subject=%s""", (self.settings.issuer, subject)
            ).fetchone()
            if row:
                db.execute(
                    """UPDATE oauth_identities SET last_seen_at=now(),
                       email=COALESCE(%s,email),display_name=COALESCE(%s,display_name)
                       WHERE issuer=%s AND subject=%s""",
                    (claims.get("email"), claims.get("name"), self.settings.issuer, subject),
                )
                return str(row["user_id"])
            if not create:
                raise AuthenticationError("OAuth account has not completed Ninai setup")
            user_id = str(uuid.uuid4())
            email = claims.get("email") if isinstance(claims.get("email"), str) else None
            display_name = claims.get("name") if isinstance(claims.get("name"), str) else None
            # Never link accounts by email. A collision receives an internal placeholder.
            stored_email = email or f"{user_id}@identity.invalid"
            if db.execute("SELECT 1 FROM users WHERE email=%s", (stored_email,)).fetchone():
                stored_email = f"{user_id}@identity.invalid"
            db.execute(
                "INSERT INTO users(id,email,display_name) VALUES(%s,%s,%s)",
                (user_id, stored_email, display_name or stored_email.split("@", 1)[0]),
            )
            db.execute(
                """INSERT INTO oauth_identities
                   (id,issuer,subject,user_id,email,display_name)
                   VALUES(%s,%s,%s,%s,%s,%s)""",
                (str(uuid.uuid4()), self.settings.issuer, subject, user_id, email, display_name),
            )
            return user_id

    def workspace_for(self, user_id: str, requested: Any = None) -> str | None:
        if requested is not None:
            try:
                requested = str(uuid.UUID(str(requested)))
            except (ValueError, TypeError, AttributeError) as exc:
                raise AuthenticationError("Bearer token has an invalid workspace claim") from exc
        with self._connect() as db:
            rows = db.execute(
                """SELECT workspace_id FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
                   WHERE m.user_id=%s AND m.revoked_at IS NULL AND w.deleted_at IS NULL
                     AND (%s::uuid IS NULL OR m.workspace_id=%s::uuid) ORDER BY m.created_at""",
                (user_id, requested, requested),
            ).fetchall()
        if requested is not None and not rows:
            raise AuthenticationError("Requested workspace is unavailable")
        return str(rows[0]["workspace_id"]) if len(rows) == 1 else None


class PrincipalResolver:
    """Resolve signed token claims and re-check live database revocation state."""

    def __init__(self, connect: Callable[[], ContextManager[Any]], settings: AuthSettings) -> None:
        self._connect = connect
        self.settings = settings
        self.identities = OAuthIdentityResolver(connect, settings)

    def resolve(self, claims: Mapping[str, Any]) -> Principal:
        user_id = self.identities.resolve_user(claims)
        oauth_client_id = claims.get(self.settings.oauth_client_claim) or claims.get("azp")
        if not isinstance(oauth_client_id, str) or not oauth_client_id.strip():
            raise AuthenticationError("Bearer token is missing its OAuth client identity")
        requested_workspace = claims.get(self.settings.workspace_claim)
        if requested_workspace is not None:
            try:
                requested_workspace = str(uuid.UUID(str(requested_workspace)))
            except (ValueError, TypeError, AttributeError) as exc:
                raise AuthenticationError("Bearer token has an invalid workspace claim") from exc
        with self._connect() as db:
            row = db.execute(
                """SELECT c.user_id,c.workspace_id,c.id AS client_connection_id
                   FROM oauth_client_bindings b JOIN client_connections c
                     ON c.workspace_id=b.workspace_id AND c.id=b.client_connection_id
                   JOIN workspace_members m ON m.workspace_id=c.workspace_id AND m.user_id=%s
                   JOIN workspaces w ON w.id=c.workspace_id
                   JOIN users u ON u.id=m.user_id
                   WHERE b.issuer=%s AND b.oauth_client_id=%s AND b.user_id=%s
                     AND (%s::uuid IS NULL OR b.workspace_id=%s::uuid) AND b.revoked_at IS NULL
                     AND c.status='active' AND c.revoked_at IS NULL
                     AND m.revoked_at IS NULL AND w.deleted_at IS NULL AND u.deleted_at IS NULL""",
                (user_id, self.settings.issuer, oauth_client_id, user_id,
                 requested_workspace, requested_workspace),
            ).fetchone()
            if not row:
                row = self._provision_unprivileged_connection(
                    db, claims=claims, user_id=user_id,
                    oauth_client_id=oauth_client_id,
                    requested_workspace=requested_workspace,
                )
        if not row:
            raise AuthenticationError(
                "OAuth client is not connected, is ambiguous, or has been revoked"
            )
        return Principal(str(row["user_id"]), str(row["workspace_id"]),
                         str(row["client_connection_id"]))

    def _provision_unprivileged_connection(
        self, db: Any, *, claims: Mapping[str, Any], user_id: str,
        oauth_client_id: str, requested_workspace: str | None,
    ) -> Mapping[str, Any] | None:
        """Bind a newly authenticated MCP client without granting memory access.

        This makes standards-compliant DCR clients usable without operator lookup
        of their generated client ID. It deliberately creates no scope grants.
        Revoked bindings are never recreated, and ambiguous multi-workspace users
        must choose a workspace through an issuer claim or the dashboard.
        """
        existing = db.execute(
            """SELECT revoked_at FROM oauth_client_bindings
               WHERE issuer=%s AND oauth_client_id=%s AND user_id=%s
                 AND (%s::uuid IS NULL OR workspace_id=%s::uuid)
               ORDER BY created_at DESC LIMIT 1""",
            (self.settings.issuer, oauth_client_id, user_id,
             requested_workspace, requested_workspace),
        ).fetchone()
        if existing:
            return None
        workspace = db.execute(
            """SELECT min(m.workspace_id::text) AS workspace_id, count(*) AS workspace_count
               FROM workspace_members m JOIN workspaces w ON w.id=m.workspace_id
               JOIN users u ON u.id=m.user_id
               WHERE m.user_id=%s AND m.revoked_at IS NULL AND w.deleted_at IS NULL
                 AND u.deleted_at IS NULL
                 AND (%s::uuid IS NULL OR m.workspace_id=%s::uuid)""",
            (user_id, requested_workspace, requested_workspace),
        ).fetchone()
        if not workspace or int(workspace.get("workspace_count", 0)) != 1:
            return None
        workspace_id = str(workspace["workspace_id"])
        connection_id = str(uuid.uuid4())
        client_name = claims.get("client_name")
        display_name = (str(client_name).strip() if isinstance(client_name, str) else "") or "OAuth MCP client"
        db.execute(
            """INSERT INTO client_connections
               (id,workspace_id,user_id,provider,client_type,external_client_id,
                display_name,metadata_json)
               VALUES(%s,%s,%s,'external','remote-mcp',%s,%s,%s::jsonb)""",
            (connection_id, workspace_id, user_id, oauth_client_id, display_name,
             '{"setup_status":"connected","auto_provisioned":true}'),
        )
        db.execute(
            """INSERT INTO oauth_client_bindings
               (id,issuer,oauth_client_id,user_id,workspace_id,client_connection_id)
               VALUES(%s,%s,%s,%s,%s,%s)""",
            (str(uuid.uuid4()), self.settings.issuer, oauth_client_id, user_id,
             workspace_id, connection_id),
        )
        return {"user_id": user_id, "workspace_id": workspace_id,
                "client_connection_id": connection_id}


class BearerAuthenticator:
    def __init__(self, validator: JWTValidator, resolver: PrincipalResolver) -> None:
        self.validator = validator
        self.resolver = resolver

    def authenticate(self, authorization: str | None) -> Principal:
        scheme, separator, token = (authorization or "").partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("A Bearer authorization header is required")
        if len(token) > MAX_BEARER_TOKEN_CHARS:
            raise AuthenticationError("Bearer token validation failed")
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
        if not token or len(token) > MAX_BEARER_TOKEN_CHARS:
            return None
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


class OAuthControlTokenVerifier(TokenVerifier):
    """Verify an issuer token for account setup without requiring a client yet.

    Existing-workspace control operations still perform a live membership check
    in ``ControlService``. This verifier exists only to break the first-workspace
    bootstrap cycle; it must never protect MCP memory tools.
    """

    def __init__(self, validator: JWTValidator, settings: AuthSettings,
                 identities: OAuthIdentityResolver) -> None:
        self.validator = validator
        self.settings = settings
        self.identities = identities

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = self.validator.validate(token)
        except AuthenticationError:
            return None
        try:
            user_id = self.identities.resolve_user(claims, create=True)
            workspace_id = self.identities.workspace_for(
                user_id, claims.get(self.settings.workspace_claim)
            )
        except AuthenticationError:
            return None
        trusted = {"user_id": user_id}
        if workspace_id:
            trusted["workspace_id"] = workspace_id
        for name in ("email", "name"):
            if isinstance(claims.get(name), str):
                trusted[name] = claims[name]
        return AccessToken(
            token=token, client_id=str(claims.get("client_id") or claims.get("azp") or user_id),
            scopes=[], expires_at=int(claims["exp"]) if claims.get("exp") is not None else None,
            resource=self.settings.resource, subject=str(claims.get("sub")), claims=trusted,
        )


class PATTokenVerifier(TokenVerifier):
    """Verify opaque self-hosted tokens by digest and live database state.

    The plaintext credential is never persisted. The single query checks token
    expiry/revocation and all enclosing identity state on every request.
    """

    def __init__(self, connect: Callable[[], ContextManager[Any]], resource: str) -> None:
        self._connect = connect
        self.resource = resource

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or len(token) > 512:
            return None
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._connect() as db:
            row = db.execute(
                """SELECT t.user_id,t.workspace_id,t.client_connection_id,
                          extract(epoch from t.expires_at)::bigint AS expires_at
                   FROM personal_access_tokens t
                   JOIN client_connections c ON c.workspace_id=t.workspace_id
                     AND c.id=t.client_connection_id AND c.user_id=t.user_id
                   JOIN workspace_members m ON m.workspace_id=t.workspace_id AND m.user_id=t.user_id
                   JOIN workspaces w ON w.id=t.workspace_id
                   JOIN users u ON u.id=t.user_id
                   WHERE t.token_hash=%s AND t.revoked_at IS NULL AND t.expires_at > now()
                     AND c.status='active' AND c.revoked_at IS NULL
                     AND m.revoked_at IS NULL AND w.deleted_at IS NULL AND u.deleted_at IS NULL""",
                (digest,),
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE personal_access_tokens SET last_used_at=now() WHERE token_hash=%s",
                (digest,),
            )
        user_id = str(row["user_id"])
        workspace_id = str(row["workspace_id"])
        client_id = str(row["client_connection_id"])
        return NinaiAccessToken(
            token=token, client_id=client_id,
            scopes=["ninai:read", "ninai:propose", "ninai:remember"],
            expires_at=int(row["expires_at"]), resource=self.resource, subject=user_id,
            claims={"user_id": user_id, "workspace_id": workspace_id,
                    "client_connection_id": client_id, "auth_mode": "pat"},
            user_id=user_id, workspace_id=workspace_id, client_connection_id=client_id,
        )


def auth_mode(env: Mapping[str, str] | None = None) -> str:
    """Return the explicitly configured authentication mode."""
    mode = (os.environ if env is None else env).get("NINAI_AUTH_MODE", "oauth").strip().lower()
    if mode not in {"oauth", "pat"}:
        raise ValueError("NINAI_AUTH_MODE must be 'oauth' or 'pat'")
    return mode


def build_token_verifier(database_url: str, settings: AuthSettings | None = None) -> MCPTokenVerifier:
    """Build the verifier used by the hosted MCP entry point."""
    from .postgres_store import PostgresStore

    configured = settings or AuthSettings.from_env()
    store = PostgresStore(database_url)
    return MCPTokenVerifier(JWTValidator(configured), PrincipalResolver(store._connection, configured))
