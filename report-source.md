# Ninai MVP launch and architecture assessment

**Audience:** Ninai founder and launch operator  
**Date:** 6 September 2026  
**Decision:** Controlled beta can open today; unrestricted public launch remains conditional.

## Scope and assumptions

This report evaluates the local Mac MVP for Claude Code and Codex, the public website and Auth0-backed account/download flow, and the read-only platform dashboard. Hosted vaults and shared connectors remain an invited preview. It combines repository inspection, automated tests, an isolated fresh Mac installation, live endpoint/browser checks, and current primary-source research. It does not claim an independent security audit or a completed test by an unrelated external user.

## Direct answer

Ninai is not made obsolete by knowledge graphs. The market has clearly validated agent memory, and several competitors already offer more sophisticated retrieval. Ninai's credible wedge is narrower: a local-first, cross-provider coding-agent memory with permission checks before retrieval, source provenance, revocation, disclosure logs, and bounded context. That is useful if it is demonstrably easier and safer than assembling those pieces yourself.

The present retrieval engine is an appropriate MVP baseline, not a defensible long-term retrieval advantage. Do not add a knowledge graph merely to match a feature list. First measure failures. Add a graph backend when entity-centric, multi-hop, temporal, or contradiction queries measurably fail and the improvement justifies extraction cost, extra dependencies, and privacy risk.

## Launch verification

| Area | Result | Evidence / limitation |
| --- | --- | --- |
| Repository and deployment | Pass | `main` is clean and synchronized at `3fa7b13`; Render readiness and public Vercel pages respond. |
| Local memory engine | Pass | 55/55 tests; capture, secret rejection/redaction, provenance, scope-before-ranking, budgets, revocation, and disclosure logging. |
| Demonstration memory flow | Pass | One captured tool outcome produced a 99-token packet from an estimated 1,197-token source (91.7% reduction); recall returned no facts after revocation. |
| Cloud/account service | Pass | 101/101 tests against disposable PostgreSQL 15 with zero skips; 12/12 cross-provider service checks passed. |
| Website | Pass | TypeScript, production build, static validator, metadata, canonical URL, crawler assets, internal links, and all principal production pages passed. |
| Fresh Mac install | Pass with product caveat | Exact installer completed in an isolated macOS home with Python 3.13, built and ad-hoc signed `Ninai.app`, created an empty local vault, kept capture off, and passed doctor/signature verification. Install footprint was about 166 MB; empty vault about 106 KB. |
| Signed-in setup/download | Pass | Real signed-in setup rendered the published command `bash ~/Downloads/install-ninai-macos.sh`; authenticated download recorded successfully; anonymous download returned 401. |
| Auth routing | Partial | Real sign-in/admin redirect works. Signup URL correctly issues an Auth0 authorization redirect with PKCE and `screen_hint=signup`, but a brand-new unrelated user was not created during this audit. |
| Admin authorization | Conditional | UUID allowlisting works, but production currently authorizes `cbce38e7-23a4-4a3d-9049-bd0574ad1588`, whose profile is `darshan.t.mn@gmail.com`; the separate `darshan@ninai.io` record has no dashboard login. Resolve this if the intended administrator must be the Ninai mailbox identity. |
| External acceptance | Not complete | No fresh, unrelated tester completed signup → download → install → real Claude Code → real Codex handoff → revoke during this audit. Automated and earlier real-host checks do not replace this. |

## Go / no-go

**Go today for a controlled beta** with a small invited cohort and direct support. **No-go for claiming a fully validated public launch** until:

1. The intended administrator signs in as `darshan@ninai.io`, its internal UUID is verified, and the Render allowlist is changed to that UUID (or the founder explicitly chooses the current Google identity).
2. One unrelated Mac user completes the whole funnel, including a real Claude Code-to-Codex handoff and revocation.
3. The launch copy clearly states Python 3.11+, macOS-only support, the roughly 166 MB current install footprint, and that the app is locally built/ad-hoc signed rather than a notarized binary.

## What Ninai is actually doing

Ninai stores compact durable facts and outcomes in local SQLite. On recall, it identifies the requesting client, limits candidates to explicitly granted scopes in SQL, ranks those candidates using lexical relevance, recency, importance, confidence, and prior access, then composes a token-bounded packet containing source URIs and records the disclosure. Session/tool capture is consented and filtered; raw tool output and obvious credentials are not durable memory.

