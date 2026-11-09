# Ninai competitive decision — 9 November 2026

## Decision

The generic idea is already implemented by multiple products. Cross-assistant memory, local ownership, permissions, provenance, graphs, and token-efficient retrieval are not individually unique. Ninai has working foundations, but no demonstrated competitive advantage yet. Continue only with a narrower customer and an independently measurable workflow advantage; do not expand simultaneously into individual, team, and enterprise products.

Recommended initial customer hypothesis: solo consultants and small software agencies switching between coding assistants across multiple client projects. The proposed job is to resume the correct project, carry forward current decisions and commitments, and prevent accidental disclosure across clients. This is a hypothesis requiring interviews and comparative trials, not established demand or a feature already delivered completely.

## Evidence boundaries

Research used public official documentation and the local repository. Three independent subagents investigated Living Brain, adjacent alternatives, and Ninai's implementation. No competitor account was created, no paid plan purchased, and no competitor workflow was exercised end to end. Published capabilities describe vendor claims, not verified deployment quality. Missing public evidence is classified as unknown rather than absent. Ninai's current uncommitted changes were preserved.

## Living Brain versus Ninai

| Capability | Living Brain published evidence | Ninai code/evidence |
| --- | --- | --- |
| Cross-assistant memory | OAuth connector, coding-tool integrations, API/SDK/CLI | Local tools and separate hosted connector implementation; compatibility bounded by recorded host tests |
| Knowledge organization | Extracts facts, routes into maintained pages, saves versions and sources, embeds and links pages | Compact typed records; optional session archive; no equivalent compiled-page/graph pipeline |
| Search | Semantic and keyword candidates merged/ranked | Local FTS5/BM25 and weighted ranking; hosted PostgreSQL full-text search; no semantic index |
| Permission filtering | Checks before policy scores; permission/provenance checks on graph links | Local scopes before retrieval; stronger hosted workspace/project/action grants |
| Identity and roles | Organization keys, subject ownership, roles; OAuth tool scopes | Hosted signed identity plus live membership/connection checks; local identity is an environment setting |
| Sources | Source references, page versions, contested-page resolution | Source URI and confidence; these are caller-supplied metadata, not verified factual evidence |
| User control | Archive, permanent page deletion, versions, Markdown export | Edit, soft deletion, permissions, disclosure records; permanent purge/backup lifecycle incomplete |
| Deployment | Standard hosted; Business assesses dedicated/customer-cloud/on-prem/air-gapped configurations | Working local mode; separate hosted mode; signed releases and operating gates pending |
| Ease of setup | ChatGPT/Claude sign-in path without keys; interactive setup | Installer and desktop guidance; five-minute clean-machine target not yet proven |
| Team product | Organization roles, three-seat Workspace, Slack/Telegram/webhooks | Hosted workspace/member/project primitives; no demonstrated complete collaboration/admin product |
| Retrieval quality | Published internal LoCoMo evaluation | Functional/policy tests and host smoke evidence; no matched comparative recall benchmark |

Living Brain is a ChatAndBuild product. ChatAndBuild's site says its legacy coding agent is retired; these links do not identify two independent competitors.

## Corrections to earlier differentiation

- Permission checks before ranking are explicitly documented by Living Brain. This cannot be described as Ninai-exclusive.
- Living Brain already documents sources, versions, conflicts, export, OAuth scopes, organizational roles, and key revocation.
- Their Business plan offers private deployment assessment. Do not call them cloud-only or claim they cannot serve enterprises.
- Basic Memory already documents fully local operation, portable files, cross-assistant knowledge, team roles, project visibility, and audit logs. Local ownership alone does not defend Ninai's position.
- A 600-token default packet is a budget, not evidence of superior efficiency. Lower context can reduce answer quality; compare correctness and cost together.
- SQLite simplicity is an implementation advantage for packaging, not a customer moat. Hybrid search can be embedded locally.

## Critical Ninai implementation gaps

This section records the pre-fix audit that motivated the implementation.
The subsequent local project/action permission change addresses items 1 and 3
for API access; see [upgrade behavior](LOCAL-PROJECT-PERMISSIONS.md).
The trust-boundary, encryption, deletion, and market-validation gaps remain.

