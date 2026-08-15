from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from ..config import database_path
from ..models import (
    ALLOWED_MEMORY_TYPES,
    ALLOWED_SCOPES,
    ALLOWED_SENSITIVITIES,
)
from ..store import MemoryStore

# Default clients shown on the Permissions screen even before they appear in the
# vault, so the owner can pre-authorize the assistants Ninai targets first.
DEFAULT_CLIENTS = ["claude-code", "codex", "claude-desktop"]


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _err(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


def _source_scheme(source_uri: str) -> str:
    scheme = urlsplit(source_uri).scheme
    return scheme or "unknown"


class DesktopApi:
    """In-process JS<->Python bridge for the desktop window.

    Every method returns a JSON-serializable envelope: {"ok": True, "data": ...}
    or {"ok": False, "error": "<message>"}. No business logic lives here; each
    method is a thin, defensive wrapper over the MemoryStore. The store is used
    as the local operator (no client_id), i.e. with full owner access.
    """

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()

    # -- reference data -----------------------------------------------------

    def meta(self) -> dict[str, Any]:
        try:
            return _ok(
                {
                    "scopes": sorted(ALLOWED_SCOPES),
                    "memory_types": sorted(ALLOWED_MEMORY_TYPES),
                    "sensitivities": sorted(ALLOWED_SENSITIVITIES),
                    "vault_path": str(database_path()),
                    "sensitivity_note": (
                        "Sensitivity is a label shown here for your reference. "
                        "It does not yet affect what is disclosed; scope controls access."
                    ),
                }
            )
        except Exception as error:  # pragma: no cover - defensive
            return _err(str(error))

    # -- memories -----------------------------------------------------------

    def list_memories(self, limit: int = 200) -> dict[str, Any]:
        try:
            return _ok(self.store.list_memories(limit=int(limit)))
        except Exception as error:
            return _err(str(error))

    def search(self, query: str) -> dict[str, Any]:
        try:
            text = (query or "").strip()
            if not text:
                return _ok(self.store.list_memories(limit=200))
            # Owner-side content match across all scopes. (recall() is the
            # scope-gated path for AI clients; the owner sees everything.)
            lowered = text.lower()
            matches = [
                memory
                for memory in self.store.list_memories(limit=1000)
                if lowered in str(memory["content"]).lower()
            ]
            return _ok(matches)
        except Exception as error:
            return _err(str(error))

    def get_memory(self, memory_id: str) -> dict[str, Any]:
        try:
            memory = self.store.explain(memory_id)
            return _ok(memory) if memory else _err("Memory not found")
        except Exception as error:
            return _err(str(error))

    def add_memory(
        self,
        content: str,
        memory_type: str = "fact",
        scope: str = "project",
        source_uri: str = "app://manual",
        sensitivity: str = "normal",
    ) -> dict[str, Any]:
        try:
            memory = self.store.remember(
                content,
                memory_type=memory_type,
                scope=scope,
                source_uri=source_uri or "app://manual",
                sensitivity=sensitivity,
            )
            return _ok({"id": memory.id})
        except ValueError as error:
            return _err(str(error))
        except Exception as error:  # pragma: no cover - defensive
            return _err(str(error))

    def update_memory(self, memory_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        try:
            allowed = {
                "content",
                "memory_type",
                "scope",
                "sensitivity",
                "importance",
                "confidence",
            }
            fields = {k: v for k, v in (changes or {}).items() if k in allowed}
            updated = self.store.update(memory_id, **fields)
            return _ok(updated) if updated else _err("Memory not found")
        except ValueError as error:
            return _err(str(error))
        except Exception as error:  # pragma: no cover - defensive
            return _err(str(error))

    def delete_memory(self, memory_id: str) -> dict[str, Any]:
        try:
            return _ok({"forgotten": self.store.forget(memory_id)})
        except Exception as error:
            return _err(str(error))

    # -- today / sources ----------------------------------------------------

    def today(self) -> dict[str, Any]:
        try:
            memories = self.store.list_memories(limit=1000)
            commitments = [m for m in memories if m["memory_type"] == "commitment"]
            decisions = [m for m in memories if m["memory_type"] == "decision"]
            rank = lambda m: (float(m["importance"]), str(m["updated_at"]))
            commitments.sort(key=rank, reverse=True)
            decisions.sort(key=rank, reverse=True)
            return _ok({"commitments": commitments, "decisions": decisions[:10]})
        except Exception as error:
            return _err(str(error))

    def sources(self) -> dict[str, Any]:
        try:
            groups: dict[str, dict[str, Any]] = {}
            for memory in self.store.list_memories(limit=1000):
                scheme = _source_scheme(str(memory["source_uri"]))
                group = groups.setdefault(
                    scheme, {"scheme": scheme, "count": 0, "last_seen": ""}
                )
                group["count"] += 1
                updated = str(memory["updated_at"])
                if updated > group["last_seen"]:
                    group["last_seen"] = updated
            ordered = sorted(groups.values(), key=lambda g: g["count"], reverse=True)
            return _ok(ordered)
        except Exception as error:
            return _err(str(error))

    # -- permissions --------------------------------------------------------

    def list_clients(self) -> dict[str, Any]:
        try:
            seen = list(self.store.clients())
            for default in DEFAULT_CLIENTS:
                if default not in seen:
                    seen.append(default)
            return _ok(sorted(seen))
        except Exception as error:
            return _err(str(error))

    def get_permissions(self, client_id: str) -> dict[str, Any]:
        try:
            granted = self.store.allowed_scopes(client_id)
            return _ok(
                {scope: (scope in granted) for scope in sorted(ALLOWED_SCOPES)}
            )
        except Exception as error:
            return _err(str(error))

    def set_permission(
        self, client_id: str, scope: str, allowed: bool
    ) -> dict[str, Any]:
        try:
            client_id = (client_id or "").strip()
            if not client_id:
                return _err("Client id cannot be empty")
            if allowed:
                self.store.grant(client_id, scope)
            else:
                self.store.revoke(client_id, scope)
            return _ok({"client_id": client_id, "scope": scope, "allowed": bool(allowed)})
        except ValueError as error:
            return _err(str(error))
        except Exception as error:  # pragma: no cover - defensive
            return _err(str(error))

    # -- activity -----------------------------------------------------------

    def list_logs(self, limit: int = 100) -> dict[str, Any]:
        try:
            return _ok(self.store.list_logs(limit=int(limit)))
        except Exception as error:
            return _err(str(error))

    def list_sessions(self, limit: int = 100) -> dict[str, Any]:
        try:
            return _ok(self.store.list_sessions(limit=int(limit)))
        except Exception as error:
            return _err(str(error))

    def delete_session(self, session_id: str) -> dict[str, Any]:
        try:
            return _ok({"deleted": self.store.delete_session(session_id)})
        except Exception as error:
            return _err(str(error))

    def capture_status(self) -> dict[str, Any]:
        try:
            return _ok({"enabled": self.store.capture_enabled()})
        except Exception as error:
            return _err(str(error))

    def set_capture_enabled(self, enabled: bool) -> dict[str, Any]:
        try:
            self.store.set_capture_enabled(bool(enabled))
            return _ok({"enabled": self.store.capture_enabled()})
        except Exception as error:
            return _err(str(error))
