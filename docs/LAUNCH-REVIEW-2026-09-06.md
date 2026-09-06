# Ninai MVP launch review — 6 September 2026

## Result

The requested platform admin dashboard is implemented and deployed from merge
commit `3fa7b13`. This review started from public repository commit `d8c9554`.
The public launch scope remains the local Mac MVP for Claude Code and Codex;
the shared hosted connector remains an invited preview.

## Implemented

- Protected `/control/admin` and read-only account overview/list/detail APIs.
- Server-configured platform administrators, distinct from workspace roles.
- Dashboard-client token checks, active-account checks, and automatic admin
  redirect after a successful login.
- Login counts and latest sign-in, with profile email/name from a subject-bound
  Auth0 profile lookup. No credential persistence or local vault collection.
- Signup/download/hosted-connection metrics, account search and pagination,
  detail view, empty/error states, and manual refresh.
- Additive migration, tests, environment example, rollout instructions, and
  account-activity disclosure on the privacy page.
- Designated founder email: `darshan@ninai.io`. General contact: `hello@ninai.io`.
  Published privacy/security addresses should forward to hello.

## Verification

- Engine: 55 tests passed.
- Cloud: 101 tests passed with a disposable PostgreSQL 16 database; no tests
  were skipped. Migration `0008_account_login_activity` was applied and its
  four added columns were verified directly.
- Website production build passed; static website validator passed.
- Admin JavaScript syntax, Python compilation, and diff whitespace checks passed.
- Desktop and 390 px mobile admin layouts were rendered with synthetic account
  data. Overview, search, account detail, and bounded tables remained usable;
  narrow tables use horizontal scrolling.
- Live unauthenticated GET `/control`: HTTP 200.
- Live database readiness GET `/ready`: HTTP 200.
- Source inspection confirms current homepage/install onboarding is consistent.
  An older search-engine snapshot of `/install` was stale; it was not treated
  as the current source.

## Required before declaring unrestricted public launch validation complete

1. Resolve the owner identity: production currently allowlists internal UUID
   `cbce38e7-23a4-4a3d-9049-bd0574ad1588`, whose verified profile displays
   `darshan.t.mn@gmail.com`; the separate `darshan@ninai.io` account has not
   completed a dashboard login. Never substitute email matching for UUID verification.
2. Test real Auth0 signup/sign-in, profile display, installer receipt, admin
   routing, and ordinary-user denial against that deployment.
3. Complete an unrelated tester's fresh Mac installation and Claude Code → Codex handoff with
   provenance and revocation. Existing automated engine tests do not replace
   this release-specific external-user acceptance check.

## Deployment and launch-audit update

- PR 1 was merged; Vercel and Render deployed `3fa7b13` successfully.
- Production `/ready` returns 200 and anonymous admin/download access returns 401.
- A signed-in founder session reached `/control/admin`, and an authenticated
  installer request was recorded.
- A fresh isolated macOS installation completed with Python 3.13, built and
  ad-hoc signed the app, created a local vault, and passed `ninai doctor`.
- The installed application environment occupied approximately 166 MB; the
  empty SQLite vault occupied approximately 106 KB.
- The full cloud suite passed 101 tests against disposable PostgreSQL with zero
  skips, and all 12 cross-provider service-semantic checks passed.
- A fresh operator-run isolated local-vault test passed in both directions
  between Claude Code `2.1.261` and Codex CLI `0.145.0`. It also passed personal
  scope non-disclosure, token budgeting, disclosure logging, immediate Codex
  revocation, and continued Claude access. The engine suite then passed all 56
  tests. This does not substitute for the unrelated tester gate above.
- See [`../report-source.md`](../report-source.md) for the complete launch and
  competitive architecture assessment.

Full operator steps: [PLATFORM-ADMIN.md](PLATFORM-ADMIN.md). The hosted public
launch checklist remains a separate gate; this change does not assert its
unchecked items have passed.
