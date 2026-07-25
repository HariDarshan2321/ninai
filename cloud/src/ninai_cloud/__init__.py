"""Ninai's explicit opt-in hosted persistence adapter."""

from .postgres_store import (
    AuthorizationError,
    HostedMemory,
    IdempotencyConflict,
    PostgresStore,
    Principal,
)

__all__ = [
    "AuthorizationError",
    "HostedMemory",
    "IdempotencyConflict",
    "PostgresStore",
    "Principal",
]
