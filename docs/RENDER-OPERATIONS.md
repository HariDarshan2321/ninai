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
  continued to return HTTP 200 from `https://ninai-cloud.onrender.com/health`.
- Notifications: workspace email notifications are enabled for failure events.
- Restore drill: not claimed as complete. Render recovery creates a separate,
  billable database. Create that isolated database only with release-owner cost
  approval, then run the verifier above and retain its non-sensitive output.

## Health, monitoring, and alerts

In the web service's **Settings**, set the HTTP health-check path to `/health`.
Render treats a 2xx/3xx response as healthy, prevents an unhealthy new deploy
from receiving traffic, and can restart an unhealthy running instance. Also run
an independent HTTPS monitor against `/health` from outside Render; the platform
probe alone cannot detect a regional or edge-path failure.

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
- set `/health`, auto-deploy **After CI Checks Pass**, and notification owners;
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
