"""Explicitly provisioned browser and project-bound assistant team API."""
from __future__ import annotations

import inspect
import json
from contextlib import contextmanager
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from psycopg import Error, IntegrityError, OperationalError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from .auth import MAX_BEARER_TOKEN_CHARS
from .control_api import ControlApp, SESSION_COOKIE, _jsonable
from .postgres_store import AuthorizationError
from .rate_limit import RateLimitError, SlidingWindowRateLimiter
from .team_packet import TaskPacket
from .team_store import DENIED, TeamHuman, digest, identifier

WORKSPACE_ACTIONS = {
    "enable": "enable", "invite": "invite", "accept": "accept_invite",
    "connect-repository": "connect_repository",
    "member": "change_member", "project-member": "assign_project", "group": "create_group",
    "group-edge": "group_edge", "project": "create_project", "archive-project": "archive_project", "audit": "audit",
}
PROJECT_ACTIONS = {
    "binding": "issue_binding", "propose": "propose", "approve": "review", "reviewer": "assign_reviewer",
    "context": "context", "proposals": "proposals", "export": "export_project",
    "handoffs": "handoffs", "publish-handoff": "publish_handoff",
    "audit-export": "export_project_audit",
    "rotate-binding": "update_binding", "revoke-binding": "update_binding",
    "retire": "suppress", "revoke": "suppress",
}
IDENTIFIERS = {"project", "user", "group", "decision", "replaces", "binding"}
READ_ACTIONS = {"identity", "overview", "audit", "context", "proposals", "export", "audit-export", "handoffs"}
ACCESS_ACTIONS = {"connect-repository", "member", "project-member", "group-edge", "archive-project", "reviewer", "rotate-binding",
                  "revoke-binding", "retire", "revoke"}
PROOF_ACTIONS = {"context", "approve", "proposals", "export", "audit-export"}
HEADERS = ControlApp._security_headers()


def json_response(body, status=200, *, headers=None):
    return Response(json.dumps(body, default=_jsonable), media_type="application/json",
                    status_code=status, headers={**HEADERS, **(headers or {})})


