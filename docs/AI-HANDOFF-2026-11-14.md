# Ninai handoff — 14 November 2026

## Follow-up to the external review

Verified source revision **`5f5986a`**: application CI **43626656402** passed all
jobs; the corrected `/start` and `/compatibility` pages are live on Vercel.
Native installer run **43626656251** passed macOS; Windows was still building
the current unsigned package at the last check. Render still reported `83b68b2`
while waiting for checks. Confirm that native run and the subsequent cloud
rollout before calling the updated hosted installer deployed. The actual owner
app was replaced with the version-corrected build, reopened, and its native About
panel verified as **Version 0.1.2 (0.1.2)**. Its prior bundle and fresh consistent
vault snapshot were preserved; the installed Python runtime was updated too.

CI run **43625705610** at `c95774c` passed, resolving the old 390px
fractional-spacing failure. Subsequent review fixes in this checkout:

- `/start` describes separate local and optional hosted memory rather than
  incorrectly claiming hosted storage is unavailable.
- Assistants refreshes the connection-status cache used by the Home guide;
  a browser regression exercises a changed status across the two views.
- Both Mac build paths set bundle metadata from engine version **before**
  PyInstaller signs the app. Native short/build versions are now `0.1.2`, not
  PyInstaller's default `0.0.0`. Upgrade smoke also checks the actual plist.
- Local checks after these changes: **179 engine tests passed without skips;
  35 browser tests passed**. Website build and validation passed, and the rebuilt
  native app's version/signature were checked. Record installation/remote CI
  separately; a local build is not evidence of a deployed update.
- `docs/AUTH0-PRODUCTION-HANDOFF.md` prepares owned Google credentials first
  and a separate optional domain migration. No external auth/DNS settings or
  billing were changed. Do not equate missing application encryption with an
  unverified claim that infrastructure has no at-rest encryption.

These changes include the hosted installer asset, so **verify a fresh Render
deployment after CI**. The older statement that no cloud files changed after
`83b68b2` no longer applies once this follow-up is pushed. Treat the earlier
commit references below as historical evidence; check current HEAD/run first.

## Start here

The owner explicitly requested a handoff to another AI session. Finish the listed
acceptance gates; do not restart discovery or broaden into another redesign.
Read `AGENTS.md`, `docs/LAUNCH-ACCEPTANCE-2026-11-14.md`, and this file first.
Review the current working tree before editing and preserve any new owner work.

Repository: `/Users/darshanthevarmahalingam/src/ninai-pat`, branch `main`.
The initial desktop working directory is not the repository. Remote:
`https://github.com/HariDarshan2321/ninai`. All implementation through `2103e38`
was pushed. This handoff adds only a browser-test rounding correction and docs.
Check current HEAD and its CI before making any readiness claim.

Meeting: Monday **16 November 2026, 15:00–15:30 CET**, with Vanessa and Eugene;
the owner supplied the email confirming booking and a calendar invite. No email
or calendar action was requested or performed. Present tested capabilities and
remaining limits honestly. Never send messages to these contacts without an
explicit request.

## What actually changed

- Local governance requests let an agent propose exact project/actions and wait
  for owner review. Agents have no approve/verify tools. Fresh OS verification,
  single-use approval capability, expiry and policy revision checks protect
  increasing grants. Revocation is immediate. The desktop bridge exposes an
  explicit flat whitelist rather than a recursively reachable store object.
- Assistants cards collapse by default. Long permission help is a disclosure;
  empty access requests are compact and advanced controls follow the cards.
- Setup no longer saves before asynchronous project creation finishes. Stale
  project-list responses and older request completion cannot overwrite newer
  selections/drafts.
- The owner's screenshots exposed cramped guide spacing and competing orange
  buttons. The guide now has shorter instructions, access details on demand,
  explicit paragraph/action spacing, one primary action and separate secondary
  progress/navigation controls with responsive alignment.
- A real capture bug promoted raw error text and query rows into memories. New
  capture rejects explicit failures, raw prose, SQL/query outputs and generic
  status/ID-only results. Compact structured decisions/commitments remain
  supported with provenance and project isolation.
