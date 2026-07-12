from __future__ import annotations

from dataclasses import dataclass

ALLOWED_MEMORY_TYPES = {
    "commitment",
    "decision",
    "event",
    "fact",
    "preference",
    "procedure",
}

ALLOWED_SCOPES = {
    "public",
    "work",
    "project",
    "preference",
    "personal",
    "finance",
    "health",
}


@dataclass(slots=True)
class Memory:
    id: str
    content: str
    memory_type: str
    scope: str
    source_uri: str
    importance: float
    confidence: float
    created_at: str
    updated_at: str
    access_count: int = 0