That architecture optimizes the boundary around memory rather than inventing a novel retrieval algorithm. The strongest product claim is not “better AI memory than everyone”; it is “portable project continuity across supported coding agents, on your Mac, with inspectable permissions and provenance.”

## Why not a knowledge graph now

Knowledge graphs are valuable when relationships are first-class: “Which decision replaced this one?”, “How is service A connected to incident B?”, point-in-time state, multi-hop questions, and contradiction/invalidation. Graphiti explicitly combines temporal edges, provenance-bearing episodes, semantic/keyword/graph retrieval, but its standard quick start needs an LLM/embedding provider and a graph backend. Mem0 reports graph memory as a ranking boost for entity-centric and multi-hop retrieval; notably, its paper reports only about a 2% overall gain for the graph variant over base Mem0 on LoCoMo. This is evidence for selective value, not proof that every memory product must start with a graph.

Ninai's current flat fact model will become weak when users accumulate aliases, evolving relationships, conflicting decisions, and months of state. The right sequence is:

1. Ship the controlled beta and record retrieval misses without collecting private vault contents automatically.
2. Build a local evaluation set covering exact fact, temporal update, contradiction, multi-hop dependency, permission leakage, and abstention.
3. Introduce a `MemoryBackend` boundary and compare current SQLite/FTS against embeddings and an embedded temporal graph option.
4. Promote a graph only if it improves target tasks materially under installation-size, latency, cost, provenance, and permission constraints.

## Competitive reality

- Graphiti/Zep already provides temporal knowledge graphs, hybrid retrieval, provenance-bearing episodes, contradiction invalidation, and MCP integration.
- Mem0 already provides extraction, consolidation, hybrid memory, entity scoping, and native graph-assisted ranking.
- Cognee already provides self-hosted graph/vector memory, sessions, provenance options, Claude Code integration, and broader ingestion.
- Letta offers agent-centric archival memory and retrieval.
- Model vendors are improving native continuity: ChatGPT synthesizes long-term memory, while Codex uses thread history and compaction. These are important substitutes, though not the same as one locally controlled vault shared across vendors.

So, “persistent memory” alone is commoditized. Ninai must win on a workflow and trust wedge, not the category name. Its highest-value differentiation to test is: **cross-agent coding continuity with local custody, explicit disclosure control, and verifiable sources, installed in minutes.**

## Risks and recommended next work

1. **Activation risk:** the installer downloads/builds a large Python environment and requires Python 3.11+. Measure funnel failures before adding retrieval sophistication.
2. **Retrieval quality risk:** PACT weights are hypotheses and have no product benchmark. Create an evaluation harness before marketing retrieval quality.
3. **Capture-quality risk:** compact extraction can omit nuance; automatic session capture is consented but needs real-world precision testing.
4. **Trust risk:** the vault is not encrypted and the app is not notarized. Keep claims precise and prioritize notarization/keychain/encryption based on user demand.
5. **Identity risk:** fix or explicitly accept the founder account mismatch before widening access.

## Primary sources

- [LongMemEval (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/d813d324dbf0598bbdc9c8e79740ed01-Paper-Conference.pdf)
- [LoCoMo paper (ACL 2024)](https://aclweb.org/anthology/2024.acl-long.747.pdf)
- [Mem0 paper](https://arxiv.org/abs/2504.19413)
- [Mem0 graph memory documentation](https://github.com/mem0ai/mem0/blob/main/docs/platform/features/graph-memory.mdx)
- [Graphiti overview](https://help.getzep.com/graphiti/getting-started/overview)
- [Graphiti quick start](https://help.getzep.com/graphiti/getting-started/quick-start)
- [Graphiti MCP server](https://help.getzep.com/graphiti/getting-started/mcp-server)
- [Zep temporal knowledge graph paper](https://arxiv.org/abs/2501.13956)
- [Cognee repository](https://github.com/topoteretes/cognee)
- [Letta archival-memory API](https://docs.letta.com/api/python/resources/agents/subresources/passages)
- [OpenAI on Codex context and compaction](https://openai.com/index/unrolling-the-codex-agent-loop/)
- [OpenAI on ChatGPT memory](https://openai.com/index/chatgpt-memory-dreaming/)

## Limitations

Competitor benchmark numbers are vendor-authored or evaluated on research benchmarks that do not directly represent Ninai's permissioned coding-agent workflow. No comparative benchmark was run against Ninai. Live Auth0 signup by a new external identity, ordinary-user production denial, a notarized distribution path, and a fresh external real-host handoff remain unverified.
