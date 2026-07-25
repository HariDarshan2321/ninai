#!/usr/bin/env python3
"""Preflight a deployment and print an honest external-tester report template."""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ninai-external-gate/1"})
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _version(command: str) -> str:
    try:
        result = subprocess.run(
            [command, "--version"], check=True, capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "NOT INSTALLED"
    return (result.stdout or result.stderr).strip().splitlines()[0]


def _commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "UNKNOWN"
    return result.stdout.strip()


def prepare(endpoint: str, *, allow_http_local: bool = False) -> str:
    base = endpoint.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    is_local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme != "https" and not (allow_http_local and is_local_http):
        raise ValueError("external acceptance requires HTTPS; use --allow-http-local only for rehearsal")

    health = _get_json(f"{base}/health")
    resource_url = f"{base}/mcp"
    metadata_url = f"{base}/.well-known/oauth-protected-resource/mcp"
    metadata = _get_json(metadata_url)
    health_ok = health.get("status") == "ok"
    metadata_ok = metadata.get("resource") == resource_url
    preflight_passed = health_ok and metadata_ok
    marker = f"NINAI_EXTERNAL_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    transport = "LOCAL HTTP REHEARSAL — NOT RELEASE EVIDENCE" if is_local_http else "HTTPS"

    return f"""# Ninai external-tester acceptance report

Generated: {datetime.now(timezone.utc).isoformat()}

This report is intentionally **PENDING**. The generator validates public discovery only. It cannot
replace an independent human using real Claude and OpenAI hosts, and it never accepts or records tokens.

## Preflight

| Field | Evidence |
| --- | --- |
| Endpoint | `{base}` |
| Transport | {transport} |
| Git commit | `{_commit()}` |
| Health | {'PASS' if health_ok else 'FAIL'} — `{json.dumps(health, sort_keys=True)}` |
| Protected-resource metadata | {'PASS' if metadata_ok else 'FAIL'} — resource `{metadata.get('resource', 'MISSING')}` |
| Claude host | `{_version('claude')}` |
| OpenAI host | `{_version('codex')}` |
| Non-sensitive marker | `{marker}` |
| Preflight decision | {'PASS' if preflight_passed else 'FAIL'} |

## Independent tester requirements

- [ ] Tester name or stable pseudonym recorded below.
- [ ] Tester confirms they are not the implementation operator and did not receive database access.
- [ ] Operator provisions distinct, short-lived, least-privilege Claude and OpenAI connections.
- [ ] Credentials are transferred out-of-band and never pasted into this report, chat, or source control.
- [ ] Tester configures their own installed Claude and OpenAI hosts against `{resource_url}`.
- [ ] Claude stores `{marker}_CLAUDE` with a non-sensitive `source_uri`; memory ID and source recorded.
- [ ] OpenAI recalls that exact memory and source, then stores `{marker}_OPENAI` with its own source.
- [ ] Claude recalls the OpenAI-authored memory with the exact memory ID, project scope, and source.
- [ ] An ungranted client returns neither marker.
- [ ] Operator confirms disclosure rows for each successful read without exposing private content.
- [ ] Operator revokes the already-issued OpenAI connection; the tester observes authentication denial.
- [ ] Claude remains able to recall only its granted project after OpenAI revocation.
- [ ] Operator revokes all temporary connections and applies the test-environment deletion policy.

## Evidence

| Gate | Result | Exact artifact, timestamp, or redacted log reference |
| --- | --- | --- |
| Independent tester identity/eligibility | PENDING | PENDING |
| Claude → Ninai write | PENDING | PENDING |
| Ninai → OpenAI read with provenance | PENDING | PENDING |
| OpenAI → Ninai write | PENDING | PENDING |
| Ninai → Claude read with provenance | PENDING | PENDING |
| Scope isolation | PENDING | PENDING |
| Disclosure audit | PENDING | PENDING |
| Existing OpenAI token denied after revocation | PENDING | PENDING |
| Claude continuity | PENDING | PENDING |
| Cleanup | PENDING | PENDING |

## Attestation

Tester: PENDING  
Tester sign-off and UTC timestamp: PENDING  
Operator sign-off and UTC timestamp: PENDING

**External-tester release gate: PENDING / FAIL until every checkbox and evidence row is complete.**
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="Deployment origin, without /mcp")
    parser.add_argument("--output", type=Path, help="Write the report here instead of stdout")
    parser.add_argument(
        "--allow-http-local", action="store_true",
        help="Permit a loopback rehearsal; the report remains ineligible as release evidence",
    )
    args = parser.parse_args()
    try:
        report = prepare(args.endpoint, allow_http_local=args.allow_http_local)
    except (ValueError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