- Existing captured records were preserved. Cards now show compact neutral
  previews or **Captured tool error** for explicit legacy failures, with exact
  original content in collapsed drawer details and full provenance. Home cards
  open by keyboard. No historical cleanup or retrieval semantics changed.
- Privacy/Terms now accurately distinguish opt-in hosted PostgreSQL from local
  SQLite, with no automatic local upload/sync. Factual disclosures were corrected;
  legal operator and retention/erasure policy decisions are still unresolved.
- Real Ninai-branded OpenAI/Anthropic packages are prepared; they have not been
  submitted, listed, approved or endorsed by either platform.

## Installed app and safety copies

The actual owner app was updated, reopened and visually checked, not just a
browser mock. Its path is:

`/Users/darshanthevarmahalingam/.ninai-app/Ninai.app`

It is development version 0.1.2, ad-hoc signed, **not** customer-signed/notarized.
Its JavaScript/CSS matched the final UI source at `2103e38`. The installed runtime
at `~/.ninai-app/venv` was also rebuilt/reinstalled without dependencies and its
capture code and UI assets checked byte-for-byte against source.

Owner data is `~/.ninai/ninai.sqlite3`. Consistent private recovery snapshots
were integrity-checked before replacement. Previous bundles are preserved under
`~/.ninai-app/recovery/`, most recently `before-ui-fixes-20261114/Ninai.app`.
Private local metadata `/tmp/ninai-local-upgrade.json` records exact snapshots
and replacement paths. Never restore a snapshot over newer writes or delete
these recovery copies automatically. No permission increases or memory deletion
were performed during update.

The installed app's bundled native helper passed its noninteractive availability
check. Real Touch ID/macOS-password owner approval remains **unverified**. A bare
Python wheel/runtime lacks the compiled helper; use the actual bundled app for
native approval acceptance. Do not add an authentication bypass or expose the
verifier as an agent tool. The trust boundary is the current OS-account owner,
not protection against malicious same-user filesystem/CLI access. SQLite is not
application-encrypted. Windows verification currently fails closed.

## Test evidence and CI caveat

- Full engine suite: **177 passed, no skips**, with real optional desktop
  framework in `/tmp/ninai-governance-native-build/venv`; see
  `/tmp/ninai-capture-quality-engine-native.log`.
- Combined local browser suite after the screenshot fixes: **33 passed**;
  `/tmp/ninai-readiness-20261114/screenshot-fixes-browser.log`.
- Prior-version frozen Mac app startup/data-preservation smoke passed after the
  final UI build; `screenshot-fixes-upgrade.json` in the same evidence folder.
- Native CI **43622796836** passed macOS and Windows at `a5ae57b`. Windows tests
  unsigned install/upgrade on Windows Server 2022, not clean Windows 11 UI,
  signing trust or Windows Hello. Mac CI uses supported macOS 15 and full git
  history for the immutable 0.1.0 fixture.
- A no-external-network PostgreSQL **18.7** container ran 144 cloud tests:
  143 passed, one Node-dependent UI test skipped (covered separately by CI).
  The real synthetic dump/restore comparison passed. The container was removed.
  This is not a production Render backup restoration.
- CI **43624520152** passed all jobs at `dd9ded8`.
- CI **43625309065** at `2103e38` passed engine, website, PostgreSQL 16 and 18;
  browser had **32 passed, one failure**: a nominal 16px mobile footer gap was
  measured as 15.896px on Linux. The handoff commit changes only that geometric
  assertion to allow 0.5px fractional rendering tolerance. Product CSS remains
  16px; do not treat the old run as green. Check the new commit's CI first.

Useful commands:

```sh
git status --short
gh run list --workflow test.yml --limit 3
gh run view RUN_ID --json status,conclusion,jobs
cd website
npm run test:e2e
```

The browser suite starts a disposable synthetic local desktop API on 58045 and
serves built website files on 3034. Run `npm run build` if website source changed.
Do not run simultaneous suites against the same ports. `engine/.venv` has no pip;
the native build venv has pip and the optional desktop framework.

Temporary visual evidence in `/tmp/ninai-readiness-20261114/` includes
`home-fixed.jpg`, `memory-detail-fixed.jpg`, `installed-home-fixed.png`,
`installed-memory-fixed.png`, and `render-live.jpg`. Native screenshots can
contain owner metadata: do not commit or publish them. Synthetic preview servers
were stopped and preview tabs closed. The Render receipt tab may remain open.

