# Ninai product readiness — 12 November 2026

Decision: **not yet accepted for an unrestricted public launch**. This review
implemented substantial release fixes and verified bounded local scenarios.
It does not certify security, native installer trust, production capacity, or
universal automatic capture. Code readiness and hosting acceptance are separate.

## Implemented in this review

| Area | Finding and resulting behavior | Evidence |
| --- | --- | --- |
| Assistant UI | Every assistant exposed all permission switches. Cards now collapse, retain their open state, and always summarize access. Each grant is independent; new project access stays off. | Desktop browser regression and screenshots |
| All app pages | Mobile navigation overflow, missing help, stale search responses and unhandled archive actions. Seven pages reviewed; Help includes troubleshooting, recovery and safe feedback. | Loaded-page mobile regression, keyboard/retry tests |
| Growing memory | Owner search filtered only the newest 1,000 rows, and filters were applied after the display cap. SQL now searches the whole live store and applies area/type filters before the 200-result limit. Inventory count is exact; the UI explains the display limit. | 1,101-row regression, Unicode/literal search, deleted-memory exclusion |
| Updates | No visible update check or consistent pre-upgrade database snapshot. Explicit bounded release checks distinguish offline/unpublished/current/newer builds. Mac replacement takes a validated private SQLite snapshot, including committed WAL data, before diagnostics/migrations. | Release metadata failure tests, live-WAL snapshot, corrupt/symlink refusal, connector failure tests |
| Local capture | Credential-shaped Ninai tokens and JSON scalar input were not handled safely. Filtering and scalar normalization corrected. SQLite sidecar cleanup races no longer fail app opening. | Security, transcript and concurrent-open regressions |
| Owner/agent boundary | Valid delegated agent credentials could reach owner control operations. OAuth control now requires the dashboard client; PAT mode requires a separate explicitly allowlisted operator credential. | Real PostgreSQL export/grant/delete denial, operator and revoked-membership tests |
| Memory isolation | Search/fetch omitted grant memory-type restrictions; raw sessions could bypass that restriction. Both now enforce the restriction. | Real PostgreSQL typed-grant denial tests |
| Session lifecycle | Expired/deleted archives could be returned or repopulated; context wrapper tokens were undercounted. Retrieval now checks retention/consent and packet size; identities remain tombstoned. | Retention, deletion, race and packet-budget tests |
| Storage | Concurrent writes could overrun count-before-write checks. Workspace locks now serialize durable-write caps and idempotent retries. | Concurrent quota/idempotency tests |
| Cloud operation | Dense connection controls, fragile JSON-only errors and missing signed-out help. Controls now progressively disclose; timeout/proxy/export/auth errors are recoverable. | Cloud UI/control tests and mobile visual review |
| Deployment | Added operational inventory and explicit retention maintenance, operator migration instructions, and current Render rollout/rollback guidance. | Render schema/policy and Compose tests |

Cloud caps default to 10,000 memory rows, 20,000 accepted write/idempotency rows,
and 1,000 sessions per workspace. Tombstones count. These are abuse/capacity
safeguards, not advertised pricing entitlements. They do not bound total disk:
audit logs, accounts, projects and connection metadata still need a retention,
monitoring and capacity policy. See [Render operations](RENDER-OPERATIONS.md).

## Verified scenarios

- Engine: final combined suite passed 125 tests, including the continuity-skill
  installer; its 18 dedicated tests cover owned updates, edit preservation, symlink refusal,
  newer-version downgrade refusal and CLI isolation before vault initialization.
- Cloud: 136 tests passed against disposable PostgreSQL, zero skips.
- Browser: 19 tests passed, covering 15 desktop cases and public pages at desktop
  and mobile viewport sizes. Synthetic vault + real DesktopApi; not a native
  macOS/Windows WebView or an authenticated production OAuth test.
- Local stress: 16 workers, 5,000 synthetic scenarios, SQLite integrity,
  provenance/isolation/revocation checks passed. This is not a capacity benchmark.
- Hosted HTTP: 48 checks, eight synthetic workspace fixtures cleaned; peer
  read/source, writes and immediate revocation passed.
- Actual Codex CLI, cloud-only, installed continuity skill: all six natural-prompt
  cases passed, including automatic active save with permission, fresh-session
  retrieval of the new decision, review-only proposal and negative control.
  Evidence: `/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-implicit-cloud-x4hj1ub_`.
  A single controlled run is not a reliability percentage or another host's proof.
  A subsequent run using the actual installer passed the first four scenarios,
  then stopped when Codex reported its usage limit during review-only saving. It is not
  recorded as another full pass; synthetic fixture cleanup completed.

Desktop visual evidence is under `/tmp/ninai-desktop-review/`: all seven pages,
expanded/collapsed assistant access, mobile Assistants and Help. The cloud
review includes a 390px permission/help interaction without document overflow.