class TeamApp:
    def __init__(self, store, token_verifier, oauth_settings):
        if not oauth_settings or not oauth_settings.control_client_id:
            raise ValueError("Team preview requires verified dashboard OAuth identities")
        self.store = store
        self.token_verifier = token_verifier
        self.settings = oauth_settings
        authority = urlsplit(self.settings.resource)
        self.origin = f"{authority.scheme}://{authority.netloc}"
        self._ingress = SlidingWindowRateLimiter(600)
        self._peers = SlidingWindowRateLimiter(180, maximum_keys=600)
        self._human_reads = SlidingWindowRateLimiter(60, maximum_keys=600)
        self._human_writes = SlidingWindowRateLimiter(20, maximum_keys=600)
        self._human_access_changes = SlidingWindowRateLimiter(20, maximum_keys=600)
        self._assistant_reads = SlidingWindowRateLimiter(30, maximum_keys=600)
        self._assistant_writes = SlidingWindowRateLimiter(10, maximum_keys=600)
        self._request_slots = BoundedSemaphore(12)
        self._proof_slots = BoundedSemaphore(4)

    async def _human(self, request):
        authorization = request.headers.get("authorization")
        credential = self._bearer(authorization) if authorization is not None else request.cookies.get(SESSION_COOKIE)
        if not credential:
            raise AuthorizationError(DENIED)
        token = await self.token_verifier.verify_token(credential)
        claims = (token.claims or {}) if token is not None else {}
        if not token or token.client_id != self.settings.control_client_id or not token.subject or not token.expires_at:
            raise AuthorizationError(DENIED)
        return TeamHuman(identifier(claims.get("user_id")), self.settings.issuer, token.subject, token.expires_at)

    @staticmethod
    def _bearer(value):
        scheme, sep, credential = (value or "").partition(" ")
        if (scheme.lower() != "bearer" or not sep or not credential or " " in credential
                or len(credential) > MAX_BEARER_TOKEN_CHARS):
            raise AuthorizationError(DENIED)
        return credential

    @staticmethod
    @contextmanager
    def _slot(semaphore):
        if not semaphore.acquire(blocking=False):
            raise RateLimitError("Team request capacity reached", retry_after=1)
        try:
            yield
        finally:
            semaphore.release()

    def _check_ingress(self, request):
        # Only ASGI's resolved peer is used. The trusted server/proxy boundary
        # owns validation of any forwarding headers before they affect it.
        self._peers.check_key(request.client.host if request.client else None)
        self._ingress.check_key(None)

    @staticmethod
    def _limited(error):
        return json_response({"error": "Team request limit reached"}, 429,
                             headers={"Retry-After": str(error.retry_after)})

    async def page(self, request: Request):
        from .team_ui import TEAM_HTML

        try:
            self._check_ingress(request)
            with self._slot(self._request_slots):
                actor = await self._human(request)
                self._human_reads.check_key(actor.user_id)
        except RateLimitError as error:
            return self._limited(error)
        except AuthorizationError:
            return HTMLResponse(
                '<!doctype html><html lang="en"><meta charset="utf-8"><title>Ninai Team</title>'
                '<main><h1>Ninai Team</h1><p><a href="/control/login">Sign in</a> to open the preview.</p></main></html>',
                status_code=401, headers=HEADERS,
            )
        return HTMLResponse(TEAM_HTML, headers=HEADERS)

    async def handle(self, request: Request):
        try:
            self._check_ingress(request)
            with self._slot(self._request_slots):
                return await self._dispatch(request)
        except RateLimitError as error:
            return self._limited(error)
        except AuthorizationError:
            return json_response({"error": DENIED}, 403)
        except (ValueError, TypeError, UnicodeDecodeError):
            return json_response({"error": "Invalid team request"}, 400)
        except IntegrityError:
            return json_response({"error": "Team change could not be applied"}, 409)
        except OperationalError:
            return json_response({"error": "Team service is temporarily unavailable"}, 503)
        except Error:
            return json_response({"error": "Team request could not be completed"}, 500)

    async def _dispatch(self, request):
        is_assistant = request.url.path.startswith("/api/team-assistant/")
        prefix = "/api/team-assistant/" if is_assistant else "/api/team/"
        parts = request.url.path.removeprefix(prefix).split("/")
        action = parts[-1]
        data = {}
        if request.method == "POST":
            if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                return json_response({"error": "Expected a JSON body"}, 415)
            origin = request.headers.get("origin")
            if origin is not None and origin != self.origin or (
                not is_assistant and request.headers.get("authorization") is None and origin != self.origin
            ):
                raise AuthorizationError(DENIED)

        if is_assistant:
            actor = self._bearer(request.headers.get("authorization"))
            limiter = self._assistant_reads if action in {"context", "handoffs"} else self._assistant_writes
            limiter.check_key(digest(actor))
        else:
            actor = await self._human(request)
            if action in ACCESS_ACTIONS:
                limiter = self._human_access_changes
            else:
                limiter = self._human_reads if action in READ_ACTIONS else self._human_writes
            limiter.check_key(actor.user_id)

        if request.method == "POST":
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
        if request.method == "GET" and not is_assistant and parts == ["identity"]:
            return json_response({"user_id": actor.user_id, "issuer": actor.issuer, "subject": actor.subject})
        if len(parts) == 2 and not is_assistant:
            workspace, action = parts
            if request.method == "GET" and action == "overview":
                return json_response(await run_in_threadpool(self.store.overview, identifier(workspace), actor))
            if request.method != "POST" or action not in WORKSPACE_ACTIONS:
                return json_response({"error": "Route unavailable"}, 404)
            operation = getattr(self.store, WORKSPACE_ACTIONS[action])
            args = (identifier(workspace), actor)
        elif len(parts) == 4 and parts[1] == "projects" and request.method == "POST":
            workspace, _, project, action = parts
            if is_assistant and action not in {"context", "propose", "handoffs", "publish-handoff"} or action not in PROJECT_ACTIONS:
                return json_response({"error": "Route unavailable"}, 404)
            operation = getattr(self.store, PROJECT_ACTIONS[action])
            args = (identifier(workspace), identifier(project), actor)
            if action in {"binding", "rotate-binding", "revoke-binding"}:
                if "project" in data:
                    raise ValueError("Unexpected request field")
                data["project"] = args[1]
                args = (args[0], actor)
            if action in {"rotate-binding", "revoke-binding", "retire", "revoke"}:
                keyword = "operation" if action.endswith("-binding") else "state"
                if keyword in data:
                    raise ValueError("Unexpected request field")
                data[keyword] = {"retire": "retired", "revoke": "revoked"}.get(action, action.split("-")[0])
        else:
            return json_response({"error": "Route unavailable"}, 404)

        identifier_fields = IDENTIFIERS | {"subject"} if action == "group-edge" else IDENTIFIERS
        data = {key: identifier(value) if value is not None and key in identifier_fields else value
                for key, value in data.items()}
        try:
            inspect.signature(operation).bind(*args, **data)
        except TypeError as error:
            raise ValueError("Missing or unexpected request fields") from error
        if action in PROOF_ACTIONS:
            with self._slot(self._proof_slots):
                output = await run_in_threadpool(operation, *args, **data)
        else:
            output = await run_in_threadpool(operation, *args, **data)
        if isinstance(output, TaskPacket):
            if output.serialized is None:
                return Response(status_code=204, headers={
                    **HEADERS, "X-Ninai-Outcome": output.outcome, "X-Ninai-Signals": ",".join(output.signals),
                })
            return Response(output.serialized, media_type="application/json", headers=HEADERS)
        return json_response(output)
