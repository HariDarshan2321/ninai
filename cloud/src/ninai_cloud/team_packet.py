"""Project already authorized team decisions into bounded task context.

The caller supplies only workspace-, project- and visibility-authorized rows
and checks source authorization and freshness at the release transaction. The
caller revalidates live grants and commits a release audit before returning
``serialized``. A truncated candidate set cannot establish lack of conflict.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import json
import re
from typing import Any


MAX_PACKET_ITEMS = 24
MAX_PACKET_TOKENS = 4096
DEFAULT_PACKET_ITEMS = 6
DEFAULT_PACKET_TOKENS = 1200
_HISTORICAL_STATES = frozenset({"replaced", "expired", "retired", "revoked"})


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    CHANGED = "changed"
    UNAVAILABLE = "unavailable"
    PERMISSION_DENIED = "permission-denied"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceEvidence:
    source_id: str
    status: EvidenceStatus
    required: bool = True
    source_uri: str | None = None


@dataclass(frozen=True)
class DecisionVersion:
    version_id: str
    decision_id: str
    version: int
    topic: str
    rule: str
    rationale: str | None
    status: str
    sources: tuple[SourceEvidence, ...]
    scope_paths: tuple[str, ...] = ()
    scope_terms: tuple[str, ...] = ()
    expires_at: datetime | None = None
    replaces_version_id: str | None = None


@dataclass(frozen=True)
class TaskContext:
    task: str
    repo_paths: tuple[str, ...] = ()
    project_overview: bool = False


@dataclass(frozen=True)
class TaskPacket:
    outcome: str
    payload: dict[str, Any] | None
    serialized: bytes | None
    released_versions: tuple[str, ...]
    signals: tuple[str, ...]


def _words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", text.casefold()))


def _repo_path(value: str) -> tuple[str, tuple[str, ...]] | None:
    repo, separator, path = value.partition(":")
    parts = tuple(path.rstrip("/").split("/"))
    if not repo or not separator or "\\" in value or any(part in ("", ".", "..") for part in parts):
        return None
    return repo, parts


def _relevance(
    version: DecisionVersion,
    task_phrase: str,
    requested_paths: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[int, int, int] | None:
    path_matches = [
        (len(prefix), len(requested_paths) - index)
        for scope in version.scope_paths
        if (parsed := _repo_path(scope)) is not None
        for repo, prefix in (parsed,)
        for index, (requested_repo, path) in enumerate(requested_paths)
        if repo == requested_repo and path[:len(prefix)] == prefix
    ]
    if version.scope_paths and not path_matches:
        return None

    terms = {" ".join(_words(term)) for term in version.scope_terms}
    matching_terms = sum(bool(term) and f" {term} " in task_phrase for term in terms)
    if version.scope_terms and not matching_terms:
        return None
    if not path_matches and not matching_terms:
        # Unscoped decisions need a meaningful exact topic match. Scope terms
        # are the place to enumerate synonyms without turning overlap into an
        # implicit topic or allowing source text to influence matching.
        topic_words = _words(version.topic)
        if not topic_words or f" {' '.join(topic_words)} " not in task_phrase:
            return None
    specificity, priority = max(path_matches, default=(0, 0))
    return specificity, matching_terms, priority


def _selectors(context: TaskContext) -> tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]:
    task_phrase = f" {' '.join(_words(context.task))} "
    requested_paths = tuple(path for value in context.repo_paths if (path := _repo_path(value)) is not None)
    return task_phrase, requested_paths


def matches_task(context: TaskContext, version: DecisionVersion) -> bool:
    """Screen task selectors before obtaining per-source evidence."""
    return context.project_overview or _relevance(version, *_selectors(context)) is not None


def _is_verified(source: SourceEvidence) -> bool:
    return source.status == EvidenceStatus.VERIFIED and bool(source.source_id and source.source_uri)


def _evidence_state(version: DecisionVersion) -> str:
    required = tuple(source for source in version.sources if source.required)
    if not required:
        return "hidden"
    if all(_is_verified(source) for source in required):
        return "verified"
    if all(_is_verified(source) or source.status in (EvidenceStatus.CHANGED, EvidenceStatus.UNAVAILABLE)
           for source in required):
        # CHANGED and UNAVAILABLE require independent positive authorization
        # to know the reference exists. The broker must use UNKNOWN otherwise.
        return "unverified"
    return "hidden"


def _decision(version: DecisionVersion, *, include_scope: bool) -> dict[str, Any]:
    rationale = version.rationale if version.rationale and version.rationale.strip() else None
    result = {
        "version_id": version.version_id,
        "decision_id": version.decision_id,
        "version": version.version,
        "rule": version.rule,
        "rationale_status": "documented" if rationale is not None else "undocumented",
        "rationale": rationale,
        "sources": [
            {"id": source.source_id, "uri": source.source_uri}
            for source in sorted(version.sources, key=lambda source: source.source_id)
            if _is_verified(source)
        ],
    }
    if include_scope:
        result.update(topic=version.topic, scope_paths=list(version.scope_paths), scope_terms=list(version.scope_terms))
    return result


def _json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _packet(
    outcome: str,
    signals: tuple[str, ...],
    token_cap: int,
    *,
    category: str | None = None,
    versions: Iterable[DecisionVersion] = (),
    lineage: dict[str, str] | None = None,
    include_scope: bool = False,
) -> TaskPacket:
    selected = tuple(versions)
    payload: dict[str, Any] = {"outcome": outcome}
    if signals:
        payload["signals"] = list(signals)
    if category is not None and selected:
        payload[category] = [_decision(version, include_scope=include_scope) for version in selected]
    if lineage:
        payload["lineage"] = [{"current": current, "replaces": replaces} for current, replaces in lineage.items()]

    serialized = _json(payload)
    # Count the complete UTF-8 context envelope at one token per byte. This
    # deliberately conservative byte-level budget avoids tokenizer drift and
    # keeps punctuation, Unicode and JSON escapes inside the advertised cap.
    if len(serialized) > token_cap:
        return TaskPacket(outcome, None, None, (), signals)
    version_ids = tuple(version.version_id for version in selected)
    predecessor_ids = tuple(lineage.values()) if lineage else ()
    return TaskPacket(outcome, payload, serialized, version_ids + predecessor_ids, signals)


def _fit_versions(
    ranked: list[DecisionVersion],
    *,
    outcome: str,
    category: str,
    signals: tuple[str, ...],
    lineage: dict[str, str],
    max_items: int,
    max_tokens: int,
    include_scope: bool = False,
) -> TaskPacket:
    included: list[DecisionVersion] = []
    for version in ranked:
        if len(included) == max_items:
            break
        attempt = _packet(outcome, signals, max_tokens, category=category, versions=(*included, version),
                          include_scope=include_scope)
        if attempt.serialized is not None:
            included.append(version)
    if not included:
        return _packet("empty", ("budget-exhausted",), max_tokens)

    # Historical IDs are optional metadata and cannot evict current guidance.
    # Count them as released decision items as well.
    edges: dict[str, str] = {}
    for version in included:
        predecessor = lineage.get(version.version_id)
        if predecessor is None or len(included) + len(edges) == max_items:
            continue
        attempt = _packet(outcome, signals, max_tokens, category=category, versions=included,
                          lineage={**edges, version.version_id: predecessor}, include_scope=include_scope)
        if attempt.serialized is not None:
            edges[version.version_id] = predecessor
    return _packet(outcome, signals, max_tokens, category=category, versions=included, lineage=edges,
                   include_scope=include_scope)


def compose_task_packet(
    context: TaskContext,
    versions: Iterable[DecisionVersion],
    *,
    now: datetime,
    max_items: int = DEFAULT_PACKET_ITEMS,
    max_tokens: int = DEFAULT_PACKET_TOKENS,
    can_view_history: bool = False,
    history_only: bool = False,
) -> TaskPacket:
    """Return a current, history, conflict, abstention or empty projection."""
    if type(max_items) is not int or not 1 <= max_items <= MAX_PACKET_ITEMS:
        raise ValueError(f"max_items must be between 1 and {MAX_PACKET_ITEMS}")
    if type(max_tokens) is not int or not 1 <= max_tokens <= MAX_PACKET_TOKENS:
        raise ValueError(f"max_tokens must be between 1 and {MAX_PACKET_TOKENS}")
    if now.utcoffset() is None:
        raise ValueError("release time must be timezone-aware")
    if history_only and not can_view_history:
        return _packet("denied", (), max_tokens)

    selectors = _selectors(context)
    current: dict[str, list[DecisionVersion]] = {}
    historic: dict[str, DecisionVersion] = {}
    unverified_topics: set[str] = set()
    relevance: dict[str, tuple[int, int, int]] = {}
    for version in versions:
        rank = (0, 0, 0) if context.project_overview else _relevance(version, *selectors)
        if rank is None:
            continue
        expires_at = version.expires_at
        if expires_at is not None and expires_at.utcoffset() is None:
            # A malformed clock value cannot prove this version is live.
            continue
        status = version.status
        if status == "approved" and expires_at is not None and expires_at <= now:
            status = "expired"
        if status != "approved" and (not can_view_history or status not in _HISTORICAL_STATES):
            continue
        if history_only and status == "approved":
            continue

        evidence = _evidence_state(version)
        topic = " ".join(_words(version.topic))
        if not topic or evidence == "hidden":
            continue
        if evidence == "unverified":
            if history_only or status == "approved":
                unverified_topics.add(topic)
            continue
        relevance[version.version_id] = rank
        if status == "approved":
            current.setdefault(topic, []).append(version)
        else:
            historic[version.version_id] = version

    def sort_key(version: DecisionVersion) -> tuple[int, int, int, str]:
        depth, terms, priority = relevance[version.version_id]
        return -depth, -terms, -priority, version.version_id

    if history_only and historic:
        return _fit_versions(sorted(historic.values(), key=sort_key), outcome="history", category="history",
                             signals=(), lineage={}, max_items=max_items, max_tokens=max_tokens)

    conflicting = [
        version for contenders in current.values()
        if len({contender.rule for contender in contenders}) > 1
        for version in contenders
    ]
    if conflicting:
        signals = ("resolve-before-edit",)
        if len(conflicting) <= max_items:
            packet = _packet("conflict", signals, max_tokens, category="conflicting",
                             versions=sorted(conflicting, key=sort_key), include_scope=context.project_overview)
            if packet.serialized is not None:
                return packet
        # An unresolved conflict stays a conflict. Never elevate a contender
        # into current guidance merely because all alternatives do not fit.
        return _packet("conflict", (*signals, "budget-exhausted"), max_tokens)

    ranked = sorted((version for topic, contenders in current.items() if topic not in unverified_topics
                     for version in contenders), key=sort_key)
    if ranked:
        lineage = {
            version.version_id: predecessor.version_id
            for version in ranked
            if (predecessor := historic.get(version.replaces_version_id or "")) is not None
            and predecessor.status == "replaced"
            and _words(predecessor.topic) == _words(version.topic)
        }
        signals = ("evidence-unverified",) if unverified_topics else ()
        return _fit_versions(ranked, outcome="packet", category="current", signals=signals, lineage=lineage,
                             max_items=max_items, max_tokens=max_tokens, include_scope=context.project_overview)

    if unverified_topics:
        return _packet("abstain", ("evidence-unverified",), max_tokens)
    return _packet("empty", (), max_tokens)
