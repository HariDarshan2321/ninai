# Launch acceptance — 14 November 2026

Ninai is not yet accepted as a universally production-ready desktop/cloud
release. Passing automated checks does not establish signed-installer trust,
successful owner authentication, provider directory approval or universal
automatic memory use.

## Completed and verified

- Render deployed application revision
  `83b68b23131e77e8dbb9f50ade7df95bd5b5332e` successfully, deployment
  `dep-dbs9oquc6qcc738j8pn0`, duration 48.4 seconds. Public `/health` reports
  that exact revision and `/ready` succeeds. The service remains on the approved
  paid compute plan; no database subscription or workspace plan was changed.
- Manual deployment temporarily disabled automatic deployment. The setting was
  restored and read back as **After CI Checks Pass**. The service's cloud root
  means a follow-up fix outside that directory may require an explicit tested
  deployment rather than assuming the latest Git push went live.
- Anonymous installer and workspace-data requests return 401. `/mcp` returns
  401 with the advertised protected-resource metadata URL; that URL returns the
  correct MCP resource and authorization server. These are transport/auth
  preflights, not an authenticated account-journey result.
- Native installer regression run
  [43622796836](https://github.com/HariDarshan2321/ninai/actions/runs/43622796836)
  passed on both macOS and Windows for source revision `a5ae57b`. The Mac job
  builds the native helper and app, checks the desktop bridge boundary, and
  launches over the immutable prior-version synthetic vault. Windows builds
  prior/current unsigned packages and exercises installation and data-preserving
  upgrades. Neither artifact is customer-signed or notarized.
- Application CI run
  [43622797284](https://github.com/HariDarshan2321/ninai/actions/runs/43622797284)
  passed engine, website, browser and PostgreSQL 16/18 jobs at `a5ae57b`.
- A real isolated PostgreSQL 18.7 container ran all 144 cloud tests: 143 passed,
  one Node-dependent UI test skipped. That UI test is covered separately by
  application CI. The real dump/restore comparison passed, including changed
  content/provenance detection and read-only enforcement. The container had no
  external network, used only synthetic databases and was removed after exit.
  This is not a live Render backup restore.
- The onboarding regression exposed a real race: Save could run before Create
  project completed. Save now waits visibly for creation and project selection;
  stale project-list responses cannot overwrite newer selections. Completion of
  an older creation does not clear a newly opened draft. Controlled delayed
  responses cover both cases; the existing onboarding suite also passed.
- Privacy and Terms now distinguish optional hosted storage from local storage,
  describe hosted records and deletion limits, and preserve the no-automatic-sync
  boundary. Public Privacy was checked for the corrected cloud description.
  This is a factual implementation correction, not legal compliance acceptance.
- Assistants now puts the permission explanation in a keyboard-accessible
  disclosure and condenses the empty request inbox. Assistant cards appear
  above the fold at 1280×720; advanced controls follow the cards. Seven focused
  governance browser tests passed, including OS-verification failure/retry,
  approval safeguards and 390px overflow checks. Desktop and mobile screenshots
  were reviewed against a disposable synthetic local vault, not the locked
  installed app or a real OS-authentication dialog.
- Once the Mac became available, the final `bb88d2a` development bundle was
  installed and reopened. Its bundled JavaScript/CSS matched source and its
  ad-hoc signature passed verification. A fresh consistent SQLite recovery
  snapshot passed integrity checking; the replaced app was preserved. The actual
  installed Assistants page loaded the compact help/inbox and collapsed cards;
  existing permission summaries remained unchanged. No grants were increased.
- A current capture-quality bug was reproduced with synthetic data and fixed:
  raw text/errors, SQL/query results and generic status/ID responses no longer
  become durable memories. Compact successful decisions and commitments retain
  provenance and project isolation. All 177 engine tests passed with the native
  framework and no skips. Existing records were preserved; historical noise
  requires a separate owner-reviewed cleanup. See the capture-quality report.
- The reported Home-screen issues have separate presentation fixes: the setup
  action has explicit paragraph spacing and one primary action, with progress
  and chapter navigation separated. Legacy tool captures show concise previews;
  explicit captured errors are labelled for review, not presented as successful
  outcomes. Exact stored text and provenance remain available in collapsed
  original details. These changes neither rewrite memories nor change recall
  permissions or retrieval semantics. Focused tests cover keyboard navigation,
  desktop/mobile geometry, original-content equality and literal HTML safety.
  The combined browser suite passed all 33 tests. The rebuilt development app
  also passed the prior-version native upgrade smoke and was installed with a
  fresh integrity-checked recovery snapshot and the previous app preserved.
  The reported spacing and compact capture previews were checked in the actual
  installed app. This does not complete OS-authenticated owner approval.

## Remaining acceptance gates

Follow-up review: CI `43625705610` at `c95774c` passed all jobs. The stale
`/start` and compatibility-page cloud claims were corrected, and compatibility
now explicitly records pending Cursor/VS Code agent acceptance. The Assistants
refresh updates the setup guide's shared connection-status cache. Both Mac build
paths now set package version in the generated spec before signing; the actual
installed About panel was checked as **Version 0.1.2 (0.1.2)**. Local follow-up
checks passed **179 engine tests without skips and 35 browser tests**, plus
the version-aware native upgrade smoke. Authentication migration preparation is
in `AUTH0-PRODUCTION-HANDOFF.md`; no provider, DNS or auth environment was changed.
Follow-up source `5f5986a` passed application CI `43626656402` and both native
installer jobs in `43626656251`. The corrected public pages are live on Vercel.
Render deployment `dep-dbsahuff3r2c73e6r70g` succeeded; `/health` reports the exact
`5f5986a` revision and `/ready` succeeds. No authentication-provider settings,
DNS or subscription were changed in this follow-up.

1. **Real owner verification.** The latest development app is installed and its
   Assistants view was checked. Actual OS-authenticated owner approval still
   requires the owner's participation. Neither the installed-page visual check
   nor a synthetic preview substitutes for that authentication test.
2. **Dedicated cloud account and real assistant journey.** Complete sign-in,
   connect, explicit project grant, save, fresh-session recall, denial,
   revocation, reconnect and upgrade checks using synthetic review content.
   Cursor and VS Code/Copilot authenticated tests remain pending by the user's
   explicit choice. Connection detection alone is not model-use evidence.
3. **Live backup restoration.** Restore to an isolated private PostgreSQL 18
   database, compare a matched source point, and verify cleanup. Creating a
   billable clone needs separate cost approval; the approved $7 web plan does
   not cover it. Never restore over the production database. The settled
   production PITR window observed previously was three days.
4. **Trusted installers and clean-machine upgrades.** Apple Developer ID/
   notarization and Windows signing are unavailable. Native unsigned CI is
   useful evidence, but Windows Hello verification and clean Windows 11 UI/
   upgrade acceptance remain incomplete. Windows approval fails closed.
5. **Public connector listings.** Real branded OpenAI/Anthropic bundles are
   prepared. Owner publishing identity, dedicated reviewer access, all-tool
   acceptance, walkthrough, domain verification, platform attestations and
   external review remain pending. No listing approval or endorsement exists.
6. **Operational data policy.** Confirm legal operator information, actual
   record-retention/purge periods, account-erasure procedure and provider details
   before directory submission. See the hosted disclosure review. Session
   retention settings alone do not execute a scheduled cleanup operation.

Public sharing should describe the currently tested preview honestly until
these release gates are closed. A Git push does not update an existing desktop
installation or install/reload its assistant integration.
