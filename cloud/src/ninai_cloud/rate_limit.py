"""In-process abuse controls for the hosted beta.

These deliberately retain only workspace/client identifiers and timestamps, never
bearer credentials, request bodies, queries, or memory content.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable

from .postgres_store import Principal

MAX_REQUEST_BODY_BYTES = 64 * 1024


class RateLimitError(Exception):
    """The authenticated client exhausted an application-level request quota."""


class SlidingWindowRateLimiter:
    """Process-local sliding-window limiter keyed by workspace and client."""

    def __init__(self, maximum: int, window_seconds: float = 60,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if maximum < 1 or window_seconds <= 0:
            raise ValueError("Rate limit and window must be positive")
        self.maximum, self.window_seconds, self.clock = maximum, window_seconds, clock
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, principal: Principal) -> None:
        key = (principal.workspace_id, principal.client_connection_id)
        now = self.clock()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.maximum:
                raise RateLimitError("Request rate limit exceeded; retry later")
            events.append(now)


class RequestBodyLimitMiddleware:
    """Reject oversized mutating request bodies without logging their contents."""

    def __init__(self, app: Any, maximum: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app, self.maximum = app, maximum

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = self.maximum + 1
        if length > self.maximum:
            await self._reject(send)
            return
        consumed = 0

        async def bounded_receive() -> dict[str, Any]:
            nonlocal consumed
            message = await receive()
            if message.get("type") == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.maximum:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self.app(scope, bounded_receive, send)
        except _RequestBodyTooLarge:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Any) -> None:
        body = b'{"error":{"code":"payload_too_large","message":"Request body is too large"}}'
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode()),
                                (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": body})


class _RequestBodyTooLarge(Exception):
    pass
