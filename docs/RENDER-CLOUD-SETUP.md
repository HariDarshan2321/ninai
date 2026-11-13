# Render cloud setup and acceptance

Ninai already has a hosted service. Adapt that service first; do not create a
second production database or move its domain by applying the example blindly.
This document and `cloud/render.example.yaml` do not change Render settings or
approve spending.

## Existing service: release-owner checks

1. Keep the existing service/database IDs, domain, database name and PostgreSQL
   major version. Confirm their actual region and current plans in Render.
2. If the web service uses Free compute, select an owner-approved paid service
   plan. Free services idle after 15 minutes; repository code and self-pinging do
   not remove that limitation. A paid plan removes this free-tier behavior; it
   does not guarantee uptime or capacity. [Render free-service limits](https://render.com/docs/free).
3. Set the service's health-check path to `/ready`, which executes a database
   query. `/health` checks only the process. Set automatic deployment to **After
   CI Checks Pass** (`autoDeployTrigger: checksPass`). Verify all repository
   checks on the deployed commit. [Health checks](https://render.com/docs/health-checks),
   [Blueprint fields](https://render.com/docs/blueprint-spec).
4. Keep service and PostgreSQL in the same region. Use the database's internal
   connection URL as `DATABASE_URL`; remove public database IP ranges. An empty
   database `ipAllowList` blocks external connections. Retain existing backup
   and retention settings. [Private networking](https://render.com/docs/private-network),
   [Postgres connections](https://render.com/docs/postgresql-creating-connecting).
5. Enter OAuth settings directly in the protected service environment using
   `cloud/.env.example` and [AUTH0.md](AUTH0.md). Audience and public resource must
   equal the actual HTTPS `/mcp` URL; preserve the issuer's trailing slash and
   exact dashboard callback URL. Do not copy credentials into chat or the repo.
   Keep public hosted mode on OAuth. Do not enable PAT fallback to make a failed
   OAuth connector appear to work.
6. Confirm the startup migration log, current commit, `/ready`, failure alert
   delivery, and the backup/restore evidence in [RENDER-OPERATIONS.md](RENDER-OPERATIONS.md).
   Measure login/readiness after genuine inactivity. Do not mark cold starts
   fixed from one quick response.

`sync: false` prompts for a variable only during initial Blueprint creation.
For an existing service, add/update protected variables manually; re-syncing an
example will not populate new values. [Secret variable behavior](https://render.com/docs/blueprint-spec#prompting-for-secret-values).

## Optional new-environment example

`cloud/render.example.yaml` is JSON-formatted YAML, so both Render and Python's
standard JSON parser can read it. It is not the default root `render.yaml` and
has not been applied to any account. Applying it can create billable resources.
Use it only after reviewing the intended environment and costs with its owner.

Its explicit assumptions are Frankfurt; one paid `0.5c-512mb` Docker web service;
one paid `0.1c-256mb` PostgreSQL instance; 15 GB database storage; PostgreSQL 16 to
match current CI; no preview environments; and no disk/local-vault mounts. These
are example values, not a capacity recommendation or the existing production
configuration. Do not downgrade/recreate an existing PostgreSQL 18 database to
match this template. Hosted mode remains separate from the user's local SQLite
memory.

Validate the example's safety policy without installing dependencies:

```sh
python3 scripts/validate_render_example.py
```

For full schema validation, download the [official Render schema](https://render.com/schema/render.yaml.json)
to a temporary file, then use optional tooling outside the production dependency
set:

```sh
uv run --with jsonschema python scripts/validate_render_example.py \
  --schema-file /path/to/render-schema.json
```

The reviewed schema on 12 November 2026 had SHA-256
`6c6721a602ef6d368d5c9384c473cefaae99980e43dd4b1adcf8a2f258fc54f4`.
Validation proves the example structure and local safeguards, not deployment,
provider settings, billing approval or production readiness.

## Real connector acceptance still required

Use a designated tester and synthetic decision in the actual hosted product:
fresh private-browser signup, return from OAuth, create a project, connect each
intended assistant, grant only the required access, save a sourced decision,
recall it from the other assistant, revoke one connection, and issue a fresh
request. Confirm denial for the revoked connection and continued access for the
other, then inspect sharing history. Never paste bearer tokens or authorization
codes into the report. Run the same-user and different-user/project isolation
checks in [CROSS-PROVIDER-SMOKE-TEST.md](CROSS-PROVIDER-SMOKE-TEST.md).

Anonymous HTTP 200 health/discovery and HTTP 401 without credentials are useful
preflight checks. They do not prove signup, consent, connector compatibility,
memory access, a hosting plan or recovery. Local PAT protocol tests do not
replace this real OAuth journey.

## Repeatable cloud releases

Follow [application upgrades and rollback](RENDER-OPERATIONS.md#application-upgrades-and-rollback)
for each hosted release. It includes prior-deploy evidence, schema compatibility,
real OAuth acceptance, rollback and restoration of CI-gated deploys. The optional
Blueprint cannot configure the existing service's Git-provider integration,
prove a paid service upgrade, or complete recovery and cold-start acceptance.
