"""Canonical manual references and requester-bound source verification.

Adapters are trusted server-side code. They must independently match the
requester's authorized provider identity to the exact requested resource on
each call. A workspace installation credential alone cannot establish access.
Adapters hold no credentials in these values and must not fetch a pasted URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import hashlib
import json
import re
from typing import Protocol
from urllib.parse import unquote, urlsplit
from uuid import UUID


_SLUG = re.compile(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?")
_GITHUB_REPOSITORY = re.compile(r"[a-zA-Z0-9_.-]{1,100}")
_NUMBER = re.compile(r"[1-9][0-9]{0,17}")
_LINEAR_IDENTIFIER = re.compile(r"[a-zA-Z][a-zA-Z0-9]{0,15}-[1-9][0-9]{0,17}")
_NOTION_PAGE = re.compile(
    r"(?:.+-)?(?P<page>[0-9a-fA-F]{32}|"
    r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})"
)
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_PROOF_MAX_AGE = {
    "github": timedelta(seconds=5),
    "linear": timedelta(seconds=5),
    "notion": timedelta(seconds=5),
}


@dataclass(frozen=True, slots=True, repr=False)
class SourceReference:
    provider: str
    resource_key: str
    canonical_url: str


def parse_source_reference(url: str) -> SourceReference:
    """Recognize a supported resource shape and discard query, title and anchor."""
    invalid = ValueError("Enter an HTTPS GitHub pull request, Linear issue or Notion page link.")
    if not isinstance(url, str) or len(url) > 2048:
        raise invalid
    url = url.strip(" ")
    if not url or not url.isascii() or any(not 33 <= ord(char) <= 126 or char == "\\" for char in url):
        raise invalid
    try:
        parts = urlsplit(url)
    except ValueError:
        raise invalid from None
    if parts.scheme != "https":
        raise invalid
    host = parts.netloc.lower()
    path = parts.path.removesuffix("/").split("/")[1:]
    if not parts.path.startswith("/") or any(not segment or segment in {".", ".."} for segment in path):
        raise invalid

    if host == "github.com" and len(path) == 4:
        owner, repository, kind, number = path
        if (len(owner) <= 39 and _SLUG.fullmatch(owner) and _GITHUB_REPOSITORY.fullmatch(repository)
                and kind == "pull" and _NUMBER.fullmatch(number)):
            key = f"{owner.lower()}/{repository.lower()}/pull/{number}"
            return SourceReference("github", key, f"https://github.com/{key}")

    if host == "linear.app" and len(path) in {3, 4}:
        workspace, kind, issue = path[:3]
        if (_SLUG.fullmatch(workspace) and kind == "issue" and _LINEAR_IDENTIFIER.fullmatch(issue)
                and (len(path) == 3 or _title_segment(path[3]))):
            key = f"{workspace.lower()}/issue/{issue.upper()}"
            return SourceReference("linear", key, f"https://linear.app/{key}")

    if host in {"notion.so", "www.notion.so"} or _is_notion_site(host):
        if len(path) in {1, 2} and (len(path) == 1 or _SLUG.fullmatch(path[0])):
            if _title_segment(path[-1]) and (match := _NOTION_PAGE.fullmatch(path[-1])):
                page_id = UUID(match["page"]).hex
                return SourceReference("notion", page_id, f"https://www.notion.so/{page_id}")

    raise invalid


def _is_notion_site(host: str) -> bool:
    suffix = ".notion.site"
    return host.endswith(suffix) and bool(_SLUG.fullmatch(host.removesuffix(suffix)))


def _title_segment(segment: str) -> bool:
    if re.search(r"%(?![0-9a-fA-F]{2})", segment):
        return False
    try:
        decoded = unquote(segment, errors="strict")
    except UnicodeDecodeError:
        return False
    return decoded.isprintable() and decoded not in {".", ".."} and not any(char in decoded for char in "/\\")


def source_fingerprint(provider: str, provider_resource_id: str, revision: str) -> str:
    """Hash an adapter-resolved immutable provider ID and revision or evidence digest."""
    if provider not in _PROOF_MAX_AGE or any(
        not isinstance(value, str) or not 1 <= len(value) <= 256 or not value.isprintable()
        for value in (provider_resource_id, revision)
    ):
        raise ValueError("Invalid source evidence identity.")
    encoded = json.dumps([provider, provider_resource_id, revision], separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


class SourceAccess(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"


class SourceStatus(StrEnum):
    VERIFIED = "verified"
    CHANGED = "changed"
    UNAVAILABLE = "unavailable"
    PERMISSION_DENIED = "permission-denied"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True, repr=False)
class SourceRequest:
    # Construct from authenticated server state before calling the verifier.
    workspace_id: str
    project_id: str
    user_id: str
    binding_id: str | None
    authorization_epoch: int
    reference: SourceReference
    expected_fingerprint: str | None
    request_id: str


@dataclass(frozen=True, slots=True, repr=False)
class SourceProof:
    request: SourceRequest
    checked_at: datetime
    access: SourceAccess
    fingerprint: str | None = None


class SourceVerifier(Protocol):
    def verify(self, request: SourceRequest) -> SourceProof | None:
        """Check current requester access and evidence through a narrow provider API.

        Use the start of the check as checked_at. Return unknown when access
        cannot be affirmatively established. Return a grant without a digest
        only when access was affirmatively proven and evidence is unavailable.
        """
        ...


class UnavailableSourceVerifier:
    """Default until a provider broker with deployment-specific authority is configured."""

    def verify(self, request: SourceRequest) -> None:
        return None


def _fresh_proof(request: SourceRequest, proof: SourceProof | None, now: datetime) -> bool:
    if not isinstance(proof, SourceProof) or proof.request != request or not request.request_id:
        return False
    if any(not isinstance(value, datetime) or value.utcoffset() is None for value in (now, proof.checked_at)):
        return False
    try:
        canonical = parse_source_reference(request.reference.canonical_url)
    except ValueError:
        return False
    if canonical != request.reference:
        return False
    return timedelta() <= now - proof.checked_at <= _PROOF_MAX_AGE[canonical.provider]


def _valid_fingerprint(fingerprint: str | None) -> bool:
    return isinstance(fingerprint, str) and _FINGERPRINT.fullmatch(fingerprint) is not None


def verified_fingerprint(request: SourceRequest, proof: SourceProof | None, *, now: datetime) -> str | None:
    """Get the exact digest for an authorized review to pin before approval."""
    if (request.expected_fingerprint is None and isinstance(proof, SourceProof)
            and proof.access is SourceAccess.GRANTED and _valid_fingerprint(proof.fingerprint)
            and _fresh_proof(request, proof, now)):
        return proof.fingerprint
    return None


def proof_status(request: SourceRequest, proof: SourceProof | None, *, now: datetime) -> SourceStatus:
    """Revalidate evidence at release. Keep denial and unknown internal."""
    if proof is None or not _fresh_proof(request, proof, now):
        return SourceStatus.UNKNOWN
    if proof.access is SourceAccess.DENIED:
        return SourceStatus.PERMISSION_DENIED
    if proof.access is not SourceAccess.GRANTED:
        return SourceStatus.UNKNOWN
    if not _valid_fingerprint(proof.fingerprint) or not _valid_fingerprint(request.expected_fingerprint):
        return SourceStatus.UNAVAILABLE
    if proof.fingerprint != request.expected_fingerprint:
        return SourceStatus.CHANGED
    return SourceStatus.VERIFIED
