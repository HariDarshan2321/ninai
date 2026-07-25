# Cross-provider release-gate report

## Recorded local host run — 25 July 2026

The core cross-provider and revocation gate passed against the real installed
Claude Code and Codex CLI hosts. This was a local self-hosted PAT run over HTTP;
it does not prove the separate production HTTPS/OAuth deployment checklist.

| Field | Evidence |
| --- | --- |
| Date/time (UTC) | 2026-07-25 17:10–17:13 |
| Git commit | `1aab2c4` |
| Endpoint | `http://127.0.0.1:8000/mcp` |
| Database | PostgreSQL 17, migrations through `0002_personal_access_tokens.sql` |
| Authentication | Explicit self-hosted PAT mode; distinct credentials per client |
| Claude host | Claude Code `2.1.219`, authenticated Team account |
| OpenAI host | Codex CLI `0.145.0`, ChatGPT-authenticated, `gpt-5.6-sol` |
| Workspace/project | One shared generated workspace and project; IDs retained in the local test database |
| Operator | Darshan / Codex implementation run |

Recorded evidence:

- Claude Code called `remember` and created memory `b714e5db-14f2-4b87-8c90-2342e95c91a5` with source `claude-code://acceptance/real-host/1`.
- Codex recalled that exact memory and source, then called `remember` and created memory `e5754c03-0ef9-493b-b511-c49e5e0452ed` with source `codex://acceptance/real-host/2`.
- Claude Code recalled the Codex-created constraint with the exact project scope and source.
- The Codex connection was revoked while its existing PAT remained configured. Its next MCP initialization received `401 invalid_token`; no tool call or memory disclosure occurred.
- Claude Code then recalled the Codex-created memory again. The stored memory and its provenance remained intact.
- Disclosure rows record the successful Codex and Claude recalls with their respective client connections and returned memory IDs.
- The PostgreSQL service-level acceptance harness separately passed all 12 scope, tenant, provenance, audit, round-trip, and revocation-continuity checks.

**Core cross-provider host gate: PASS.**

**Production hosted launch gate: NOT YET PASSED.** HTTPS deployment, external
OAuth/OIDC configuration, restore testing, rate limiting, and production
operations remain outstanding.

Copy this file to a dated report and replace every `PENDING` with command output, IDs, timestamps, screenshots, or log queries. The gate fails if any required row is pending, skipped, or inferred.

`scripts/verify_cross_provider.py` is a useful PostgreSQL service-level prerequisite. Its report intentionally says `host_invocation: not_run`; even a passing result does not satisfy this real Claude/OpenAI host report.

## Run metadata

| Field | Evidence |
| --- | --- |
| Date/time (UTC) | PENDING |
| Git commit | PENDING |
| Deployment URL | PENDING |
| Database/migration version | PENDING |
| OAuth issuer | PENDING |
| Claude host and version | PENDING |
| OpenAI/Codex host, SDK, and model | PENDING |
| Workspace, project, and connection IDs (non-secret) | PENDING |
| Operator | PENDING |

Never paste access tokens, authorization codes, client secrets, or private memory into this report.

## Required sequence

Use a unique marker such as `NINAI_GATE_<timestamp>` and a non-sensitive source URI.

1. Health and discovery: prove `/health`, protected-resource metadata, and OAuth issuer discovery are reachable over HTTPS.
2. Claude write: from the registered Claude connection, call `remember` (or approve a `propose_memory`) with the marker, project scope, source URI, and a unique idempotency key. Record the tool result and memory ID.
3. OpenAI read: from a separately registered Codex or Responses API connection with read grant to the same project, call `recall`. Prove the exact marker, same memory ID, and source URI are returned.
4. OpenAI write: create a second source-backed marker from the OpenAI connection. Record the result and memory ID.
5. Claude read: call `recall` from Claude and prove the OpenAI-authored marker, memory ID, and source URI are returned.
6. Isolation negative: query from a connection without the project grant, or from another workspace. Prove no marker is returned.
7. Disclosure audit: query the control center/database and prove each successful read records the correct workspace, client connection, tool, purpose, returned memory IDs, and timestamp.
8. Immediate revocation: revoke the OpenAI connection while retaining its unexpired token. Repeat its prior read request. Prove HTTP authentication fails or the tool is denied, with no memory returned.
9. Claude continuity: prove revoking OpenAI did not revoke Claude and that Claude can still recall only its granted scopes.
10. Cleanup: revoke temporary grants/connections and soft-delete test memories according to the test environment policy.

## Evidence table

| Gate | Result | Evidence link or exact artifact |
| --- | --- | --- |
| HTTPS health and discovery | PENDING | PENDING |
| Claude → Ninai write | PENDING | PENDING |
| Ninai → OpenAI read with provenance | PENDING | PENDING |
| OpenAI → Ninai write | PENDING | PENDING |
| Ninai → Claude read with provenance | PENDING | PENDING |
| Tenant/scope isolation | PENDING | PENDING |
| Disclosure records | PENDING | PENDING |
| Existing token denied after revocation | PENDING | PENDING |
| Other client remains authorized | PENDING | PENDING |
| Cleanup | PENDING | PENDING |

## Decision

**Release gate: PENDING / FAIL until every required result is PASS.**

Known deviations: PENDING

Operator sign-off: PENDING  
Reviewer sign-off: PENDING
