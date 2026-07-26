# Hosted beta launch checklist

Unchecked items block a truthful public hosted-beta launch.

## Build and data

- [ ] Pin and record the release commit and image digest.
- [ ] Run the complete engine, cloud unit, PostgreSQL integration, website, and validator suites with no skipped required tests.
- [ ] Apply migrations to staging, verify schema, then rehearse production migration and rollback/restore.
- [ ] Provision private PostgreSQL, a least-privilege runtime role, encrypted backups, retention, and a successful restore test.
- [x] For Render, use the internal database URL and clear the external IP allow list; evidence recorded in [RENDER-OPERATIONS.md](RENDER-OPERATIONS.md) on 26 July 2026.
- [ ] Verify paid-plan PITR, create and retain a logical export, and pass the read-only restore verifier against an isolated recovery database.
- [ ] Seed users, workspace memberships, client connections, and least-privilege grants through an auditable operator flow.

## Identity and network

- [ ] Configure a real OAuth/OIDC issuer, registered redirect URIs, consent, token lifetimes, MFA policy, and signing-key rotation.
- [ ] Verify JWT `iss`, `aud`, `resource`, `exp`, `sub`, workspace, and client-connection claims in staging.
- [ ] Serve `/mcp` and `/health` over HTTPS; keep the database off the public network.
- [ ] Validate protected-resource metadata and, in OAuth mode, issuer metadata from outside the deployment network.
- [ ] Add rate limits, request/time limits, trusted-host/CORS rules, redacted centralized logs, monitoring, and alerts.
- [ ] On Render, set `/health`, enable failure notifications, add an external HTTPS monitor, and record database capacity/connection alert thresholds.

## Product controls

- [ ] Wire the hosted control center to production authentication; test owner/admin/member authorization.
- [ ] Verify proposal review, grant creation/revocation, connection revocation, activity, export, and confirmed workspace deletion.
- [ ] Publish privacy terms covering hosted persistence, subprocessors, region, retention, deletion timing, and provider disclosure.
- [ ] Document support, incident response, backup recovery, token compromise, and security-contact procedures.

## Compatibility gate

- [ ] Complete and sign [CROSS-PROVIDER-SMOKE-TEST.md](CROSS-PROVIDER-SMOKE-TEST.md) against the release deployment.
- [x] Verify Claude → OpenAI → Claude provenance-preserving round trip locally with real hosts.
- [x] Verify workspace/scope isolation and immediate denial using an already-issued token after revocation locally.
- [x] Record exact client, SDK, model, and server versions in [COMPATIBILITY.md](COMPATIBILITY.md).
- [ ] Reconcile the website, README, privacy copy, and `llms.txt` with the recorded evidence—no broader claims.

## Release

- [ ] Review [SECURITY-REPORT.md](SECURITY-REPORT.md), accept or remediate every open risk, and assign owners/dates.
- [ ] Run the website SEO/domain checklist and verify production DNS, redirects, certificates, metadata, and forms.
- [ ] Establish rollback authority and perform a go/no-go review.
- [ ] Tag the verified release and retain the test report, logs, migration output, and image digest.
- [ ] Retain the backup checksum, restore-verifier output, recovery timing, operator, and approval with the release evidence.