1. Local durable memories have a `scope` field but no project identifier. Granting `project` access permits that category across local durable memories. Project IDs used for sessions do not solve this durable-memory boundary. See `engine/src/ninai/store.py` schema and recall.
2. Local client identity comes from `NINAI_CLIENT_ID` in `engine/src/ninai/config.py`. Applications with the same operating-system account and filesystem/shell access can bypass the API or change identity. The local interface is a cooperative sharing boundary, not a sandbox against hostile local software.
3. Local `remember` has no independent write grant; `forget` uses scope access rather than a separate delete capability. Hosted read/propose/auto-activate grants are more granular. See `engine/src/ninai/server.py` and hosted store.
4. `restricted` and `blocked` sensitivity labels do not enforce additional disclosure rules. See `engine/src/ninai/models.py`.
5. SQLite is not encrypted by Ninai. Owner filesystem permissions exist; keychain-managed encryption does not.
6. Revocation stops subsequent Ninai disclosures. It cannot retract information already sent to another assistant or provider.
7. Soft deletion excludes content from retrieval but is not verified physical erasure. Full derived-data and backup deletion is incomplete.
8. Local duplicate consolidation, long-term quotas/retention, and recall-quality evaluation are incomplete. Lexical recall can miss paraphrases.
9. The last suite result was 61 engine tests and 107 cloud tests, with 17 skipped database integration tests. Tests using fake services do not prove real signup, provider authorization, installation, database isolation, or usability.

## Individuals, teams, enterprises

| Segment | Actual job | Ninai missing for a credible offer | Recommendation |
| --- | --- | --- | --- |
| Individual using several assistants | Resume useful context without repeating work; correct and inspect memory | Reliable install, automatic but consented capture, project boundaries, semantic recall, useful import/export, recovery | Choose one frequent workflow; broad consumer second-brain positioning is crowded |
| Consultant/small agency | Keep client projects separate; transfer decisions between assistants; handle handover/offboarding | Per-client/project IDs, separate read/propose/edit/delete rights, member identity, review conflicts, deletion propagation, polished collaboration | Strongest initial hypothesis, but must beat existing tools in observed trials |
| Enterprise | Enforce identity, access, lifecycle, and operational commitments across people/tools | SSO provisioning/deprovisioning integration, policy administration, data residency, key/backup operations, reliable audit/export, restore evidence, support and service commitments | Later paid design partnership only; do not market enterprise readiness now |

OAuth login alone does not establish enterprise SSO/SCIM administration. Infrastructure-provider certifications do not certify Ninai. These requirements should be scoped to an actual customer rather than built speculatively.

## Potential opportunity to test

Proposed product promise: “Resume the right client project in your next assistant, with current decisions and an inspectable sharing receipt.” This must include client isolation, not just context portability.

Possible differentiators to earn:

- A guided handoff that carries decisions, unresolved commitments, constraints, and current state into the next assistant, while explaining why each item was selected.
- Correcting a decision updates future handoffs and exposes superseded evidence rather than silently keeping conflicting facts active.
- Removing a source invalidates dependent memory and indexes, with clear exceptions for facts still supported by another source.
- A user can preview, approve, and inspect the exact packet and recipient. Budgets vary with task needs.
- Clean installation and first verified success for a beginner without credentials or terminal troubleshooting in the normal local path.

None is a proven exclusive feature. Copyability remains high; durable advantage would come from measured reliability, habitual workflow fit, integrations, and distribution.

Living Brain's capture documentation explicitly says source deletion leaves already-derived pages intact. This is a concrete lifecycle scenario to test, not grounds to claim weak security. Ninai does not yet solve complete cascading deletion either.

## Comparative validation and decision gates

Use Living Brain and Basic Memory plus a plain Markdown/project-instructions baseline. Add OpenMemory where appropriate. Test identical synthetic projects with consented disposable accounts; do not submit real customer information.

Fixtures: two clients with similar names; conflicting deployment decisions; an old and updated deadline; paraphrased questions; deliberately forbidden memories; deleted sources; interrupted setup; revoked access; assistant switching; malicious instructions inside a source. For local same-user filesystem attacks, report the trust boundary honestly rather than treating API grants as protection.

Measure installation-to-first-success time, assistance needed, correct latest decision, cross-project disclosure, answer relevance, source correctness, correction propagation, revocation on the next API request, recovery success, full processing cost, and median/p95 latency. Hold answering model and task configuration constant where supported. Record version/date/settings and differences in capabilities. Do not compare unlike token counters or a default budget against competitors' measured totals.

