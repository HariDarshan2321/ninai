# Isolated restore comparison and consenting-account acceptance

The production restore gate remains pending until an approved Render recovery
instance exists and its private read-only evidence is retained. This document
does not authorize billing, opening database networking, deleting a database,
accessing anyone's account, or switching the production service's database.

## Operator boundary and recovery cost

The release owner must approve creation of **one separate billable recovery
database**, its selected compute/storage price, region and maximum lifetime.
Record the dashboard's actual quote and approval before creation. An existing
web-service upgrade approval does not cover a recovery database. Render says a
recovery instance remains separately billable until deletion and copies the
source IP allow list. Keep both databases private, inspect the clone's list,
and use a trusted same-region private shell rather than opening public access.
Deletion requires separate explicit approval. See [Render recovery documentation](https://render.com/docs/postgresql-backups)
and [Render's recovery billing explanation](https://render.com/tutorials/postgres-on-render/backups-and-pitr).

Do not attach an HTTP/MCP service to the clone: recovered OAuth bindings, PAT
digests, memberships and grants can represent an older authorization state.
Run no bootstrap, migrations, cross-provider fixture or application startup
against production or its recovery clone for this read-only comparison.

## Explicit-target contract

`scripts/compare_postgres_restore.py` requires Python 3.11+ and the cloud
environment's `psycopg` dependency. From a local checkout the interpreter is
`cloud/.venv/bin/python`; in the existing Render Python environment use `python`.
The script uses only read-only transactions against both targets. It neither
creates nor restores databases. Supply URLs through a protected environment,
never command arguments, pasted chat, saved shell history, screenshots or logs:

- `NINAI_SOURCE_DATABASE_URL`: approved source's internal PostgreSQL URL.
- `NINAI_RESTORE_DATABASE_URL`: approved recovery clone's internal URL.

Use simple `postgresql://role:password@host:port/database` URLs without query
parameters. TLS is required by the CLI. Unset `PGHOSTADDR`, `PGSERVICE` and
`PGSERVICEFILE`; the script refuses those target overrides. Do not print URLs
while removing an optional URL query suffix in the protected environment.

Privately review the source and clone host/database/role against the Render
resource records. These commands print only a SHA-256 fingerprint of those
identity fields and **do not connect**:

```sh
cloud/.venv/bin/python scripts/compare_postgres_restore.py --fingerprint-env NINAI_SOURCE_DATABASE_URL
cloud/.venv/bin/python scripts/compare_postgres_restore.py --fingerprint-env NINAI_RESTORE_DATABASE_URL
```

After the operator has confirmed the identities and the clone's isolation, pass
those two returned 64-character fingerprints explicitly:

```sh
cloud/.venv/bin/python scripts/compare_postgres_restore.py \
  --confirm-source SOURCE_FINGERPRINT \
  --confirm-restore RESTORE_FINGERPRINT \
  --confirm-isolated-restore \
  --statement-timeout 30 --total-timeout 180 > restore-comparison.json
```

The confirmation flag is an operator attestation; software cannot establish the
Render network policy or billing approval. The script rejects equal URL targets
even with different roles and equal connected database/server-address/port
identities (including simple DNS aliases). This is a guard, not proof that two
different proxy endpoints cannot reach the same database. Use direct internal
database URLs, not proxy endpoints. Fingerprints exclude passwords.

Exit `0` means both inventories/invariants are valid, complete reviewed table
sets and migration versions match, schema digests match, and every table's count
and digest match. Exit `1` means completed comparison found differences or
invalid inventories. Exit `2` means validation/connection/query failed; it prints
a generic reason because driver exceptions can contain secrets. Do not enable
SQL parameter logging or shell tracing. Check private platform diagnostics when
needed without publishing credentials or stored rows.

The report covers all 21 current public tables, including session artifacts,
OAuth mappings, PAT records and capture settings. No row text, credential/hash,
user identity, source URI or individual row digest is returned. Each row is
salted and SHA-256 hashed **inside PostgreSQL**, then the client streams sorted
hashes into one digest per table. The random salt stays in process memory and
is discarded, so digests cannot be compared between separate runs. Counts and
schema/migration versions are non-content operational metadata; keep the report
in the private release evidence directory.

The verifier checks provenance and workspace/project/user scope relationships,
client memberships and OAuth/PAT ownership. It compares column definitions,
defaults, constraints and indexes. It fails closed on unreviewed/missing tables
and row-level security, which could otherwise hide rows. These checks do not
execute retrieval or establish runtime authorization behavior. Each database has
an independent repeatable-read snapshot. Active writes or an earlier PITR point
can legitimately produce differences; **do not turn those into an exact-match
PASS**. Record the recovery timestamp and reconcile every difference against
the known recovery point. A zero-difference comparison requires an equivalent
source snapshot. The existing `verify_postgres_restore.py` is a narrower
structural check and is not an equality proof.

Connection attempts are bounded to ten seconds each, SQL statements to thirty
seconds by default (maximum sixty), locks to three seconds, and idle transactions
to sixty seconds. The total budget is checked between queries and fetch batches;
one in-flight bounded statement can run beyond that budget. Failed transactions
are rolled back by the connection contexts. Large datasets can time out rather
than being reported as verified; arrange a capacity-appropriate operator window.

## Trusted backup tools and synthetic rehearsal

Use official PostgreSQL **18** client binaries for the current PostgreSQL 18
source and recovery target. Record resolved absolute binary paths, `pg_dump
--version`, `pg_restore --version` and server major versions privately before
running a logical backup. Do not use the local PostgreSQL 15 binaries against
production 18. PostgreSQL documents that older `pg_dump` cannot dump a newer
server and that restoring into an older major version is not guaranteed. Use
matching trusted dump/restore binaries and restore into 18 for this drill.
See [PostgreSQL 18 pg_dump documentation](https://www.postgresql.org/docs/18/app-pgdump.html).

Only a trusted backup should be restored; restoration executes its SQL. Archive
checksum, encrypted retention location, creation/recovery timestamps, recovery
duration, operator and target resource IDs belong in private evidence. The
comparison script performs no `pg_dump` or `pg_restore`. A clone created by PITR
proves the provider recovery path; a logical export requires its own successful
restore rehearsal if that gate is claimed.

The opt-in test creates its own temporary loopback-only cluster, synthetic
source and distinct restore database, applies repository migrations, runs the
synthetic cross-provider fixture, dumps to a custom archive, restores it, and
removes only that temporary cluster. It uses no existing database URL. Run with
an explicitly reviewed local binary directory:

```sh
NINAI_RESTORE_REHEARSAL_PG_BIN=/opt/homebrew/opt/postgresql@15/bin \
  cloud/.venv/bin/python -m unittest discover -s cloud/tests \
  -p test_restore_comparison.py -v
```

This passed with local PostgreSQL 15 on 13 November 2026: eight tests, real
synthetic dump/restore equality, same-count content corruption detection,
provenance loss detection, missing-index detection, RLS refusal, and attempted
DELETE denied by the verifier's read-only transaction. It is local tool evidence,
not a production PostgreSQL 18 recovery or hosted account acceptance result.

## Consenting dedicated cloud account journey

`prepare_external_tester_acceptance.py` creates a pending report after public
HTTPS discovery checks and records installed Claude/Codex versions. It does not
sign in, grant access, handle tokens or complete acceptance. Use:

```sh
cloud/.venv/bin/python scripts/prepare_external_tester_acceptance.py \
  --endpoint https://app.ninai.io --output external-tester-acceptance.md
```

The consenting tester must sign up/sign in using their own dedicated beta
account, create an isolated named project with synthetic facts only, approve
each Claude/OpenAI connection's exact project permissions, then use their own
installed hosts. Record a stable tester pseudonym, UTC timestamps, host versions,
synthetic marker/memory IDs and provenance references; never record OAuth codes,
cookies, bearer tokens, authorization headers or private account data.

Complete the generated two-way marker journey, verify a third ungranted client
cannot read the markers, and verify disclosure records for the successful reads.
Revoke the already-issued OpenAI connection; prove its existing credential is
denied on a fresh request while Claude can still read its own permitted project.
Capture evidence of explicit user consent and the permission/revocation result.
Revoke temporary connections and follow the agreed synthetic-data cleanup policy.
An independent tester attestation is required for the independent-tester gate;
the implementation operator cannot attest to being independent.

`verify_cross_provider.py` is a **mutating synthetic service-level test**: it
applies migrations, inserts fixtures and deletes fixture rows. Run it only against
an explicitly provisioned disposable synthetic database. Do not point it at
production or a recovery clone containing production data. It does not invoke
real Claude/Codex hosts and cannot replace the consenting-account journey.
