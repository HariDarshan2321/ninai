"""Storage-independent contracts for Ninai's current local engine behavior.

These values deliberately describe capabilities the SQLite adapter already has.
Future adapters can implement the protocol without importing SQLite or transport
types, while existing callers may continue using ``ninai.store.MemoryStore``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from .models import Memory


MemoryCandidate = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    """The caller whose scope grants must be enforced.

    ``client_id=None`` represents the trusted local vault owner, matching the
    existing CLI and desktop behavior.
    """

    client_id: str | None = None


@dataclass(frozen=True, slots=True)
class CreateMemoryRequest:
    content: str
    memory_type: str = "fact"
    scope: str = "project"
    source_uri: str = "user://manual"
    importance: float = 0.6
    confidence: float = 1.0
    sensitivity: str = "normal"


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str
    scopes: frozenset[str]
    limit: int = 20


@dataclass(frozen=True, slots=True)
class DisclosureEvent:
    client_id: str
    purpose: str
    query: str
    scopes: tuple[str, ...]
    memory_ids: tuple[str, ...]
    estimated_tokens: int


@runtime_checkable
class MemoryStore(Protocol):
    """Minimal backend contract implemented by the current SQLite store."""

    def create_memory(self, request: CreateMemoryRequest) -> Memory: ...

    def get_memory(
        self, principal: PrincipalContext, memory_id: str
    ) -> MemoryCandidate | None: ...

    def search_candidates(self, request: SearchRequest) -> list[MemoryCandidate]: ...

    def record_disclosure(self, event: DisclosureEvent) -> None: ...


@runtime_checkable
class PermissionService(Protocol):
    """Scope resolution contract kept separate from storage and transport."""

    def allowed_scopes(self, client_id: str) -> set[str]: ...
