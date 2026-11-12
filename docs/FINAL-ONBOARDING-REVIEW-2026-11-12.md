# Final onboarding review — 12 November 2026

Decision: the local regression gates pass. Full production approval remains
blocked by the live OAuth/connector journey, signed distribution and operational
evidence below. Do not describe localhost checks as authenticated production use.

## Reproduced failures fixed

- A guide-created decision could be saved without a named project, leaving setup
  permanently waiting. The guide now requires a project and opens creation when
  none exist; ordinary unassigned memories remain supported outside the guide.
- The recall/revocation prompt copied the entire saved decision, bypassing the
  purpose of testing retrieval. It now requests recent allowed project memories
  with an empty query and never embeds the answer.
- A delayed save could close and erase a newer draft. Dialog generations now
  protect newer drafts, including stale project-list responses.
- Modal/drawer keyboard navigation could reach background controls. Background
  controls are inert while a dialog is active, Tab wraps, and Escape restores focus.
- Failed setting changes could receive truthy strings such as `"false"`. Local
  and cloud permission/capture handlers now require real JSON booleans.
- Whitespace-normalized grants could survive an inconsistent revoke. Project
  revocation now normalizes identifiers consistently and rejects invalid targets.
- Concurrent older-database startups could race additive migrations or initial
  WAL setup. Migrations are serialized and lock retry has a shared five-second
  deadline. I/O/corruption errors are surfaced rather than retried indefinitely.
- Failed connector installation could discard a working configuration and old
  app. Installation now restores its prior app/settings on failure, uses atomic
  hook writes, preserves custom memory paths, and refuses unsafe install paths.
- Uninstall could remove another installation's connection. Removal now checks
  exact executable ownership, including quoted/environment-prefixed hooks.
- Narrow pages overflowed in the footer at 320px; install prerequisites touched
  the action buttons. Footer columns and note spacing are corrected.
- Unproven two-/five-minute setup claims and internal customer-facing labels were
  removed. Connection choices show their observable state without equating a
  configuration file to a successful model request.

## Local evidence

| Gate | Result | Boundary |
| --- | --- | --- |
| Engine | 94 tests passed | Includes migration races and isolated installer rollback/uninstall orchestration |
| Cloud | 119 tests passed, zero skips | Disposable real PostgreSQL; includes strict settings, usage, OAuth handler and HTTP-verifier regressions |
| Browser | 11 tests passed | Real desktop API/SQLite; injected transport failures/delays are explicitly synthetic |
| Layout | Eight public pages at 320, 390, 768 and 1440px | Automated overflow, image, heading and install-spacing checks; manual live review also performed |
| Local MCP | 12 checks passed | Actual subprocess transport; no model invocation or editor authentication |
| Local stress | 16 workers, 5,000 scenarios passed | 1,008 writes, 1,008 permitted recalls, 1,000 denied project reads, 992 revocation cycles and 992 denied writes; integrity/audit totals matched |
| Hosted HTTP concurrency | Four lifecycles × two rounds; 48 checks passed; eight fixtures cleaned | Synthetic localhost PAT/SQL traffic, not production OAuth or capacity measurement |
| Website | Typecheck, static build, validator passed; dependency audit zero reported vulnerabilities | Does not establish security certification |
| Render example | Safety policy and official schema validated | Unapplied example; no account, plan, billing, domain or secret changes |

CI now includes the model-free MCP journey, bounded local stress, real PostgreSQL,
and headless browser regressions. Browser traces are retained on failure using
synthetic test data; they are not collected from customers.

## Knowing whether users actually use Ninai

The protected hosted admin dashboard derives activation from an allowed `recall`
that returned at least one memory. It reports activated accounts, distinct active
hosted accounts over seven days, successful recalls over seven days and first
successful recall per account. Empty/denied requests, sign-ins and downloads are
not counted as successful usage. A returned memory does not prove usefulness.
Last memory-request time is derived from actual disclosure records.

Local Mac activity is not uploaded or collected. Offline installation/usage cannot
be inferred from download counts. Use a guided tester's explicit feedback to
understand local success; no silent analytics were added.

## Cloud and release gates still open

- The user agreed to sign into a designated cloud test account. The last observed
  handoff was still at the identity-provider login; successful login, consent,
  real assistant invocation and production revoke/continuity are not claimed.
- The account page now exposes local and separate cloud setup explicitly, with
  instructions and a first-success checklist. Visibility is not proof that every
  host's OAuth flow is compatible.
- The Render example and existing-service checklist are in
  [RENDER-CLOUD-SETUP.md](RENDER-CLOUD-SETUP.md). Confirm actual always-on compute,
  database networking, alert delivery and restore evidence with the owner.
- No Developer ID signing identity was available on this Mac. Signed/notarized
  Mac distribution, signed Windows distribution, real Windows testing and a
  timed independent beginner installation remain incomplete.
- Authenticated Cursor/VS Code invocation remains pending by the user's choice.
- The installed Codex model run previously hit a usage limit before revocation.
  Protocol acceptance is separate evidence and does not erase that gap.

Evidence logs are local temporary files: `/tmp/ninai-final-engine-suite.log`,
`/tmp/ninai-final-cloud-suite.log`, `/tmp/ninai-browser-regressions-2026-11-11.log`,
`/tmp/ninai-final-mcp-journey.log`, and `/tmp/ninai-final-stress.json`.
