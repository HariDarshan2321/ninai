# Ninai Desktop App — Design Spec

- **Date:** 2026-07-12
- **Status:** Implemented (engine `update()` + `sensitivity`, `DesktopApi` bridge,
  `ninai-app` window, five web screens; 42 engine/bridge tests passing; UI verified
  against the real engine).
- **Scope tier:** "Polished app I use myself now" — a real macOS window wired to the
  live engine. NOT code-signed/notarized, NO SQLCipher/keychain. Those belong to
  the later "shippable to strangers" tier and are explicitly out of scope here.

## 1. Goal

Give the vault owner a real desktop application — a window with clickable screens —
to see and control their Ninai memory, permissions, and disclosure audit trail,
backed by the existing hardened Python engine. No browser tab; a genuine app window.

Success criteria:
- Launches a native macOS window via `ninai-app`.
- Shows five screens (Today, Memories, Sources, Permissions, Activity) backed by real
  engine data.
- Owner can add, search, view-with-provenance, edit/correct, and delete memories;
  toggle each AI client's scope permissions; and read the full access log.
- Reuses the existing engine unchanged except for two small, additive, tested changes
  (see §4). Follows `docs/BRAND.md`. Truthful about what is not yet built.

## 2. Non-goals (explicitly deferred)

- Code-signing, notarization, `.dmg` installer, Gatekeeper handling.
- SQLCipher / keychain / at-rest encryption.
- Live connectors (Gmail/Calendar OAuth or import), extraction pipeline.
- Windows/Linux builds; mobile.
- Full automated UI/E2E test coverage (a boot smoke test is in scope; full UI
  automation is not).
- Any change to the MCP policy boundary or the untrusted-client rules.

## 3. Architecture

A single native window (PyWebView → macOS system WebKit) renders a web UI. Python
calls the existing engine in-process. No Rust, no separate server, no network egress.

```
Ninai.app  (native window, PyWebView)
   Web UI  ──  Today · Memories · Sources · Permissions · Activity
      │  window.pywebview.api.*   (in-process JS <-> Python bridge)
   DesktopApi  (thin Python adapter — no business logic)
      │  direct calls
   MemoryStore  (existing hardened engine, unchanged)
      │
   ~/.ninai/ninai.sqlite3   ← same vault the MCP server uses
```

### Trust model
The desktop app runs as the **local operator**: it constructs a `MemoryStore` and calls
its methods with `client_id=None`, which the engine already treats as the vault owner
with full access. This is deliberately different from an MCP client (which is untrusted
and scope-restricted + logged). The desktop app is the owner's control panel and may see
and edit everything. It must never be exposed over a network or to another process.

### Concurrency
The app and the MCP server both open `~/.ninai/ninai.sqlite3`. This is safe because the
store already uses WAL journaling and `PRAGMA busy_timeout=5000` (added during engine
hardening). Each call opens and closes its own connection via the store's
`_connection()` context manager.

## 4. Engine changes (additive, backward-compatible, TDD)

1. **`MemoryStore.update(memory_id, *, content=None, memory_type=None, scope=None,
   sensitivity=None, importance=None, confidence=None)`** — edit a memory in place:
   - Preserves `id`, `source_uri` (provenance), and `created_at`.
   - Bumps `updated_at`.
   - Re-runs `contains_secret` on new content and re-validates memory_type/scope.
   - Refreshes the FTS row for the memory.
   - Returns the updated memory dict, or `None` if no active memory has that id.
     Raises `ValueError` on invalid field values (same contract as `remember`).
