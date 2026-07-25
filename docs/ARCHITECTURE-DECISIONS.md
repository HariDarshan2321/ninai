# Hosted architecture decisions and open questions

## Accepted decisions

1. **Local remains local.** Hosted mode is an independent opt-in deployment. There is no implicit upload, migration, or sync from SQLite.
2. **PostgreSQL is authoritative for hosted mode.** Workspace IDs are carried through hosted records and queries; derived search indexes are not an authorization boundary.
3. **OAuth is the normal hosted boundary.** An external issuer owns login, consent, client registration, and token issuance. Ninai validates asymmetric JWTs and resolves signed claims to live database identities. Explicit PAT mode is limited to trusted self-hosting and resolves opaque token digests to fixed principals.
4. **Authorization precedes retrieval.** Only active client grants for the authenticated workspace may contribute candidates. Purpose and identity in request bodies are not trusted as authorization.
5. **Review-first is the default write posture.** `propose_memory` and `remember` are distinct operations and active writes require a separate grant.
6. **Provenance and disclosure are product invariants.** Source URI is mandatory; read tools record disclosure events.
7. **Streamable HTTP MCP is the cross-provider interface.** Host-specific adapters should remain thin and must not weaken store policy.
8. **Revocation is checked live.** A client, membership, workspace, or user revoked in PostgreSQL is rejected on the next authenticated request even if its JWT has time remaining.
9. **The hosted control center is a separate adapter.** It must receive identity from production authentication, never from request JSON or an untrusted header.
10. **Compatibility claims require real-host evidence.** Unit or protocol tests prove implementation, not Claude/OpenAI product compatibility.

## Open questions before general availability

- Which OAuth/OIDC issuer and client-registration model will be supported for the beta, and how will each host's redirect/discovery behavior be tested?
- How are users, workspaces, projects, and initial client connections provisioned without direct SQL?
- Will the control center share a process/domain with MCP or deploy as a separate authenticated application?
- What are the retention and hard-deletion timelines for memories, sources, idempotency records, disclosures, and backups?
- Which deployment region, subprocessors, availability target, recovery objectives, and support commitment will be published?
- What rate limits and quotas apply per connection and workspace?
- How will schema migrations, rollback, backup restore, key rotation, and incident revocation be operated and audited?
- Is PostgreSQL lexical search sufficient for beta quality, and what benchmark would justify embeddings or reranking?
- How should conflict groups, supersession chains, and freshness policy receive richer visualization beyond the current status/source fields in the control center?
- Which exact Claude, Codex, OpenAI Responses API, and Anthropic API versions passed the release gate?
- What security review is required before external user data is accepted?
