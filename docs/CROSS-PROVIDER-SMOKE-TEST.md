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

## Recorded Compose real-host rerun — 25 July 2026

The current Compose service was exercised again with fresh one-day credentials
held in macOS Keychain and injected into temporary host configurations only by
environment-variable reference. Claude Code `2.1.219` (Claude Opus 5) wrote and
recalled memory `99adc906-a5f4-48a6-a492-df840e57ca74`, preserving source
`claude-code://cloud-acceptance/20260725/1`. Codex CLI `0.145.0` using
`gpt-5.6-sol` recalled it, then wrote memory
`add1ba8b-e35e-425e-a08d-edaadb7fa775` with source
`codex://cloud-acceptance/20260725/2`. Claude recalled that exact Codex-authored
memory and source. After live revocation of the already-issued Codex connection,
Codex MCP initialization failed with `401 invalid_token`, while Claude recalled
the Codex-authored memory again. Four successful reads are present in the
workspace disclosure log. The Claude connection was then revoked, both temporary
credentials were removed from macOS Keychain, and the token-free temporary host
configuration was deleted.

**Current Compose real-host and revocation gate: PASS.** This was still operated
by the implementation team over loopback HTTP/PAT and is not independent-user,
production OAuth, or durable public-deployment evidence.

## Recorded ephemeral HTTPS transport run — 25 July 2026

The current `main` container was exposed temporarily through an account-less
Cloudflare Quick Tunnel using fresh one-day PATs. This run proves the remote MCP
transport, public TLS endpoint, resource metadata, authenticated bidirectional
memory flow, and live connection revocation. The tunnel was stopped after the
run and is not a durable deployment.

| Field | Evidence |
| --- | --- |
| Git commit | `08586ce` plus the Compose public-resource override recorded in the next commit |
| Container | Non-root UID/GID `10001:10001`; automatic migrations through `0003_memory_lifecycle.sql`; healthy |
| Transport | Public Cloudflare HTTPS tunnel to the loopback-only Compose service |
| Authentication | Fresh explicit PAT-mode staging connections expiring after one day |
| Discovery | `/health` returned `200`; protected-resource metadata advertised the exact HTTPS `/mcp` resource |
| Challenge | Unauthenticated MCP initialization returned `401` with matching `resource_metadata` |
| Tools | `fetch`, `propose_memory`, `recall`, `remember`, and `search` listed over HTTPS |
| Round trip | Claude-labelled connection wrote; OpenAI-labelled connection recalled with exact source; OpenAI wrote; Claude recalled with exact source |
| Revocation | The already-issued OpenAI PAT returned HTTP `401` after its connection was revoked |
| Continuity | The Claude connection still recalled the OpenAI-authored memory after OpenAI revocation |

**Ephemeral HTTPS/PAT transport gate: PASS.** This is stronger transport
evidence than the loopback run, but it deliberately does not claim production
OAuth, durable hosting, independent tester completion, or production operations.

**Production hosted launch gate: NOT YET PASSED.** HTTPS deployment, external
OAuth/OIDC configuration, restore testing, rate limiting, and production
operations remain outstanding.

Copy this file to a dated report and replace every `PENDING` with command output, IDs, timestamps, screenshots, or log queries. The gate fails if any required row is pending, skipped, or inferred.

`scripts/verify_cross_provider.py` is a useful PostgreSQL service-level prerequisite. Its report intentionally says `host_invocation: not_run`; even a passing result does not satisfy this real Claude/OpenAI host report.

Use `scripts/prepare_external_tester_acceptance.py --endpoint https://<host>` to
preflight a release endpoint and generate a uniquely marked independent-tester
report. The generator deliberately leaves the release decision at PENDING/FAIL;
only an actual non-operator tester can complete and sign it. A loopback rehearsal
requires `--allow-http-local` and is labelled ineligible as release evidence.

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
