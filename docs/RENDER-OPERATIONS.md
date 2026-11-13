# Render operations runbook

This runbook covers the account-level controls required when the hosted Ninai
beta runs as a Render web service with Render Postgres. It does not make the
local SQLite vault hosted, and it does not replace the hosted launch checklist.

## Private database networking

Place the web service and PostgreSQL in the same Render region and configure
`DATABASE_URL` from the database's **internal** connection URL. Render services
in the same region can use that private path even when public database access is
disabled.

Render Postgres permits `0.0.0.0/0` external access by default. Before loading
real beta data, open the database's **Info → Networking** section and remove all
external IP ranges so the allow list is empty. Do not put an external database
URL in the web-service environment. If an operator temporarily needs `psql` or
`pg_restore`, allow only that operator's current `/32`, complete the operation,
then remove it and confirm access fails from the public internet. The Render CLI
equivalent is `render pg update <database> --clear-ip-allow-list`; this command
is documented here for an administrator and is not run by repository scripts.

A Render point-in-time recovery instance copies the original database's IP
allow list. Verify the recovered instance's list before connecting any service.

## Backup and restore evidence

Use a paid Render Postgres plan for a public beta. Render's free database type
does not provide PITR or managed logical exports. At launch, record the paid
plan, PostgreSQL major version, recovery-window length, region, and responsible
operator in the release evidence.

At least weekly, create a logical export from **Postgres → Recovery → Create
export**, download it to the approved encrypted retention location, and record
its timestamp and checksum. Render retains downloadable exports for seven days;
that platform window is not a long-term retention policy. Never commit an export
or database URL.

Run a restore drill before launch and at least quarterly:

1. In **Recovery**, choose a point at least ten minutes in the past and start a
   point-in-time recovery into a new, isolated database. This creates a new
   database; it does not overwrite the source.
2. Restrict the recovery database's external allow list to the operator's `/32`
   only. Do not point the production service at it.
3. Run the read-only verifier with the recovery database's external URL:

   ```bash
   NINAI_RESTORE_DATABASE_URL='postgresql://...' \
     cloud/.venv/bin/python scripts/verify_postgres_restore.py
   ```

4. Confirm all expected migrations and tables are present. Compare the reported
   non-sensitive row totals with the production baseline and perform a small
   application-level recall test using designated synthetic records.
5. Record the recovery point, start/finish time, verifier output, tester, and
   result. Remove temporary external access immediately.
6. Keep the recovery database until the release owner accepts the evidence.
   Database deletion is destructive and Render does not retain backups of a
   deleted database, so deletion requires separate explicit approval.

The verifier sets its transaction read-only, reports schema/migration gaps and
aggregate row totals, never prints its database URL, and performs no restore or
deletion itself.

### Production evidence — 26 July 2026

- Database: `ninai-cloud-db`, Render Basic-256mb, PostgreSQL 18, Frankfurt.
- Point-in-time recovery: enabled with a three-day recovery window.
- Logical export: completed successfully at 08:36 Europe/Berlin. The prior
  25 July export remains visible in Render; export download links are not
  recorded because they are signed credentials.
- Network boundary: the database-specific public allow rule was removed and
  **Block All Inbound IPs** was confirmed. Render reports that all internet
  traffic is blocked by the database inbound-IP policy.
- Private-path validation: after the block was applied, the deployed service
  continued to return HTTP 200 from `https://app.ninai.io/health`.
- Notifications: workspace email notifications are enabled for failure events.
- Restore drill: not claimed as complete. Render recovery creates a separate,
  billable database. Create that isolated database only with release-owner cost
  approval, then run the verifier above and retain its non-sensitive output.

## Health, monitoring, and alerts

In the web service's **Settings**, set the HTTP health-check path to `/ready`.
Render treats a 2xx/3xx response as healthy, prevents an unhealthy new deploy
from receiving traffic, and can restart an unhealthy running instance. `/ready`
checks PostgreSQL through the application pool; `/health` checks only that the
web process is alive. Also run independent HTTPS monitors against both endpoints
from outside Render; the platform probe alone cannot detect a regional or edge-path
failure.

In **Workspace → Integrations → Notifications**, enable at least failure email
notifications for every on-call release owner. This covers failed deploys,
unhealthy services, and failed jobs. Configure escalation outside Render and
test delivery before launch.

Review these dashboard signals at least weekly and before/after every release:

- web-service HTTP error volume and latency, CPU, and memory;
- PostgreSQL disk usage, active connections versus the plan limit, CPU, memory,
  slow-query logs, and any slow locks;
- authentication failures, authorization denials, revocations, and unusual MCP
  request volume in redacted application logs;
- most recent successful PITR window, logical export, and restore drill.

