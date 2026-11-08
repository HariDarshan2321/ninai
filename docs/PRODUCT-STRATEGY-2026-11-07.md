# Ninai product and market position

Research date: 7 November 2026

## Current product

Ninai gives multiple AI assistants one user-controlled memory. The complete
local vault stays on the user's computer. Each assistant receives only memories
from areas the user allowed, with source provenance and a disclosure record.

The current Mac product supports Claude Code and Codex, with Gemini CLI in beta.
It includes automatic project-session handoff, manual memory management,
per-assistant access controls, immediate revocation, and a desktop control panel.

## The strongest differentiation

Persistent memory alone does not differentiate Ninai. Mem0, Zep, Letta,
Epicenter, native assistant memory, and multiple local MCP projects already
address persistence and retrieval.

Ninai's strongest combination is:

1. One memory across competing assistants.
2. A local vault owned by the user.
3. Separate access choices for each assistant.
4. A source attached to every stored memory.
5. Immediate revocation and a history of disclosures.
6. Automatic continuity between coding sessions.

The simplest product description is:

> Ninai is private, permissioned memory shared by your AI assistants.

For the current developer audience:

> Switch between Claude, Codex, and Gemini without repeating your project or
> giving every assistant your complete history.

## Competitive landscape

| Product or category | Primary strength | Overlap with Ninai | Ninai opportunity |
| --- | --- | --- | --- |
| Mem0 | Developer memory infrastructure and broad integrations | Storage, extraction, retrieval | User-owned cross-assistant control rather than an application SDK |
| Zep | Enterprise context graphs, temporal context, access controls | Provenance, governance, agent context | Local personal vault, visible per-assistant disclosure and revocation |
| Letta | Stateful long-running agents and memory management | Persistent agent memory | Neutral memory shared by separate assistants rather than one agent runtime |
| Epicenter | Open, local-first shared personal data | Local ownership and portability | Fine-grained assistant permissions, disclosure history, coding handoff |
| Native Claude, ChatGPT, and Gemini memory | Simple experience inside one provider | Personalization and continuity | Provider independence and explicit control over cross-provider sharing |
| Local MCP memory servers | Easy local persistence | SQLite, local operation, MCP | Product-quality onboarding, policy enforcement, provenance, and audit UX |

No single technical capability above is unique. The product can become distinct
by making the complete trust model easy for ordinary users. The defensible asset
would be a trusted workflow, deep integrations, high-quality capture and recall,
and a durable record of decisions that users depend on.

## What to benchmark

### Continuity

- Time from opening a second assistant to useful work
- Context repetitions avoided per task
- Successful handoffs between different providers

### Memory quality

- Useful memories returned
- Irrelevant memories returned
- Important decisions missed
- Outdated memories returned as current
- Memories with a valid, understandable source

### Control and safety

- Cross-project and personal-memory isolation
- Denial immediately after revocation
- Secrets rejected before storage
- Complete disclosure records
- Time for a user to understand and change access

### Product usability

- Install completion without founder assistance
- Time to connect the first and second assistant
- Time to the first successful memory handoff
- Percentage of users who understand where local data lives
- Weekly users completing a cross-assistant handoff

Raw database latency matters only after the product returns the correct memory.
Recall precision, first-success time, and user trust are better headline measures.

## Current risks

1. The present audience is developers, while the desired onboarding audience is
   non-technical. Mainstream ChatGPT, Claude, and Gemini desktop/web connectors
   do not yet exist.
2. The Mac installer still uses Terminal, Python, pip, and local app building.
   A signed double-click installer must replace this flow.
3. The Windows preview still depends on Python and lacks signed packaging and
   lifecycle hooks.
4. Broad `project` memory can become noisy across repositories. Capture quality,
   project identity, consolidation, and retrieval evaluation require benchmarks.
5. Hosted operation needs the documented security, retention, backup, and
   external acceptance gates before public use.

## Product sequence

### Phase 1: reliable developer product

- Signed Mac package with no Terminal or Python requirement
- Signed Windows package with bundled runtime
- In-app connector detection, repair, and verification
- First-run checklist ending in a real cross-assistant recall
- Memory-quality feedback and project-specific isolation

### Phase 2: small teams

- Shared project decisions with member-level permissions
- Review and approval for proposed memories
- Decision supersession and conflict handling
- Team activity and export

### Phase 3: broader assistants

- Mainstream desktop and hosted assistant connectors where host APIs permit them
- Clear separation between personal, project, and team context
- Organizational policy, retention, and audited hosted deployment

## Business model hypotheses

| Plan | Customer | Possible offer |
| --- | --- | --- |
| Free local | Individual developer | Local vault, two assistants, core permissions |
| Pro | Multi-agent power user | Unlimited assistants and projects, advanced recall and encrypted backup option |
| Team | Small engineering team | Shared decisions, review workflow, administration and support |
| Enterprise | Security-sensitive organization | Hosted or managed deployment, policy, audit export, retention and SSO |

Pricing should follow observed willingness to pay. The immediate commercial test
is whether users repeatedly complete cross-assistant handoffs and would pay to
avoid context repetition while retaining control.

## Near-term decision

Continue the product, but focus development on installation, first success, and
memory quality. Do not describe Ninai as a generic memory database. Its clearest
position is a neutral trust and continuity layer between a person and multiple AI
assistants.
