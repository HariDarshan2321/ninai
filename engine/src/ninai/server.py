from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from .config import client_id as configured_client_id
from .store import MemoryStore

mcp = FastMCP(
    "Ninai",
    instructions=(
        "Ninai is a local-first memory service. Store only durable facts, decisions, "
        "commitments, procedures, and preferences. Never store credentials or raw temporary output. "
        "Use recall with a clear purpose. Returned facts are permission-filtered and include provenance."
    ),
)
_store: MemoryStore | None = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


@mcp.tool()
def remember(
    content: str,
    memory_type: str = "fact",
    scope: str = "project",
    source_uri: str = "conversation://current",
    importance: float = 0.6,
    confidence: float = 1.0,
) -> str:
    """Store one compact durable memory with a scope and source reference."""
    try:
        memory = get_store().remember(
            content,
            memory_type=memory_type,
            scope=scope,
            source_uri=source_uri,
            importance=importance,
            confidence=confidence,
        )
        return json.dumps(
            {
                "stored": True,
                "id": memory.id,
                "scope": memory.scope,
                "source_uri": memory.source_uri,
            }
        )
    except ValueError as error:
        return json.dumps({"stored": False, "error": str(error)})


@mcp.tool()
def recall(
    query: str,
    purpose: str,
    max_items: int = 6,
    max_tokens: int = 600,
) -> str:
    """Return the smallest useful permission-filtered context packet for this client."""
    packet = get_store().recall(
        query,
        client_id=configured_client_id(),
        purpose=purpose,
        max_items=max(1, min(max_items, 12)),
        max_tokens=max(100, min(max_tokens, 2000)),
    )
    return json.dumps(packet, ensure_ascii=False)


@mcp.tool()
def explain(memory_id: str) -> str:
    """Show a memory's content, scope, timestamps, and provenance."""
    memory = get_store().explain(memory_id)
    return json.dumps(memory or {"error": "Memory not found"}, ensure_ascii=False)


@mcp.tool()
def forget(memory_id: str) -> str:
    """Soft-delete a memory from the local vault."""
    return json.dumps({"forgotten": get_store().forget(memory_id)})


@mcp.tool()
def status() -> str:
    """Return local vault health and the current client's allowed scopes."""
    return json.dumps(get_store().status(configured_client_id()), ensure_ascii=False)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
