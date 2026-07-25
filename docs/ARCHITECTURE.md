# Ninai MVP architecture

## Product promise

Ninai stores durable memory locally, controls which scopes each AI client may access, and sends compact provenance-backed context packets rather than the full vault.

## Deployment modes

Local mode is local-first: SQLite remains on the user's machine and nothing is uploaded or synced automatically. The repository also contains a separate, explicit opt-in hosted beta for clients that cannot reliably reach a local MCP server. Hosted mode uses PostgreSQL and authenticated Streamable HTTP MCP; it does not read or synchronize the local vault. It is implemented and automated-testable, and its local real-host Claude Code/Codex gate passed on 25 July 2026. Production HTTPS/OAuth deployment remains pending.

Both modes share the same core invariants: permission checks happen before retrieval, every memory retains provenance, and disclosures are audited. Hosted storage must not bypass those controls.

Hosted data flow:

```text
Claude, Codex, or an API integration
        -> HTTPS Streamable HTTP MCP + bearer token
        -> OAuth JWT or explicit self-hosted PAT validation + live principal check
        -> active workspace/client scope grants
        -> PostgreSQL retrieval or review-first write
        -> provenance-backed result + disclosure log
```

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
- `desktop/` is the owner-facing desktop control panel (another transport adapter).

The current shape is intentionally smaller than the old Jarvis engine. Vector search, local-model extraction, consolidation, and a browser UI remain optional future adapters rather than runtime requirements.

## Desktop app

`desktop/` is a native window (PyWebView → system WebView) that gives the vault
owner a UI over the engine: Today, Memories, Sources, Permissions, and Activity.
It is a thin transport adapter, exactly like `server.py` and `cli.py`:

- `desktop/app.py` builds the `MemoryStore`, the bridge, and the window; it is the
  `ninai-app` entry point (optional dependency `pywebview`, installed via the
  `desktop` extra).
- `desktop/api.py` is the `DesktopApi` JS↔Python bridge — thin wrappers over
  `MemoryStore` returning `{ok, data}` / `{ok, error}` envelopes. No policy lives here.
- `desktop/web/` is dependency-free static HTML/CSS/JS.

Trust model: the desktop app runs as the **local operator** (it calls the store with
no `client_id`), i.e. with full owner access — deliberately unlike an untrusted MCP
client, which is scope-restricted and logged. The app must never be exposed over a
network. It shares `~/.ninai/ninai.sqlite3` with the MCP server; concurrency is safe
because the store uses WAL and `busy_timeout`. The app is not a security boundary and
the vault is not encrypted; the `sensitivity` label is display-only and does not yet
affect disclosure.

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

The hosted implementation adds tenant-bound PostgreSQL records, asymmetric JWT validation against an external issuer, live membership/client revocation checks, distinct propose/auto-activate grants, idempotent writes, and disclosure records. These controls have repository tests; they are not an independent security audit or proof of a hardened production deployment. See [SECURITY-REPORT.md](SECURITY-REPORT.md).

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
