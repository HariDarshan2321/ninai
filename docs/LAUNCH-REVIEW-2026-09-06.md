# Ninai MVP launch review — 6 September 2026

## Result

The requested platform admin dashboard is implemented in this change. It is
not deployed. This review started from public repository commit `d8c9554`.
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

## Required before declaring this release live

1. Publish the review branch through authenticated GitHub access. This session's
   read-only clone succeeded; push dry-run failed because GitHub credentials
   were unavailable. No remote branch, PR, or deployment was created.
2. Deploy the account service and privacy-page change. Enable only Darshan's
   verified internal account UUID with `NINAI_PLATFORM_ADMIN_USER_IDS`.
3. Test real Auth0 signup/sign-in, profile display, installer receipt, admin
   routing, and ordinary-user denial against that deployment.
4. Complete a fresh Mac installation and Claude Code → Codex handoff with
   provenance and revocation. Existing automated engine tests do not replace
   this release-specific external-user acceptance check.

Full operator steps: [PLATFORM-ADMIN.md](PLATFORM-ADMIN.md). The hosted public
launch checklist remains a separate gate; this change does not assert its
unchecked items have passed.