## Live Render facts and authorization

- Web service `srv-d9iganjeo5us739to4l0`, Frankfurt, root directory `cloud`.
- The owner explicitly approved **$7/month web compute**. It is on paid
  0.5c-512mb compute, one instance. No database/workspace plan was upgraded.
- Tested cloud revision `83b68b23131e77e8dbb9f50ade7df95bd5b5332e` was deployed
  successfully as `dep-dbs9oquc6qcc738j8pn0`, duration 48.4 seconds. Later commits
  change local engine/UI/tests/docs; do not assume health must equal main HEAD.
- `https://app.ninai.io/health` reports that revision; `/ready` succeeds.
  Anonymous installer/workspace/MCP requests return 401. The MCP challenge
  advertises `/.well-known/oauth-protected-resource/mcp`, which returns the
  correct resource/auth server. These do not prove authenticated acceptance.
- Manual specific-commit deployment disabled auto-deploy temporarily; restored
  and read back as **After CI Checks Pass**. A fix outside the cloud root may
  not retrigger a failed cloud-path commit: verify the actual deployed revision.
- DB `dpg-d9ig79jrjlhs73eulokg-a`, PostgreSQL 18, private external access disabled.
  Previously observed plan: Basic 256MB, $6/month compute, 1GB allocated. Settled
  recovery UI showed **three-day PITR**, not seven. Recheck if needed.
- An isolated restore clone can add a charge. **That cost is not authorized by
  the web-plan approval.** Prepare a concrete quote and ask before creating it.
  Never restore over production or open the DB publicly for convenience.

Render dashboard access was owner-authenticated in the in-app browser. Reuse
available authorized sessions; do not ask for credentials in chat. If computer
use is needed in a fresh session, read its current documentation first. Do not
bypass OS locks, OS verification or security warnings.

## Finish these gates in order

1. Confirm CI for this handoff commit. Investigate actual failures; do not rerun
   blindly or weaken functional assertions to obtain a green check.
2. With the owner present, test actual app verification, cancellation/retry and
   exact-action approval. Use a clearly identified synthetic test project. Get
   action-specific approval before increasing access; agents never self-approve.
3. Complete a dedicated cloud review account journey: login, connection, explicit
   project grant, save, fresh-session recall, denial/revocation, reconnect and
   upgrade. A URL-only connection does not install a continuity skill; model
   tool presence is not proof of automatic use. Cursor/VS Code authenticated
   agent tests were explicitly left pending by the owner.
4. Do the isolated live PostgreSQL 18 backup restore after clone-cost approval.
   Use `scripts/compare_postgres_restore.py` and the restore acceptance document.
   Compare matched source points; a write-time mismatch is not a pass. Keep
   credentials private, preserve production, and arrange billable clone cleanup.
5. Complete signing/notarization, clean-machine Windows 11 upgrade/UI acceptance
   and Windows verification when resources exist. The owner clarified that
   neither Apple nor Windows signing setup is currently available. Unsigned
   builds can be tested; do not label them trusted production installers.
6. Finish publisher identity, domain/reviewer access, all-tool tests, walkthrough,
   legal/retention decisions and platform review for official listings. See
   `docs/OFFICIAL-CONNECTORS.md` and the directory submission kit. Do not submit,
   accept legal attestations or publish on the owner's behalf without the
   relevant explicit authorization.

Read `docs/GOVERNANCE-ACCEPTANCE-2026-11-13.md`,
`docs/CAPTURE-QUALITY-2026-11-14.md`,
`docs/HOSTED-DISCLOSURE-REVIEW-2026-11-14.md`,
`docs/CUSTOMER-UPGRADES.md`, `docs/MACOS-RELEASE.md`, and
`docs/WINDOWS-PREVIEW.md` for details. Preserve local-first boundaries and do not
silently grant access, migrate/upload local data, or remove historical records.

No blanket production-ready, universal automatic-memory, security certification,
competitor weakness or directory-approval claim is supported. The earlier goal
was paused in the app UI; subsequent work was manual owner-requested continuation.
Do not create an endless automation to finish this handoff.
