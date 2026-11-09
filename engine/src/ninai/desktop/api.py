from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from typing import Any
from urllib.parse import urlsplit

from ..config import database_path
from ..connectors import status as editor_status
from ..connectors import configure as configure_editor
from ..models import (
    ALLOWED_MEMORY_TYPES,
    ALLOWED_SCOPES,
    ALLOWED_SENSITIVITIES,
)
from ..store import MemoryStore

# Default clients shown on the Permissions screen even before they appear in the
# vault, so the owner can pre-authorize the assistants Ninai targets first.
DEFAULT_CLIENTS = ["claude-code", "codex", "gemini", "cursor", "vscode"]

CLIENT_LABELS = {
    "claude-code": "Claude Code",
    "codex": "Codex",
    "gemini": "Gemini CLI",
    "cursor": "Cursor",
    "vscode": "VS Code",
}


def _cli_connection_status(client_id: str) -> tuple[bool, bool]:
    executable = {"claude-code": "claude", "codex": "codex"}.get(client_id)
    if not executable:
        return False, False
    installed = shutil.which(executable) is not None
    if not installed:
        return False, False
    command = [executable, "mcp", "get", "ninai-local"]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True, False
    return True, result.returncode == 0


def _gemini_connection_status() -> tuple[bool, bool]:
    installed = shutil.which("gemini") is not None
    if not installed:
        return False, False
    settings = Path.home() / ".gemini" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
        connection = data.get("mcpServers", {}).get("ninai-local", {})
        connected = bool(connection.get("command")) and connection.get("trust") is False
    except (OSError, json.JSONDecodeError, AttributeError):
        connected = False
    return True, connected


def _client_status(client_id: str) -> dict[str, Any]:
    if client_id in {"cursor", "vscode"}:
        result = editor_status(client_id)
        return {"id": client_id, "name": CLIENT_LABELS[client_id], **result}
    if client_id == "gemini":
        installed, connected = _gemini_connection_status()
    else:
        installed, connected = _cli_connection_status(client_id)
    if connected:
        status = "configured"
        message = "Configuration found. Open this assistant and test a memory to verify the connection."
    elif installed:
        status = "needs_attention"
        message = "Installed, but Ninai is not connected. Rerun the Ninai installer to repair it."
    else:
        status = "not_installed"
        message = "Not found on this computer. Install this assistant first, then rerun the Ninai installer."
    return {
        "id": client_id,
        "name": CLIENT_LABELS[client_id],
        "installed": installed,
        "configured": connected,
        "status": status,
        "message": message,
    }


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
        project_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            memory = self.store.remember(
                content,
                memory_type=memory_type,
                scope=scope,
                source_uri=source_uri or "app://manual",
                sensitivity=sensitivity,
                project_id=project_id,
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
            recent = sorted(
                memories, key=lambda memory: str(memory["updated_at"]), reverse=True
            )[:10]
            commitments = [m for m in memories if m["memory_type"] == "commitment"]
            decisions = [m for m in memories if m["memory_type"] == "decision"]
            rank = lambda m: (float(m["importance"]), str(m["updated_at"]))
            commitments.sort(key=rank, reverse=True)
            decisions.sort(key=rank, reverse=True)
            return _ok(
                {
                    "recent_memories": recent,
                    "commitments": commitments,
                    "decisions": decisions[:10],
                }
            )
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

    def list_projects(self) -> dict[str, Any]:
        try:
            return _ok(self.store.list_projects())
        except Exception as error:
            return _err(str(error))

    def create_project(self, name: str) -> dict[str, Any]:
        try:
            if not name or not name.strip():
                return _err("Give the project a name.")
            return _ok(self.store.ensure_project(
                name=name, binding_key=f"app://project/{uuid.uuid4()}", cwd_or_repo=""
            ))
        except Exception as error:
            return _err(str(error))

    def get_project_permissions(self, client_id: str) -> dict[str, Any]:
        try:
            projects: dict[str, dict[str, Any]] = {}
            for item in self.store.project_permissions(client_id):
                project_id = str(item["project_id"])
                entry = projects.setdefault(project_id, {
                    "project_id": project_id, "can_read": False,
                    "can_write": False, "can_delete": False,
                })
                entry[f"can_{item['action']}"] = bool(item["allowed"])
            return _ok(list(projects.values()))
        except Exception as error:
            return _err(str(error))

    def set_project_permission(
        self, client_id: str, project_id: str, action: str, allowed: bool
    ) -> dict[str, Any]:
        try:
            if allowed:
                self.store.grant_project(client_id, project_id, action)
            else:
                self.store.revoke_project(client_id, project_id, action)
            return _ok({"allowed": bool(allowed)})
        except Exception as error:
            return _err(str(error))

    def get_capabilities(self, client_id: str) -> dict[str, Any]:
        try:
            permissions = {str(item["scope"]): item for item in self.store.permissions(client_id)}
            return _ok({scope: {
                "read": bool(permissions.get(scope, {}).get("allowed", False)),
                "write": bool(permissions.get(scope, {}).get("can_write", False)),
                "delete": bool(permissions.get(scope, {}).get("can_delete", False)),
            } for scope in sorted(ALLOWED_SCOPES)})
        except Exception as error:
            return _err(str(error))

    def set_capability(
        self, client_id: str, scope: str, action: str, allowed: bool
    ) -> dict[str, Any]:
        try:
            self.store.set_scope_capability(client_id, scope, action, allowed)
            return _ok({"allowed": bool(allowed)})
        except Exception as error:
            return _err(str(error))

    def list_clients(self) -> dict[str, Any]:
        try:
            seen = list(self.store.clients())
            for default in DEFAULT_CLIENTS:
                if default not in seen:
                    seen.append(default)
            return _ok(sorted(seen))
        except Exception as error:
            return _err(str(error))

    def assistant_statuses(self) -> dict[str, Any]:
        """Report observable installation and Ninai connection state.

        The probe is read-only. It never installs software, grants access, or
        modifies an assistant's configuration.
        """
        try:
            return _ok([_client_status(client_id) for client_id in DEFAULT_CLIENTS])
        except Exception as error:  # pragma: no cover - defensive
            return _err(str(error))

    def connect_assistant(self, client_id: str) -> dict[str, Any]:
        """Explicit owner action: configure an editor without granting memory."""
        try:
            if client_id not in {"cursor", "vscode"}:
                return _err("Use the Ninai installer to configure this assistant.")
            executable = Path(sys.executable)
            command = (executable.parents[3] / "venv/bin/ninai-mcp"
                       if getattr(sys, "frozen", False) and sys.platform == "darwin"
                       else executable.with_name("ninai-mcp.exe" if sys.platform == "win32" else "ninai-mcp"))
            if not command.is_file():
                return _err("Ninai's connection program is missing. Rerun the installer to repair it.")
            configure_editor(client_id, str(command))
            return _ok(_client_status(client_id))
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
