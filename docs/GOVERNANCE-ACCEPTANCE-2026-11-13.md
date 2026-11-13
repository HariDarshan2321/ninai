# Agent-requested access — 13 November 2026

## What changed

The installed app on this Mac was still version0.1.0 with the expanded permission
matrix. Source changes alone had not updated that executable. The engine and an
initial0.1.2 desktop build were installed with a consistent SQLite recovery
snapshot and private backups of the previous app and runtime. The final reviewed
build is staged; reopening and visual acceptance await the owner unlocking macOS.
Do not confuse that pending native step with browser-fixture tests.

In the new local workflow:

1. An assistant calls `request_project_access` for an existing exact project ID,
   exact Read/Save/Delete actions and a bounded reason. Its client identity comes
   from server configuration, not a request parameter. This grants nothing.
2. The owner reviews the request in Assistants. Cards are collapsed by default;
   existing access stays visible as a compact summary. The inbox shows the exact
   project/action diff, reason and review deadline. Request expiry does not imply
   an expiring grant after approval.
3. Approval invokes fresh macOS LocalAuthentication (Touch ID, Apple Watch or
   account password, depending on OS availability). Ninai does not collect an
   approval password or store a PIN. Cancellation/unavailability grants nothing.
4. A short-lived, single-use in-process capability binds approval to the reviewed
   request, actions and policy revision. SQLite applies the grant atomically only
   if the request and project remain valid. Replay and stale approvals fail.
5. Manual permission increases use the same verified snapshot discipline.
   Already-allowed operations are no-ops, not unverified regrants. Revocation is
   immediate and does not require an authentication prompt.

Ordinary capture heartbeats, timestamps and worktree-location metadata do not
invalidate pending approvals. Automatic capture preserves existing project
names. Real project identity changes and grant/revoke ABA invalidate them.

The native webview now exposes only30 explicit flat bridge functions. It does
not pass the owner object to pywebview's recursive/dotted dispatcher. Raw store
and authority methods cannot be invoked through those payload paths. Verification
tickets and asserted success booleans are never accepted from JavaScript or MCP.

## Verification

- Full engine suite with the actual optional pywebview framework:172 tests passed,
  no skips. It includes installed exporter/dispatcher tests, stale/ABA/no-op,
  wrong-client, replay, expiry, cancellation and atomic exact-action approval.
- Browser suite:25 tests passed, including six approval cases and a real
  synthetic preview bridge that grants exactly Read after simulated verification.
  Preview authentication is explicitly labelled simulated; it is not an OS test.
- Public-page visual checks include the new support page at320/390/768/1440px.
- Cloud suite:144 tests passed with explicit synthetic PostgreSQL15 dump/restore
  rehearsal enabled. That is not production Render PostgreSQL18 recovery proof.
- Local concurrency:5,000 scenarios,16 workers, no surfaced database errors or
  isolation failures. Diagnostic timings are not a production benchmark.
- Actual frozen macOS app upgraded a synthetic prior0.1.0 vault without changing
  memories, provenance, projects, permissions, audit history or capture setting.
- Actual compiled native helper noninteractive `--check` reported available.
  Real owner authentication has not been completed because the Mac is locked.
- Source Mac installer now checks Apple Command Line Tools and packages the
  compiled helper; missing prerequisites fail before replacing the app.

A real Codex MCP access request was created in the owner's local Ninai app for
Read and Save on the Ninai project. No Delete access was requested and no grants
were changed. It remains subject to review, expiry and policy-revision checks;
if it becomes stale, a fresh request is required.

## Boundaries and remaining acceptance

This is local macOS account-owner presence, not an authenticated separate vault
identity or protection against malicious software with unrestricted access as
the same OS user. The owner CLI and Python/database access remain local-owner
administration, not agent self-approval routes. The local database is not
application-encrypted. Restrict assistants to the intended MCP boundary when
using this approval workflow.

This feature is local project access; it does not configure cloud account roles,
provider consent, organization policies or all-agent memory retention rules.
The request tool requires an existing exact project ID, not discovery of private
projects the assistant cannot already identify.

The current native verification helper is macOS-only. Unsupported Windows
approvals fail closed; Windows Hello and real Windows11/UI acceptance remain
release gates. The prepared Windows CI exercises unsigned installation and data
preservation, not trusted signing or OS verification.

No certificate is required to build/test the local development app or to prepare
OpenAI/Anthropic plugin ZIPs. Customer-signed/notarized desktop distribution and
platform directory approvals are separate, unfinished processes.
