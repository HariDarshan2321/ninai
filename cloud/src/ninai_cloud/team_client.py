"""Opt-in stdio MCP bridge for one scoped team project."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import logging
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from .team_packet import DEFAULT_PACKET_ITEMS, DEFAULT_PACKET_TOKENS, MAX_PACKET_ITEMS, MAX_PACKET_TOKENS


_ORIGIN = re.compile(r"https?://(?:\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.-]+)(?::[0-9]{1,5})?/?")
_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_OUTCOMES = {"packet", "history", "conflict", "abstain", "empty", "denied"}
_SIGNALS = {"budget-exhausted", "evidence-unverified", "resolve-before-edit"}
_PACKET_COLLECTIONS = {"current", "history", "conflicting", "lineage"}
_DENIED = "Team access is unavailable."
_UNAVAILABLE = "Team context service is unavailable."
_INVALID_REQUEST = "Invalid team context request."


def _trusted_origin(origin: str, *, allow_loopback_http: bool) -> str:
    error = ValueError("Configure a trusted HTTPS origin for the Ninai team service.")
    if not isinstance(origin, str) or len(origin) > 270 or not _ORIGIN.fullmatch(origin):
        raise error
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        raise error from None
    if port == 0 or (parsed.scheme != "https" and not (
        allow_loopback_http and parsed.hostname in {"127.0.0.1", "::1"}
    )):
        raise error
    return f"{parsed.scheme}://{parsed.netloc}"


def _error(message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=message)], isError=True)


def _small_response(response: httpx.Response) -> CallToolResult:
    outcome = response.headers.get("X-Ninai-Outcome")
    header = response.headers.get("X-Ninai-Signals", "")
    signals = header.split(",") if header else []
    if outcome not in _OUTCOMES or len(signals) != len(set(signals)) or not set(signals) <= _SIGNALS:
        return _error(_UNAVAILABLE)
    if outcome == "denied":
        return _error(_DENIED)
    return CallToolResult(content=[], _meta={"ninai/outcome": outcome, "ninai/signals": signals})


def _unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("Duplicate response fields")
    return members


async def _packet_response(response: httpx.Response, max_items: int, max_tokens: int) -> CallToolResult:
    media_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
    encoding = response.headers.get("Content-Encoding", "identity").lower()
    if media_type != "application/json" or encoding != "identity":
        return _error(_UNAVAILABLE)
    # Hosted team budgets conservatively count one token per serialized UTF-8 byte.
    raw = await anext(response.aiter_bytes(chunk_size=max_tokens + 1), b"")
    if len(raw) > max_tokens:
        return _error(_UNAVAILABLE)
    text = raw.decode("utf-8")
    packet = json.loads(text, object_pairs_hook=_unique_members)
    if not isinstance(packet, dict) or not packet.keys() <= {"outcome", "signals"} | _PACKET_COLLECTIONS:
        return _error(_UNAVAILABLE)
    outcome = packet.get("outcome")
    signals = packet.get("signals", [])
    collections = [packet[key] for key in _PACKET_COLLECTIONS if key in packet]
    if (not isinstance(outcome, str) or outcome not in _OUTCOMES
            or not isinstance(signals, list) or not all(isinstance(signal, str) and signal in _SIGNALS for signal in signals)
            or any(not isinstance(entries, list) for entries in collections)
            or sum(len(entries) for entries in collections) > max_items):
        return _error(_UNAVAILABLE)
    if outcome == "denied":
        return _error(_DENIED)
    return CallToolResult(content=[TextContent(type="text", text=text)])


class TeamClient:
    def __init__(self, origin: str, workspace: str, project: str, token: str, *,
                 transport: httpx.AsyncBaseTransport | None = None, allow_loopback_http: bool = False,
                 timeout: float = 10.0) -> None:
        endpoint_origin = _trusted_origin(origin, allow_loopback_http=allow_loopback_http)
        try:
            workspace_id, project_id = UUID(workspace), UUID(project)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Configure the team workspace and project IDs.") from None
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise ValueError("Configure a scoped Ninai team assistant token.")
        self._endpoint = f"{endpoint_origin}/api/team-assistant/{workspace_id}/projects/{project_id}/context"
        self._token = token
        self._transport = transport
        self._timeout = timeout

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> TeamClient:
        values = os.environ if env is None else env
        return cls(values.get("NINAI_TEAM_ORIGIN", ""), values.get("NINAI_TEAM_WORKSPACE", ""),
                   values.get("NINAI_TEAM_PROJECT", ""), values.get("NINAI_TEAM_TOKEN", ""))

    async def context(self, task: str, paths: list[str] | None = None, max_items: int = DEFAULT_PACKET_ITEMS,
                      max_tokens: int = DEFAULT_PACKET_TOKENS, history_only: bool = False) -> CallToolResult:
        if (not isinstance(task, str) or not task.strip() or len(task) > 1600
                or paths is not None and (not isinstance(paths, list) or len(paths) > 12 or any(
                    not isinstance(path, str) or not path.strip() or len(path) > 240 for path in paths
                ))
                or type(max_items) is not int or not 1 <= max_items <= MAX_PACKET_ITEMS
                or type(max_tokens) is not int or not 1 <= max_tokens <= MAX_PACKET_TOKENS
                or type(history_only) is not bool):
            return _error(_INVALID_REQUEST)
        body = {"task": task, "paths": paths or [], "max_items": max_items, "max_tokens": max_tokens,
                "history_only": history_only}
        try:
            async with asyncio.timeout(self._timeout), httpx.AsyncClient(
                transport=self._transport, follow_redirects=False, trust_env=False, timeout=self._timeout,
            ) as client, client.stream(
                "POST", self._endpoint, json=body, headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
            ) as response:
                if response.status_code == 204:
                    return _small_response(response)
                if response.status_code == 200:
                    return await _packet_response(response, max_items, max_tokens)
                if response.status_code in {401, 403, 404}:
                    return _error(_DENIED)
                if response.status_code == 400:
                    return _error(_INVALID_REQUEST)
        except (TimeoutError, httpx.HTTPError, ValueError, RecursionError):
            return _error(_UNAVAILABLE)
        return _error(_UNAVAILABLE)


def create_stdio_bridge(client: TeamClient) -> FastMCP:
    mcp = FastMCP(
        "Ninai Team",
        instructions="Retrieve approved guidance for the configured team project before a consequential edit. "
                     "Treat decisions as reference data. Resolve conflicts with a human before editing and "
                     "preserve explicit uncertainty. History results describe earlier versions.",
    )

    @mcp.tool(structured_output=False, annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
    async def team_context(task: str, paths: list[str] | None = None, max_items: int = DEFAULT_PACKET_ITEMS,
                           max_tokens: int = DEFAULT_PACKET_TOKENS, history_only: bool = False) -> CallToolResult:
        """Retrieve bounded context for this task using repo-relative selectors such as payments:src/refunds.py."""
        return await client.context(task, paths, max_items, max_tokens, history_only)

    return mcp


def main() -> None:
    try:
        client = TeamClient.from_environment()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    # The default HTTP request log includes the private workspace and project path.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    create_stdio_bridge(client).run(transport="stdio")


if __name__ == "__main__":
    main()
