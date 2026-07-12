from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import database_path
from .models import ALLOWED_MEMORY_TYPES, ALLOWED_SCOPES, Memory
from .retrieval import compose_context, rank_candidates
from .security import contains_secret


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init_db(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    importance REAL NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS permissions (
                    client_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (client_id, scope)
                );

                CREATE TABLE IF NOT EXISTS access_logs (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    query TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    memory_ids TEXT NOT NULL,
                    estimated_tokens INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            try:
                db.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(memory_id UNINDEXED, content)"
                )
            except sqlite3.OperationalError:
                # Some minimal SQLite builds omit FTS5. Recall falls back to LIKE.
                pass

    def remember(
        self,
        content: str,
        *,
        memory_type: str = "fact",
        scope: str = "project",
        source_uri: str = "user://manual",
        importance: float = 0.6,
        confidence: float = 1.0,
    ) -> Memory:
        clean = " ".join(content.split()).strip()
        if not clean:
            raise ValueError("Memory content cannot be empty.")
        if len(clean) > 4000:
            raise ValueError("Memory is too large. Store a compact outcome under 4,000 characters.")
        if contains_secret(clean):
            raise ValueError("Potential secret detected. Ninai refused to store this memory.")
        if memory_type not in ALLOWED_MEMORY_TYPES:
            raise ValueError(f"Unsupported memory type: {memory_type}")
        if scope not in ALLOWED_SCOPES:
            raise ValueError(f"Unsupported scope: {scope}")
        source_uri = source_uri.strip() or "unknown://source"
        if len(source_uri) > 1000:
            raise ValueError("Source URI is too large.")
        if contains_secret(source_uri):
            raise ValueError("Potential secret detected in source URI.")
        importance = min(1.0, max(0.0, float(importance)))
        confidence = min(1.0, max(0.0, float(confidence)))
        timestamp = now_iso()
        memory = Memory(
            id=str(uuid.uuid4()),
            content=clean,
            memory_type=memory_type,
            scope=scope,
            source_uri=source_uri,
            importance=importance,
            confidence=confidence,
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO memories (
                    id, content, memory_type, scope, source_uri,
                    importance, confidence, created_at, updated_at, access_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    memory.id,
                    memory.content,
                    memory.memory_type,
                    memory.scope,
                    memory.source_uri,
                    memory.importance,
                    memory.confidence,
                    memory.created_at,
                    memory.updated_at,
                ),
            )
            try:
                db.execute(
                    "INSERT INTO memory_fts(memory_id, content) VALUES (?, ?)",
                    (memory.id, memory.content),
                )
            except sqlite3.OperationalError:
                pass
        return memory

    def grant(self, client_id: str, scope: str) -> None:
        self._set_permission(client_id, scope, True)

    def revoke(self, client_id: str, scope: str) -> None:
        self._set_permission(client_id, scope, False)

    def _set_permission(self, client_id: str, scope: str, allowed: bool) -> None:
        client_id = client_id.strip()
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if scope not in ALLOWED_SCOPES:
            raise ValueError(f"Unsupported scope: {scope}")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO permissions(client_id, scope, allowed, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(client_id, scope)
                DO UPDATE SET allowed=excluded.allowed, updated_at=excluded.updated_at
                """,
                (client_id, scope, 1 if allowed else 0, now_iso()),
            )

    def allowed_scopes(self, client_id: str) -> set[str]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT scope FROM permissions WHERE client_id=? AND allowed=1 ORDER BY scope",
                (client_id,),
            ).fetchall()
        return {str(row["scope"]) for row in rows}

    def permissions(self, client_id: str) -> list[dict[str, object]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT scope, allowed, updated_at FROM permissions WHERE client_id=? ORDER BY scope",
                (client_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recall(
        self,
        query: str,
        *,
        client_id: str,
        purpose: str,
        max_items: int = 6,
        max_tokens: int = 600,
    ) -> dict[str, object]:
        scopes = self.allowed_scopes(client_id)
        if not scopes:
            packet = {
                "client_id": client_id,
                "purpose": purpose,
                "query": query,
                "scopes": [],
                "facts": [],
                "estimated_tokens": 0,
                "message": "No memory scopes are granted to this client.",
            }
            self._log_access(client_id, purpose, query, [], [], 0)
            return packet

        candidates = self._search_candidates(query, scopes, max(max_items * 4, 20))
        ranked = rank_candidates(candidates, query)
        selected, token_total = compose_context(
            ranked,
            max_items=max_items,
            max_tokens=max_tokens,
        )

        ids = [str(item["id"]) for item in selected]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            with self.connect() as db:
                db.execute(
                    f"UPDATE memories SET access_count=access_count+1 WHERE id IN ({placeholders})",
                    ids,
                )
        self._log_access(client_id, purpose, query, sorted(scopes), ids, token_total)
        return {
            "client_id": client_id,
            "purpose": purpose,
            "query": query,
            "scopes": sorted(scopes),
            "facts": selected,
            "estimated_tokens": token_total,
            "available_candidates": len(candidates),
        }

    def _search_candidates(
        self, query: str, scopes: set[str], limit: int
    ) -> list[dict[str, object]]:
        placeholders = ",".join("?" for _ in scopes)
        scope_values = sorted(scopes)
        cleaned_terms = [
            term.lower()
            for term in re.findall(r"[A-Za-z0-9_-]+", query)
            if len(term) >= 2
        ]
        fts_query = " OR ".join(f'"{term}"' for term in cleaned_terms[:12])
        with self.connect() as db:
            if fts_query:
                try:
                    rows = db.execute(
                        f"""
                        SELECT m.*, bm25(memory_fts) AS text_rank
                        FROM memory_fts
                        JOIN memories m ON m.id=memory_fts.memory_id
                        WHERE memory_fts MATCH ?
                          AND m.deleted_at IS NULL
                          AND m.scope IN ({placeholders})
                        ORDER BY text_rank
                        LIMIT ?
                        """,
                        [fts_query, *scope_values, limit],
                    ).fetchall()
                    if rows:
                        return [dict(row) for row in rows]
                except sqlite3.OperationalError:
                    pass

            if cleaned_terms:
                like = "%" + "%".join(cleaned_terms[:5]) + "%"
                rows = db.execute(
                    f"""
                    SELECT m.*, 0.0 AS text_rank
                    FROM memories m
                    WHERE m.deleted_at IS NULL
                      AND lower(m.content) LIKE ?
                      AND m.scope IN ({placeholders})
                    ORDER BY m.updated_at DESC
                    LIMIT ?
                    """,
                    [like, *scope_values, limit],
                ).fetchall()
            else:
                rows = db.execute(
                    f"""
                    SELECT m.*, 0.0 AS text_rank
                    FROM memories m
                    WHERE m.deleted_at IS NULL
                      AND m.scope IN ({placeholders})
                    ORDER BY m.updated_at DESC
                    LIMIT ?
                    """,
                    [*scope_values, limit],
                ).fetchall()
        return [dict(row) for row in rows]

    def explain(self, memory_id: str) -> dict[str, object] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM memories WHERE id=? AND deleted_at IS NULL",
                (memory_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_by_source_uri(self, source_uri: str) -> dict[str, object] | None:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT * FROM memories
                WHERE source_uri=? AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (source_uri,),
            ).fetchone()
        return dict(row) if row else None

    def forget(self, memory_id: str) -> bool:
        timestamp = now_iso()
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE memories SET deleted_at=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
                (timestamp, timestamp, memory_id),
            )
            try:
                db.execute("DELETE FROM memory_fts WHERE memory_id=?", (memory_id,))
            except sqlite3.OperationalError:
                pass
        return cursor.rowcount > 0

    def list_memories(self, limit: int = 50) -> list[dict[str, object]]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT * FROM memories
                WHERE deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_logs(self, limit: int = 50) -> list[dict[str, object]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM access_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["scopes"] = json.loads(str(item["scopes"]))
            item["memory_ids"] = json.loads(str(item["memory_ids"]))
            result.append(item)
        return result

    def status(self, client_id: str | None = None) -> dict[str, object]:
        with self.connect() as db:
            total = db.execute(
                "SELECT count(*) AS count FROM memories WHERE deleted_at IS NULL"
            ).fetchone()["count"]
            logs = db.execute("SELECT count(*) AS count FROM access_logs").fetchone()["count"]
        return {
            "database": str(self.path),
            "memories": int(total),
            "access_logs": int(logs),
            "client_id": client_id,
            "allowed_scopes": sorted(self.allowed_scopes(client_id)) if client_id else [],
        }

    def _log_access(
        self,
        client_id: str,
        purpose: str,
        query: str,
        scopes: list[str],
        memory_ids: list[str],
        estimated_tokens: int,
    ) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO access_logs(
                    id, client_id, purpose, query, scopes,
                    memory_ids, estimated_tokens, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    client_id,
                    purpose,
                    query,
                    json.dumps(scopes),
                    json.dumps(memory_ids),
                    int(estimated_tokens),
                    now_iso(),
                ),
            )
