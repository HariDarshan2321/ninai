from __future__ import annotations

import re

# High-signal secret patterns. This is a defense-in-depth capture filter, not a
# complete security boundary: it deliberately targets well-known credential
# formats to keep false positives (which would reject legitimate memories) low.
# Generic high-entropy detection is intentionally omitted for that reason.
_SECRET_PATTERNS = [
    # Private key blocks.
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----", re.I),
    # Hyphenated provider keys (OpenAI-style, etc.).
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{20,}\b"),
    # Underscored provider keys (Stripe live/test, etc.).
    re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{10,}\b"),
    # GitHub classic tokens.
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    # GitHub fine-grained personal access tokens.
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
    # Slack tokens.
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    # AWS access key ids.
    re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16}\b"),
    # Google API keys.
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    # JSON Web Tokens (three base64url segments, first begins with eyJ).
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    # Bearer / authorization tokens.
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}=*", re.I),
    # Connection strings that embed a password in the userinfo, e.g.
    # postgres://user:secret@host/db.
    re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/@]+:[^\s:/@]{3,}@"),
    # Credential-shaped assignments (key = value / key: value).
    re.compile(
        r"(?:api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|"
        r"refresh[_-]?token|client[_-]?secret|secret|password|passwd|pwd|token)"
        r"\s*[:=]\s*['\"]?[^\s'\"]{8,}",
        re.I,
    ),
]

_REDACTIONS = [
    (pattern, "[REDACTED_SECRET]") for pattern in _SECRET_PATTERNS
]


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    clean = text
    for pattern, replacement in _REDACTIONS:
        clean = pattern.sub(replacement, clean)
    return clean