Proposed two-week decision experiment (targets, not results):

1. Interview 8–12 consultants/agencies using two or more assistants; establish existing workarounds and frequency/cost of context loss.
2. Run baseline trials before building broadly. Confirm whether any pain remains after using existing products.
3. Close Ninai's project/action permission gaps before testing the isolation promise.
4. Have five independent users perform first setup and repeated handoffs. Proposed gate: at least four finish unaided within five minutes on the explicitly supported environment; zero unauthorized disclosures in the defined fixture; latest decisions correctly recalled in at least 90% of defined handoff tasks.
5. Ask for paid pilots at a concrete, cost-informed price. Proposed gate: at least three independent customers commit to pay and use it weekly. Compliments or hypothetical willingness are insufficient.
6. Continue if the workflow advantage is observed and buyers commit. Narrow or integrate with existing storage if users value the control/handoff interface but competitors retrieve better. Stop or pivot if existing tools solve the same job satisfactorily and no paid need emerges.

Pricing remains an experiment: individual convenience plan; team project/seat subscription if collaboration proves valuable; enterprise contracts only with scoped deployment/support economics. Do not invent revenue, margin, willingness to pay, or pricing advantage.

## Primary sources

Living Brain:

- https://chatandbuild.com/ — product/company relationship and retired coding agent
- https://docs.livingbrain.com/docs/concepts — compilation, graph, provenance and conflicts
- https://docs.livingbrain.com/docs/design-policies — eligibility and permission checks before scoring
- https://docs.livingbrain.com/docs/authentication — organization roles, subject identity, key controls
- https://docs.livingbrain.com/mcp/sign-in — OAuth scopes and interactive setup
- https://docs.livingbrain.com/docs/search-ranking — hybrid retrieval
- https://docs.livingbrain.com/docs/pages — versions, archive, permanent page deletion, export
- https://docs.livingbrain.com/docs/capturing — source deletion and derived pages
- https://docs.livingbrain.com/docs/importing — import and deletion behavior
- https://livingbrain.com/pricing — paid plans and assessed private deployments
- https://docs.livingbrain.com/docs/benchmarks — internal evaluation scope
- https://livingbrain.com/ — headline benchmark claims

Adjacent alternatives:

- https://docs.basicmemory.com/start-here/quickstart-local — local hybrid search and installation
- https://www.basicmemory.com/security — local ownership, tenant isolation, project visibility, roles, audit, SSO; vendor says it does not yet hold its own SOC 2 certification
- https://docs.basicmemory.com/start-here/what-is-basic-memory — shared persistent knowledge
- https://docs.basicmemory.com/cloud/routing — project routing
- https://docs.basicmemory.com/start-here/quickstart-cloud — guided first note and connector onboarding
- https://mem0.ai/openmemory — project memory, coding integrations, visibility and access history
- https://docs.mem0.ai/open-source/setup — self-hosted alternative
- https://github.com/mem0ai/openmemory/blob/main/openmemory-archive/README.md — archived legacy local dashboard; do not describe it as current maintained product
- https://help.getzep.com/governance — traceability and organization/agent governance
- https://help.getzep.com/policy-based-access-control — per-request policy enforcement and default-deny Context MCP
- https://help.getzep.com/security-compliance — published enterprise security/deployment options
- https://help.getzep.com/context-retention — lifecycle/deletion and backup exceptions
- https://docs.letta.com/configuration/memory — Git-backed memory maintenance
- https://github.com/letta-ai/letta-docs-md/blob/main/concepts/shared-memory/index.md — organization shared memory repositories

Zep's documented governance means enterprise memory permissioning is also an occupied category. Mem0/OpenMemory overlaps on coding-project memory and visibility/access history. Letta's agent runtime differs from a neutral memory broker but provides established memory maintenance and shared memory. Do not prioritize matching every feature; select competitors according to the specific user job.

Benchmark caution: Living Brain's homepage reports 464 ms retrieval and 3.7 s total, while the benchmark document reports 592 ms and 11.2 s for its dated run. These configurations must be clarified before comparison. The documents do not establish independent superiority, and Ninai has no equivalent result yet.
