"""Process-local owner verification capabilities; never exposed as MCP tools.

The owner transport supplies a trusted verifier (for example OS authentication).
A successful verification authorizes precisely the displayed request snapshot.
Tickets are not persisted and cannot survive process restart.
This protects the restricted MCP transport, not against arbitrary Python or
filesystem access by another process running as the same operating-system user.
"""
from __future__ import annotations

import copy
import hashlib
import json
import secrets
import threading
import time
from collections.abc import Callable


def request_fingerprint(request: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class OwnerVerificationAuthority:
    def __init__(self, verifier: Callable[[dict[str, object]], bool]) -> None:
        if not callable(verifier):
            raise TypeError("A trusted owner verifier is required")
        self._verifier = verifier
        self._tickets: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def verify(self, request: dict[str, object]) -> str:
        """Authenticate the owner against this exact review snapshot."""
        snapshot = copy.deepcopy(request)
        fingerprint = request_fingerprint(snapshot)
        if snapshot.get("status") != "pending":
            raise ValueError("Only pending requests can be verified")
        if self._verifier(copy.deepcopy(snapshot)) is not True:
            raise PermissionError("Owner verification was not completed")
        ticket = secrets.token_urlsafe(32)
        with self._lock:
            now = time.monotonic()
            self._tickets = {key: value for key, value in self._tickets.items() if value[1] > now}
            self._tickets[ticket] = (fingerprint, now + 60)
        return ticket

    def consume(self, ticket: str, request: dict[str, object]) -> None:
        """Consume once, including failed attempts, after checking the snapshot."""
        with self._lock:
            record = self._tickets.pop(ticket, None)
        if record is None or record[1] <= time.monotonic() or not secrets.compare_digest(
            record[0], request_fingerprint(request)
        ):
            raise PermissionError("Owner verification is missing, expired, or does not match this request")