2. **`sensitivity` column** on `memories` — nullable `TEXT` added via a guarded
   `ALTER TABLE ... ADD COLUMN` in `_init_db` (backward compatible; existing rows read
   as `normal`). Allowed values: `normal`, `personal`, `restricted`, `blocked`.
   - Display-only in the MVP: shown as a badge and editable via `update`. It does NOT
     yet affect ranking or disclosure (the dossier's sensitivity penalty is post-MVP).
     This limitation is stated in the UI and docs to avoid overclaiming.

## 5. The Python bridge — `DesktopApi`

A single class exposed to JS as `js_api`. Methods are thin wrappers over `MemoryStore`
returning JSON-serializable envelopes: `{"ok": true, "data": ...}` or
`{"ok": false, "error": "<message>"}`. No business logic lives here.

Methods:
- `list_memories(limit)`, `search(query)`, `get_memory(id)`
- `add_memory(content, memory_type, scope, source_uri, sensitivity)`
- `update_memory(id, **fields)`, `delete_memory(id)`
- `list_clients()`, `get_permissions(client_id)`, `set_permission(client_id, scope, allowed)`
- `list_logs(limit)`
- `today()` — open commitments + recent decisions
- `sources()` — memories grouped by `source_uri` scheme with counts + last-seen
- `meta()` — allowed scopes, memory types, sensitivity levels, engine/app version,
  vault path

## 6. Screens

1. **Today** — open commitments (`memory_type="commitment"`) and recent decisions,
   ordered by importance/recency. "What needs attention." No calendar; honest empty
   state.
2. **Memories** — searchable/filterable list (by scope, type). Row: content, type +
   scope + sensitivity badges, source link, confidence, updated_at. Click → detail
   drawer showing full provenance with **Edit** and **Delete**. **Add memory** button →
   form (content, type, scope, source_uri, sensitivity). Secret-rejection surfaced
   inline.
3. **Sources** — read-only. Existing memories grouped by `source_uri` scheme
   (`gmail://`, `linear://`, `claude-hook://`, `cli://`, `conversation://`, …) with
   counts and most-recent timestamp. Banner: "Live connectors (Gmail, Calendar) are not
   available yet; these are the origins of memories captured so far."
4. **Permissions** — one card per known AI client (union of clients seen in the
   `permissions` table plus sensible defaults `claude-code`, `claude-desktop`). Per-scope
   toggles (work/project/preference/personal/finance/health/public) calling grant/revoke,
   each with a plain-English description. Field to add a new client id.
5. **Activity** — access log newest-first: time, client, purpose, scopes, released fact
   count (expandable to the released memory ids), estimated tokens. Read-only. The
   "prove what the AI saw" surface.

## 7. Look & feel

Strictly follows `docs/BRAND.md`:
- "The Return" mark and the context-aperture motif.
- Calm, restrained, trustworthy. **No generic-AI imagery** (no neural nets, glowing
  brains, purple gradients, star fields, floating orbs, glass cards).
- Reuses existing SVG assets (`website/public/assets/ninai-app-icon.svg`, wordmarks).
- Mirrors the website's design tokens; light/dark aware.
- Layout: fixed left sidebar nav (5 items + brand mark) and a main content area.
- The `frontend-design` skill is used during implementation for UI quality.

## 8. Packaging & layout

- New package module `engine/src/ninai/desktop/`:
  - `app.py` — creates the `MemoryStore`, the `DesktopApi`, and the PyWebView window;
    `main()` is the `ninai-app` entry point.
  - `api.py` — `DesktopApi` bridge class.
  - `web/` — static assets: `index.html`, `app.css`, `app.js`, screen modules, icons.
- `pyproject.toml`:
  - `[project.optional-dependencies] desktop = ["pywebview>=5"]`
  - `[project.scripts] ninai-app = "ninai.desktop.app:main"`
  - hatchling wheel config includes `ninai/desktop/web/**` as package data.
- Run: `pip install '.[desktop]'` then `ninai-app`.
- A PyInstaller `.app` bundle is an optional, documented follow-up (unsigned bundles hit
  Gatekeeper friction), not required for self-use.

## 9. Error handling

- Every bridge method returns the `{ok,...}` envelope; the UI renders friendly inline
  errors (e.g., secret-rejected on add/edit) and empty states on every screen.
- Works on a fresh, empty vault (first launch).
- DB-locked is absorbed by `busy_timeout`; a persistent failure surfaces a retry message.
- The app never writes secrets: `add`/`update` go through the same `contains_secret`
  gate as the engine.

## 10. Testing (TDD, per AGENTS.md)

- Engine: `update()` preserves provenance/created_at, re-validates secrets, refreshes
  FTS; `sensitivity` migration is backward compatible and defaults correctly.
- Bridge: `DesktopApi` methods against a temp vault — correct envelope shapes, validation
  errors surfaced, permission toggles reflected, `today()`/`sources()` grouping correct.
- App: a boot smoke test that the window/API initialize and `meta()` responds.
- Run: `python -m unittest discover -s tests -v` from `engine/`.

## 11. Build approach (agents)

After the implementation plan is written, fan out parallel agents:
- Agent 1: engine `update()` + `sensitivity` migration + tests.
- Agent 2: `DesktopApi` bridge + tests.
- Agent 3–4: web UI screens (split across agents), following `BRAND.md`.
Then integrate, wire the bridge, and verify end-to-end by launching `ninai-app` and
driving each screen.

## 12. Open truthfulness guardrails

- Do not describe the app or vault as encrypted/secure; it is not (unchanged from the
  engine's current posture).
- Sensitivity is display-only for now; say so in-app.
- Sources shows origins of captured memories, not live connectors; say so in-app.
