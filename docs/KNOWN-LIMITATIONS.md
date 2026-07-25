# Known limitations and deferred work

## Hosted beta

- The service is not deployed by this repository. The local PAT-backed Claude Code → Codex → Claude Code and post-revocation gate passed on 25 July 2026, but production OAuth/HTTPS acceptance is still pending.
- OAuth depends on an external issuer. Minimal signed-subject workspace/project/client provisioning is implemented, but issuer-hosted consent, MFA, dynamic client registration, and production browser sessions remain external/deployment work.
- PAT mode is for trusted private self-hosting. It has expiry and live revocation but no browser consent, MFA, refresh flow, or JWT audience/resource claims.
- PostgreSQL search is lexical. There are no embeddings, semantic reranker, consolidation, automatic conflict resolution, or measured retrieval-quality benchmark.
- The hosted control center is a dependency-light authenticated ASGI surface mounted with the MCP service. Its security posture has not been browser-hardened or independently reviewed.
- Workspace deletion is currently soft deletion/revocation. Retention, scheduled hard deletion, backup expiry, and deletion verification are operational work.
- The application has process-local per-client read/write limits and a request-body ceiling, but no distributed quota/billing system, WAF abuse detection, tamper-evident audit chain, external alerting, or documented availability objective.
- Compatibility is limited to the explicit matrix in [COMPATIBILITY.md](COMPATIBILITY.md). MCP availability never implies access to unrelated host conversations.

## Local mode

- The SQLite vault is not encrypted by Ninai; the desktop app runs as the full local owner and must not be exposed over a network.
- Sensitivity labels are display-only. Scope grants, not labels, enforce disclosure.
- Automatic capture is specific to the optional Claude Code `PostToolUse` hook. Other clients write through explicit MCP tool calls.
- SQLite FTS5 is the retrieval index; there are no vector embeddings or local-model extraction.

## Deferred release work

- Complete the production deployment and signed cross-provider report.
- Choose and integrate the beta OAuth issuer and provisioning lifecycle.
- Harden the hosted control center and infrastructure controls listed in [SECURITY-REPORT.md](SECURITY-REPORT.md).
- Establish privacy terms, retention/deletion operations, backup restore evidence, monitoring, incident response, support, and rollback ownership.
- Benchmark retrieval before adding embeddings, temporal consolidation, or additional memory backends.
