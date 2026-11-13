"""Ninai's explicit opt-in hosted persistence adapter."""

__version__ = "0.1.1"

from .postgres_store import (
    AuthorizationError,
    HostedMemory,
    IdempotencyConflict,
    StorageLimitError,
    PostgresStore,
    Principal,
)
from .auth import (
    AuthSettings,
    PATTokenVerifier,
    AuthenticationError,
    BearerAuthenticator,
    JWTValidator,
    MCPTokenVerifier,
    OAuthControlTokenVerifier,
    OAuthIdentityResolver,
    NinaiAccessToken,
    PrincipalResolver,
    build_token_verifier,
    auth_mode,
)

__all__ = [
    "AuthorizationError",
    "HostedMemory",
    "IdempotencyConflict",
    "StorageLimitError",
    "PostgresStore",
    "Principal",
    "AuthSettings",
    "PATTokenVerifier",
    "AuthenticationError",
    "BearerAuthenticator",
    "JWTValidator",
    "MCPTokenVerifier",
    "OAuthControlTokenVerifier",
    "OAuthIdentityResolver",
    "NinaiAccessToken",
    "PrincipalResolver",
    "build_token_verifier",
    "auth_mode",
]
