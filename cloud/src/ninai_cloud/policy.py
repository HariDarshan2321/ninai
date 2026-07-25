"""Conservative, server-owned policy for hosted memory writes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class MemoryType(str, Enum):
    COMMITMENT = "commitment"
    CONSTRAINT = "constraint"
    DECISION = "decision"
    EVENT = "event"
    FACT = "fact"
    PREFERENCE = "preference"
    PROCEDURE = "procedure"
    PROJECT_STATE = "project_state"


ALLOWED_MEMORY_TYPES = frozenset(item.value for item in MemoryType)


class WriteDisposition(str, Enum):
    ACTIVE = "active"
    PROPOSED = "proposed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class WritePolicyDecision:
    disposition: WriteDisposition
    risk_level: str
    reasons: tuple[str, ...]

    @property
    def allows_auto_activation(self) -> bool:
        return self.disposition is WriteDisposition.ACTIVE


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("secret_or_credential", re.compile(
        r"\b(?:secret|credential|private key|api key|access token|refresh token|password)\b", re.I)),
    ("permission_change", re.compile(
        r"\b(?:grant|revoke|authorize|permission|access rights?|role|admin|owner)\b", re.I)),
    ("delete_or_forget", re.compile(
        r"\b(?:delete|erase|forget|purge|destroy|irreversible|remove permanently)\b", re.I)),
    ("legal_commitment", re.compile(
        r"\b(?:contract|legal|lawsuit|liability|indemnif|terms of service|nda|sign(?:ed|ing)? agreement)\b", re.I)),
    ("financial_commitment", re.compile(
        r"(?:[$€£]\s?\d|\b(?:pay|purchase|invoice|budget|price|salary|bank|tax|financial|refund|subscribe)\b)", re.I)),
    ("company_wide_policy", re.compile(
        r"\b(?:company[- ]wide|organization[- ]wide|org[- ]wide|all employees|corporate policy)\b", re.I)),
    ("inferred_sensitive_information", re.compile(
        r"\b(?:diagnos(?:is|ed)|medical condition|health condition|sexual orientation|religion|ethnicity|political affiliation)\b",
        re.I)),
)
_AMBIGUOUS = re.compile(
    r"(?:\?|\b(?:maybe|perhaps|probably|possibly|might|could be|I think|I guess|apparently|"
    r"someone|something|somewhere|they said|it seems|unclear|unknown|TBD|to be determined)\b)", re.I)


def validate_memory_type(memory_type: str) -> str:
    if not isinstance(memory_type, str) or memory_type not in ALLOWED_MEMORY_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MEMORY_TYPES))
        raise ValueError(f"Unsupported memory type: {memory_type!r}; expected one of: {allowed}")
    return memory_type


def _source_is_attached(source_uri: str) -> bool:
    if not isinstance(source_uri, str) or not source_uri.strip():
        return False
    parsed = urlparse(source_uri.strip())
    return bool(parsed.scheme and (parsed.netloc or parsed.path)) and parsed.scheme.lower() not in {
        "unknown", "none", "model", "inference",
    }


def classify_write(*, content: str, memory_type: str, scope_kind: str, scope_id: str,
                   source_uri: str, requested_auto: bool, contains_secret: bool = False,
                   has_active_conflict: bool = False) -> WritePolicyDecision:
    """Apply policy without accepting client-supplied risk or safety overrides."""
    validate_memory_type(memory_type)
    if contains_secret:
        return WritePolicyDecision(WriteDisposition.REJECTED, "blocked", ("secret_or_credential",))

    reasons = [reason for reason, pattern in _RULES if pattern.search(content)]
    if _AMBIGUOUS.search(content) or len(content.split()) < 3:
        reasons.append("ambiguous_statement")
    if scope_kind not in {"workspace", "project", "user"} or not str(scope_id).strip():
        reasons.append("ambiguous_scope")
    if not _source_is_attached(source_uri):
        reasons.append("missing_authoritative_source")
    if has_active_conflict:
        reasons.append("active_conflict")
    reasons = list(dict.fromkeys(reasons))

    if not requested_auto:
        return WritePolicyDecision(WriteDisposition.PROPOSED, "high" if reasons else "low",
                                   tuple(reasons or ["review_mode_default"]))
    if reasons:
        return WritePolicyDecision(WriteDisposition.PROPOSED, "high", tuple(reasons))
    return WritePolicyDecision(WriteDisposition.ACTIVE, "low", ("eligible_for_auto_activation",))


__all__ = ["ALLOWED_MEMORY_TYPES", "MemoryType", "WriteDisposition", "WritePolicyDecision",
           "classify_write", "validate_memory_type"]
