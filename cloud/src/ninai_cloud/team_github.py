"""Verify one GitHub pull request using the requesting user's GitHub App grant."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPException
import hashlib
import json
import re
from time import monotonic
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .team_sources import SourceAccess, SourceProof, SourceRequest, parse_source_reference, source_fingerprint


_API_ORIGIN = "https://api.github.com"
_USER_TOKEN = re.compile(r"ghu_[A-Za-z0-9_]{1,508}")
_HEAD_SHA = re.compile(r"[a-f0-9]{40}")
_IDENTITY_LIMIT = 64 * 1024
_PULL_LIMIT = 512 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True, slots=True, repr=False)
class GitHubUserGrant:
    """Ephemeral token from a trusted, requester-specific managed broker."""

    github_user_id: int
    access_token: str


class GitHubSourceVerifier:
    def __init__(self, grant_for: Callable[[SourceRequest], GitHubUserGrant | None], *, opener=None):
        # The broker must bind the grant to the request's tenant, project, and user.
        self._grant_for = grant_for
        self._opener = opener if opener is not None else build_opener(ProxyHandler({}), _NoRedirect())

    def verify(self, request: SourceRequest) -> SourceProof | None:
        start = datetime.now(timezone.utc)
        deadline = monotonic() + 4
        reference = request.reference
        try:
            if reference.provider != "github" or parse_source_reference(reference.canonical_url) != reference:
                return None
            grant = self._grant_for(request)
            if (not isinstance(grant, GitHubUserGrant) or type(grant.github_user_id) is not int
                    or grant.github_user_id <= 0 or not isinstance(grant.access_token, str)
                    or not _USER_TOKEN.fullmatch(grant.access_token)):
                return None
            identity = self._get_json("/user", grant.access_token, _IDENTITY_LIMIT, deadline)
            if type(identity.get("id")) is not int or identity["id"] != grant.github_user_id:
                return None
            owner, repository, _, number = reference.resource_key.split("/")
            pull = self._get_json(f"/repos/{owner}/{repository}/pulls/{number}",
                                  grant.access_token, _PULL_LIMIT, deadline)
            fingerprint = self._fingerprint(pull, f"{owner}/{repository}", int(number))
            if not fingerprint or monotonic() >= deadline:
                return None
            return SourceProof(request, start, SourceAccess.GRANTED, fingerprint)
        except HTTPError as error:
            error.close()
            return None
        except (OSError, HTTPException, ValueError, RecursionError):
            # Provider errors, permission denials, missing resources and malformed
            # evidence produce the same result. Never log provider payloads or tokens.
            return None

    def _get_json(self, path: str, token: str, limit: int, deadline: float) -> dict:
        outgoing = Request(_API_ORIGIN + path, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "X-GitHub-Api-Version": "2026-03-10",
        })
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError
        with self._opener.open(outgoing, timeout=min(remaining, 1.25)) as response:
            if (response.status != 200 or response.geturl() != outgoing.full_url
                    or response.headers.get_content_type() != "application/json"
                    or response.headers.get("Content-Encoding", "identity").lower() != "identity"):
                raise ValueError("Unexpected GitHub response")
            data = bytearray()
            while len(data) <= limit and monotonic() < deadline:
                chunk = response.read1(min(16 * 1024, limit + 1 - len(data)))
                if not chunk:
                    decoded = json.loads(data)
                    if isinstance(decoded, dict) and monotonic() < deadline:
                        return decoded
                    break
                data.extend(chunk)
        raise ValueError("Invalid or oversized GitHub response")

    @staticmethod
    def _fingerprint(pull: dict, repository: str, number: int) -> str | None:
        base = pull.get("base")
        head = pull.get("head")
        repo = base.get("repo") if isinstance(base, dict) else None
        full_name = repo.get("full_name") if isinstance(repo, dict) else None
        sha = head.get("sha") if isinstance(head, dict) else None
        node_id = pull.get("node_id")
        title, body = pull.get("title"), pull.get("body")
        if (type(pull.get("number")) is not int or pull["number"] != number or not isinstance(full_name, str)
                or full_name.lower() != repository or not isinstance(sha, str) or not _HEAD_SHA.fullmatch(sha)
                or not isinstance(node_id, str) or not isinstance(title, str)
                or "body" not in pull or (body is not None and not isinstance(body, str))):
            return None
        # Evidence covers the pull request description and commit. Comments,
        # repository files and linked pages need separate proof to support a claim.
        revision = json.dumps([sha, title, body], ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return source_fingerprint("github", node_id, hashlib.sha256(revision).hexdigest())
