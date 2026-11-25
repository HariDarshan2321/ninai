"""In-process abuse controls for the hosted beta.

These deliberately retain only workspace/client identifiers and timestamps, never
bearer credentials, request bodies, queries, or memory content.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from typing import Any, Callable, Hashable

from .postgres_store import Principal

MAX_REQUEST_BODY_BYTES = 64 * 1024


class RateLimitError(Exception):
    """The authenticated client exhausted an application-level request quota."""

    def __init__(self, message: str, *, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    """Process-local sliding-window limiter for a principal or an opaque key."""

    def __init__(self, maximum: int, window_seconds: float = 60,
                 clock: Callable[[], float] = time.monotonic, *, maximum_keys: int | None = None) -> None:
        if maximum < 1 or window_seconds <= 0 or (maximum_keys is not None and maximum_keys < 1):
            raise ValueError("Rate limit and window must be positive")
        self.maximum, self.window_seconds, self.clock = maximum, window_seconds, clock
        self.maximum_keys = maximum_keys
        self._events: OrderedDict[Hashable, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, principal: Principal) -> None:
        self.check_key((principal.workspace_id, principal.client_connection_id))

    def check_key(self, key: Hashable) -> None:
        with self._lock:
            now = self.clock()
            cutoff = now - self.window_seconds
            while self._events and next(iter(self._events.values()))[-1] <= cutoff:
                self._events.popitem(last=False)
            events = self._events.get(key)
            if events is None:
                if self.maximum_keys is not None and len(self._events) >= self.maximum_keys:
                    raise RateLimitError("Request rate limit exceeded; retry later")
                events = self._events[key] = deque()
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.maximum:
                raise RateLimitError("Request rate limit exceeded; retry later")
            events.append(now)
            self._events.move_to_end(key)


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
