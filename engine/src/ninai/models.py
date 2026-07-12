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

# Per-memory sensitivity label. Display-only in the MVP: it is shown in the
# desktop UI and is editable, but does not yet influence ranking or disclosure
# (the dossier's sensitivity penalty is post-MVP). Scope remains the access
# control that actually gates recall.
ALLOWED_SENSITIVITIES = {
    "normal",
    "personal",
    "restricted",
    "blocked",
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
    sensitivity: str = "normal"