Render dashboard history is bounded by the workspace plan. For longer retention
and threshold alerts, configure a supported external log stream and, on eligible
plans, an OpenTelemetry metrics stream. Never log bearer tokens, database URLs,
OAuth claims beyond the minimum identifiers, memory bodies, or source contents.

## Account actions still required

These cannot be proven or performed by the repository:

- select and pay for the database/service plans and confirm the recovery window;
- ensure service and database use the same selected region and internal URL;
- populate OAuth and service secrets in Render's secret manager;
- set `/ready`, auto-deploy **After CI Checks Pass**, and notification owners;
- configure external uptime/log/metrics destinations and alert thresholds;
- retain a downloaded logical export in the approved encrypted location and
  complete the isolated, billable restore drill after cost approval;
- record operators, recovery objectives, retention, escalation, and destructive
  database-deletion authority.

Official Render references: [Postgres connections and network
access](https://render.com/docs/postgresql-creating-connecting), [recovery and
backups](https://render.com/docs/postgresql-backups), [health
checks](https://render.com/docs/health-checks), [service
metrics](https://render.com/docs/service-metrics), and
[notifications](https://render.com/docs/notifications).

## Application upgrades and rollback

Use this procedure for the existing hosted service. A local Ninai app update and
an account-level database major-version upgrade are separate operations.

Before a release, record the current successful deploy ID and commit, target
commit, current migration versions, current service/database plan and region,
`/ready` result, and the timestamp of the latest restorable backup. Confirm a
recent isolated restore drill and an accountable operator. Keep credentials and
memory contents out of the evidence. Review every new migration for compatibility
with both the previous and target application versions: startup runs migrations
before serving traffic, and old and new processes can briefly share the database.
Do not combine a destructive schema change with an application rollout.

1. Run repository CI on the exact release commit, including PostgreSQL migration
   and isolation tests. Rehearse the upgrade and application rollback against an
   isolated restored database with synthetic test memories.
2. Confirm that the service is linked through the Render Git integration.
   A service created with only a public repository URL cannot auto-deploy;
   `checksPass` in an example file alone does not establish that integration.
   Render also does not auto-deploy when it detects zero checks; verify the
   expected checks actually ran rather than being skipped. [Deploy behavior](https://render.com/docs/deploys).
3. Deploy the reviewed commit through the existing service. Watch migration and
   startup logs, readiness and resource usage. If migrations fail, investigate
   while retaining the previous healthy deploy; do not repeatedly restart a
   failing migration or clear the database to make startup succeed.
4. Verify login, project grants, a synthetic proposal/approval/recall, a fresh
   revoked-client denial, and an export. Check both `/health` and `/ready` from
   outside Render. Readiness alone does not test OAuth or tenant isolation.
5. Observe error rate and request latency against the recorded baseline through
   a representative usage period. Stop the rollout on isolation regression,
   persistent readiness failure, failed synthetic recall, or an unexplained
   increase in errors. Record the deploy ID and evidence, not just a green build.

For an application regression, choose the recorded prior successful deploy in
**Deploys → Rollback**, provided its artifact is still retained and its code is
compatible with the current schema. Render's dashboard rollback disables
auto-deploys; an API rollback does not. The rollback can reuse the target's
environment variables and health-check path, so recheck credentials, `/ready`
and authorization after it finishes. Database contents and migrations are not
undone by reverting application code. Preserve current data and investigate any
schema incompatibility before considering database recovery. [Render rollback
semantics](https://render.com/docs/rollbacks).

If code rollback is unsafe, keep the incident contained and use the isolated
restore procedure above with the release owner. Replacing production with a
recovery database can discard writes after the recovery point and requires an
explicit recovery decision. After resolving the incident, verify the corrected
commit and deliberately restore **After CI Checks Pass** rather than leaving
the service indefinitely on an old deploy.

### Release evidence record

Record these values in the release owner's private operational record; blanks
mean the corresponding gate is still pending:

| Evidence | Record |
| --- | --- |
| Operator and UTC release time | Pending |
| Prior and target deploy IDs / commits | Pending |
| Current plans, region and PostgreSQL version | Pending |
| Applied migration versions / compatibility review | Pending |
| Last backup, recovery point and restore drill | Pending |
| External readiness and synthetic OAuth checks | Pending |
| Error/latency baseline and observation period | Pending |
| Rollback rehearsal / final auto-deploy setting | Pending |

### Cold-start acceptance

Verify the web **service compute plan**, rather than only the workspace plan.
Render Free services idle after 15 minutes and can take about a minute to resume;
upgrading only the workspace does not remove that behavior. [Free compute
limits](https://render.com/docs/free).

On the intended paid service, record the plan and timestamp, allow a genuine
idle period (without self-pings), then time the first page, login callback and
`/ready` request. Repeat after a normal deploy and service restart and compare
with a subsequent warm request. An external monitor may prevent idle time, so
label that limitation in the evidence. Distinguish hosting resume time from
application startup, database connection and OAuth latency before claiming the
reported cold-start issue resolved. Repository checks cannot prove the live
billing plan or these measurements.

## Workspace quotas and physical retention

The hosted application applies these limits per workspace. Enter overrides in
the existing web service's protected environment and deploy/restart to load them;
use positive integers. Invalid or nonpositive values fail initialization. Match
the limits across all replicas. Raising a limit requires checking database
capacity first; it does not resize the Render database.

| Environment setting | Default | Counts |
| --- | ---: | --- |
| `NINAI_MAX_WORKSPACE_MEMORIES` | 10000 | All memory rows, including soft-deleted tombstones |
| `NINAI_MAX_WORKSPACE_WRITES` | 20000 | Durable idempotency-key rows for memory writes |
| `NINAI_MAX_WORKSPACE_SESSIONS` | 1000 | All session rows, including deleted/expired tombstones |

The store serializes quota checks with writes by locking the workspace row.
An exact idempotent retry can return its existing result at capacity; changing
the retry key consumes another write row even when content is deduplicated.
Deleting memories or sessions does not regain row capacity. Session deletion and
retention cleanup remove transcript artifacts while retaining session tombstones
so a delayed client cannot recreate a deleted archive with the same identity.
Do not delete tombstones or retry keys to work around a full workspace.

Use the operator inventory from a trusted shell with the existing `DATABASE_URL`
already supplied securely by the environment. The examples run from the repo
with its cloud virtual environment; in the deployed container use `python`
instead of `cloud/.venv/bin/python`:

```sh
cloud/.venv/bin/python -m ninai_cloud.storage_admin --workspace WORKSPACE_UUID
```

By default this reports counts, approximate row bytes, configured limits and
session artifacts eligible for removal. Row-byte estimates exclude indexes and
are not a substitute for Render's actual disk metrics. The report contains no
memory bodies or credentials. Review the output and existing workspace retention
policy before explicitly applying cleanup:

```sh
cloud/.venv/bin/python -m ninai_cloud.storage_admin \
  --workspace WORKSPACE_UUID --apply-retention
```

This removes artifacts belonging to already deleted or expired sessions according
to the workspace's existing `retention_days`, and tombstones expired sessions.
It does not prune memories, memory tombstones, retry keys or audit logs. It prints
pre-cleanup inventory; rerun without the flag to measure the resulting inventory.
Schedule maintenance only under the operator's approved retention policy.

These quotas are not a global storage bound. Disclosure/audit logs, connections,
grants, projects, tokens and account/workspace creation remain uncapped. Operators
must monitor actual disk growth, maintain an explicit audit-retention policy and
capacity alerts, and investigate abusive account/workspace creation. No automatic
log purge or blanket retention guarantee is implemented. Database-role holders
can read stored text; TLS and provider disk encryption are platform controls,
not application-layer encryption supplied by these quotas.


## Private PAT-mode owner access

Public hosted Render deployments remain OAuth-only for the control plane: set
`NINAI_OAUTH_CONTROL_CLIENT_ID` to the dashboard client and keep
`NINAI_OAUTH_ALLOW_PAT=false` unless scoped machine-client access is separately
required. The public OAuth example does not need an operator PAT setting.

For an explicitly private `NINAI_AUTH_MODE=pat` deployment, ordinary AI PATs are
not owner dashboard credentials. Bootstrap issues a separate no-memory-grant
`operator_client`, `tokens.operator` and its `control_pat_sha256`. Set
`NINAI_CONTROL_PAT_SHA256` in protected service environment to that digest and
restart. Enter only `tokens.operator` in the dashboard's self-hosted access-token
field; keep it out of AI/editor configuration, chat and logs. The empty default
denies PAT dashboard access while scoped MCP PATs remain usable.

Existing workspaces can provision a dedicated operator without recreating data:

```sh
# DATABASE_URL is already supplied securely in the operator environment.
cloud/.venv/bin/python -m ninai_cloud.bootstrap \
  --operator-workspace WORKSPACE_UUID --operator-user OWNER_USER_UUID
```

Use an existing active owner/admin user UUID. This command creates only a new
operator connection and credential; do not pass `--email` or rerun ordinary
workspace bootstrap as a migration. Allowlist the returned digest and restart.
Never allowlist an existing agent token as a shortcut. The allowlist accepts
comma-separated SHA-256 hex digests and still enforces live token, connection,
membership, workspace and role checks. Revoke replaced tokens and remove old
digests during rotation. See [self-hosted setup](../cloud/README.md#self-hosted-personal-access-tokens).
