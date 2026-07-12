# Ninai MVP architecture

## Product promise

Ninai stores durable memory locally, controls which scopes each AI client may access, and sends compact provenance-backed context packets rather than the full vault.

## Data flow

```text
Existing MCP tool (Linear, GitHub, etc.)
        ↓
Claude Code PostToolUse hook
        ↓
Durability + secret filter
        ↓
Local SQLite vault
        ↓
Permission check for the requesting client
        ↓
Hybrid lexical, recency, importance and confidence ranking
        ↓
Token-budgeted context packet with provenance
        ↓
Claude Code or another MCP client
```

## Why this MVP does not use Cognee yet

Cognee is a capable graph-memory platform, but adding it to the current MVP would create another installation and debugging surface. Ninai first needs to establish its differentiated layer: capture from existing tool workflows, scoped permissions, provenance, and minimum-context delivery.

Future backend evaluation should begin with a `MemoryBackend` interface and compare:

- the current SQLite/FTS implementation;
- the existing Jarvis SQLite + LanceDB engine;
- Cognee as a graph-memory backend;
- Mem0/OpenMemory as an interoperability target.

## Retrieval method

PACT is implemented as two pure stages after permission-filtered SQL retrieval. Ranking combines:

- lexical overlap;
- FTS result position;
- type-aware recency decay;
- importance;
- extraction confidence;
- access reinforcement.

The context composer then greedily selects the highest-ranked memories that fit both the item and token limits. Every selected fact includes its source URI. The weights are explicit hypotheses in `retrieval.py`, not a claim of academic novelty, and should later be tuned against evaluation fixtures.

The policy boundary is deliberately earlier than ranking:

```text
client identity + purpose
        -> granted scopes
        -> SQL candidate filter
        -> PACT ranking
        -> token-budget composition
        -> disclosure log
```

This prevents unauthorised rows from entering search results, ranking code, or context composition.

## Module boundaries

- `models.py` contains dependency-free domain values.
- `store.py` is the SQLite adapter and policy enforcement point.
- `retrieval.py` contains deterministic ranking and packet composition.
- `hook_capture.py` is the host-event capture policy.
- `server.py` and `cli.py` are transport adapters.

The current shape is intentionally smaller than the old Jarvis engine. Vector search, local-model extraction, consolidation, and a browser UI remain optional future adapters rather than runtime requirements.

## Website architecture

The marketing site is a Next.js application under `website/` with `output: "export"`. It uses React only for focused interactions such as the permission/revocation model and copyable install commands; all pages are emitted as static HTML for deployment.

- `app/` owns routes, metadata, and the visual system.
- `components/` contains shared navigation, footer, command, and disclosure components.
- `public/` contains the supplied Ninai brand assets and crawler-facing files.
- `scripts/validate_website.py` validates exported files, metadata, H1 count, 404 policy, internal links, anchor targets, and required launch assets.

The site avoids third-party analytics, runtime API calls, fake customer proof, and claims beyond the implemented MVP.

## Security boundaries

Present in the MVP:

- explicit per-client scope grants;
- secret-pattern rejection and hook redaction;
- local-only database;
- provenance on every memory;
- append-only access records (by convention; not yet cryptographically tamper-evident);
- soft deletion;
- bounded memory size and context budgets.

Not present yet:

- SQLCipher/full-database encryption;
- OS keychain integration;
- signed and notarized desktop releases;
- prompt-injection classifier;
- cryptographic audit chains;
- zero-knowledge sync;
- independent security audit.

Do not describe the MVP as production secure.

## Lessons from jarvis-cognitive-memory

Jarvis was reviewed as prior product research. Ninai does not copy or rename its source. Post-MVP work may independently evaluate these concepts and reuse only benchmark fixtures or public interfaces where licensing and product fit are clear:

1. Type-aware ontology and decay curves.
2. LanceDB embedding index and local Ollama extraction.
3. Consolidation, supersession and reflection.
4. Query-less priming.
5. Existing test cases and benchmark fixtures.
6. FastAPI/HTMX local memory browser.

Any accepted capability must sit behind Ninai's permission and disclosure boundary, preserve local provenance, keep derived indexes rebuildable, and demonstrate measurable value before adding runtime dependencies.