## Live Render findings

Authenticated dashboard inspection found:

- `ninai-cloud` was running the Free compute plan. Render explicitly warned of
  idle spin-down and delays of 50 seconds or more. This is the observed cause of
  infrastructure sleep; it is not fixed by a health endpoint or keepalive pings.
- The owner explicitly approved the $7/month web-service plan plus applicable
  taxes and confirmed staying on Render. The compute change completed successfully. The dashboard shows
  `0.5c-512mb`, one instance, $7/month selected, and the compute-triggered deployment
  `dep-dbr0iao8v5cc73edm6m0` succeeded in 25.7 seconds at 19:44:59 Europe/Berlin.
  Public `/health` and `/ready` returned HTTP200 afterward. No database compute/storage/workspace subscription upgrade authorized.
- Database: PostgreSQL18, Frankfurt, paid Basic-256mb; $6/month compute, 1GB
  allocated storage, 11.75% used at inspection. External database traffic is
  disallowed. Storage autoscaling and database high availability are off.
- Settled recovery UI: three-day point-in-time recovery window. Seven days
  requires a Pro workspace. The initial loading placeholder said seven days;
  the settled three-day value is authoritative. A restore drill has not run.
- Existing deployments track the GitHub `main` branch. The previous live code was
  `e5d8c80`; newer code must be identified after CI/deployment, not assumed live
  because it was pushed. Version/revision are now included in `/health` for this.

## Release blockers and acceptance actions

1. **Actual cloud rollout and account journey.** Verify the final deployed revision,
   paid compute, `/ready`, sign-in after idle, existing OAuth connections and
   cached-tool metadata refresh. Test new-user signup, permission grant, ordinary
   natural recall/save, subsequent session, revoked access and export/delete with
   a dedicated consenting test account. Never seed real customer accounts.
2. **Restore proof.** Restore into a separate isolated database, compare memory
   IDs/sources/grants, and run integration checks. Do not overwrite production.
   A restored database can incur a separate bill; confirm that cost first.
3. **Continuity distribution.** URL-only connections are not evidence of automatic
   memory. The explicit Codex skill installer is included with source/app tooling
   (`ninai integration-skill install --client codex`), has 18 preservation/update
   tests, and was built/imported from a wheel in an isolated smoke test. Existing users need
   that workflow installed/refreshed. Cloud-only novice setup and other providers
   still need independent acceptance; local hooks do not capture cloud/browser chats.
4. **Trusted app delivery.** No valid macOS signing identity is available on this
   machine. Sign/notarize and test a packaged prior-to-new-version upgrade on a
   clean Mac. Windows installer, signatures and upgrade/rollback need real Windows
   acceptance. Do not advertise signed or generally available Windows builds.
5. **Operations.** Assign uptime/error/capacity alerts, maintenance schedule and
   audit retention. Test database outage, exhausted pool, credential rotation,
   auth-provider outage, incident revocation and rollback. Keep a single replica
   until cross-replica rate limits are implemented or enforced externally.
6. **Independent usability.** Time an unfamiliar technical and nontechnical person
   from first visit through installation, connection and a first shared memory.
   Do not claim five minutes until that complete path has been observed.

## Protection boundaries

Local SQLite and recovery snapshots are permission-restricted files, not
application-encrypted vaults. Hosted memory/session columns are also not encrypted
by application code; a database operator credential can read their contents.
Provider disk/backup encryption and TLS are separate operational controls and
must not be described as end-to-end encryption. Application SQL enforces tenant
and scope boundaries; PostgreSQL RLS is not a second boundary in this release.
Secret-pattern filters are defense in depth, not comprehensive secret detection.
Revocation blocks future retrieval, not copies an assistant has already received.

[Customer upgrades](CUSTOMER-UPGRADES.md),
[natural-prompt acceptance](IMPLICIT-CONTINUITY-ACCEPTANCE.md),
[Render rollout/rollback and storage runbook](RENDER-OPERATIONS.md).

## Live release verification — 13 November 2026

- Code `ef42bd27d4b6d44d630c8cb0718b896957e27ef7` was pushed to `main`.
- [GitHub validation](https://github.com/HariDarshan2321/ninai/actions/runs/43378174323)
  succeeded; Vercel also reported success.
- Render dashboard identifies the same commit as Live; public `/health` reports
  version0.1.1 and that exact revision, and `/ready` returns HTTP200.
- The live service is on approved paid0.5c-512mb compute with one instance.
- Auto-deploy was found set to On Commit, then changed and confirmed to
  After CI Checks Pass. Existing /ready health-check configuration was confirmed.
- No database plan, storage allocation, external access rule, or workspace
  subscription was changed. A production restore or clean-machine signed/native
  installer acceptance has not been performed.
