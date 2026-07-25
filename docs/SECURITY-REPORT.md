# Hosted beta security report

## Scope and conclusion

This is an implementation review, not an independent audit or certification. The hosted beta has useful application-layer controls and automated tests, but it must not be described as production-secure until deployment hardening, operational controls, and real-host acceptance are complete.

## Implemented controls

- Local and hosted modes are separate. Hosted code does not import or synchronize the local SQLite vault.
- OAuth identity comes from an asymmetric-signed JWT validated for issuer, audience, expiry, and resource. Ninai delegates OAuth authorization and token issuance to an external issuer. Explicit self-hosted PAT mode instead resolves an opaque token digest to a fixed database principal.
- Signed user, workspace, and client-connection claims are rechecked against live user, membership, workspace, and connection state on each authenticated request.
- PostgreSQL queries bind the authenticated workspace and enforce live scope grants before reads and writes.
- `propose_memory` and `remember` use distinct grants; active writes require `can_auto_activate`.
- Stored and returned memories retain a source URI. Search, fetch, and recall create disclosure records.
- Idempotency keys are unique per workspace and client connection; reusing a key with different content is rejected.
- Common credential patterns and bounded request sizes are rejected by the store/transport.
- Per-workspace/client sliding-window read and write quotas are enforced in process, and streamed HTTP request bodies are capped at 64 KiB before tool dispatch.
- Client revocation also revokes its grants and is checked before its next request.
- Workspace export and soft deletion exist in the control service; destructive workspace deletion requires owner role and exact slug confirmation.

## Test evidence

The automated suite covers JWT validation, identity resolution, revoked-client rejection, MCP authentication and route registration, tool bounds, provenance, disclosure logging, write-mode separation, tenant isolation, idempotency, grants, control-center authorization, export, and deletion behavior. PostgreSQL lifecycle coverage only runs when `NINAI_TEST_DATABASE_URL` points to a disposable database; a skipped integration test is not a pass.

## Known gaps and deferred work

- No independent penetration test, security audit, compliance certification, threat-model sign-off, or production incident exercise.
- No database-at-rest encryption managed by Ninai, field-level encryption, customer-managed keys, or zero-knowledge design. Deployment-provider disk encryption is an operator concern.
- No refresh-token storage or authorization server in Ninai. In OAuth mode, issuer configuration, consent, MFA, session policy, token lifetime, key rotation, and client registration remain external responsibilities. Self-hosted PAT mode has expiry and live revocation but no MFA, consent, refresh, or audience-bearing JWT.
- The in-process limiter is not distributed across replicas and does not replace platform/WAF abuse controls, global quotas, or denial-of-service protection.
- No cryptographically tamper-evident disclosure log, external log sink, alerting, backup/restore proof, retention scheduler, or hard-delete job.
- The control UI/API is mounted with the hosted service and verifies the same bearer credentials. Existing-workspace identity comes only from verified token claims; first-workspace OAuth onboarding accepts only the signed subject. Browser hardening and production session/consent design remain deployment work.
- Secret-pattern filtering is defense in depth, not a complete data-loss-prevention system. Prompt injection and malicious source content are not classified.
- No browser security policy, CSRF design, hardened session cookie flow, or content-security-policy review has been proven for a hosted control-center deployment.
- Dependency scanning, container scanning, SBOM generation, TLS policy, network segmentation, database roles, and secret rotation are not yet recorded release evidence.

## Required deployment controls

Terminate TLS at a trusted proxy; keep PostgreSQL private; use a least-privilege database user; store credentials in the platform secret manager; restrict CORS and trusted hosts; add request/body/time limits and rate limiting; centralize redacted logs; test backup restore; monitor health, authentication failures, denial rates, and database saturation; and document token/key rotation plus incident revocation.
