# Ninai MVP

**Your AI should remember. You decide what it knows.**

Ninai is a local-first, permissioned memory layer for AI tools. This repository contains:

- `engine/` — an installable Python MCP server with local SQLite memory, scoped permissions, provenance, access logs, and compact context packets.
- `cloud/` — an explicit opt-in PostgreSQL store, authenticated Streamable HTTP MCP service, and hosted control-center API/UI.
- `website/` — a statically exported Next.js launch site for `ninai.io`, including an interactive permission model, sitemap, robots.txt, JSON-LD, Open Graph metadata, privacy page, install guide, and research page.
- `.claude/` — an optional Claude Code `PostToolUse` hook that captures durable results from existing MCP tools without asking users to reconnect Linear, GitHub, or other services.
- `docs/` — product architecture, brand guidance, deployment instructions, and the SEO launch checklist.

The MVP intentionally keeps the trust boundary small: memory is stored on the user's machine and only permission-filtered context packets are returned to an AI client.

Local mode is local-first and never uploads or syncs the vault automatically. A separate hosted beta is now implemented in `cloud/` for clients that cannot reach a local MCP server. It is not automatically enabled and does not inspect the local vault. Its local real-host Claude Code → Codex → Claude Code gate passed on 25 July 2026; production OAuth/HTTPS deployment remains pending. Both modes share the same required permission, provenance, and disclosure-audit invariants.

## 1. Run the engine locally

Requirements: Python 3.11+. On macOS the default `python3` is often 3.9, which
is too old and will fail the install with a `requires-python` / build error.
Check with `python3 --version`; if it is below 3.11, use an explicit interpreter
(`python3.11`, `python3.12`, or `python3.13`) in the `venv` command below.

```bash
cd engine
python3.13 -m venv .venv   # or python3.11 / python3.12 — must be >= 3.11
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .

# Grant Claude Code access to selected scopes.
ninai permission grant claude-code work
ninai permission grant claude-code project
ninai permission grant claude-code preference

# Register the MCP server (use the absolute path to ninai-mcp from this venv
# so the command resolves after you deactivate, e.g. .venv/bin/ninai-mcp).
claude mcp add ninai --scope user -- "$(pwd)/.venv/bin/ninai-mcp"
```

For a durable install that survives moving this repository, create the virtual
environment in a stable location outside the source tree (for example
`~/.ninai-app/venv`) and point the `claude mcp add` command at
`~/.ninai-app/venv/bin/ninai-mcp`.

In Claude Code, try:

```text
Remember that the Ninai permission dashboard must be ready before launch.
```

Then begin a new session and ask:

```text
What should I finish before launch?
```

## 1b. Optional: open the desktop control panel

Ninai ships a native desktop control panel — a window with five screens
(Today, Memories, Sources, Permissions, Activity) for the vault owner to see and
manage everything the engine stores. It runs as the local operator (full access)
and talks to the same local vault the MCP server uses.

```bash
pip install '.[desktop]'   # adds pywebview; from the engine/ directory
ninai-app                  # opens the window
```

The app lets you add, search, view-with-source, correct, and delete memories;
toggle each AI client's scope permissions; and read the full disclosure log. It is
**not** a security boundary and the vault is **not** encrypted — see the boundaries
below. Sensitivity labels are shown for your reference but do not yet affect what is
disclosed; scope is the control that gates recall.

## 2. Optional: capture results from existing MCP tools

Claude Code hooks receive tool events after tools complete. Copy the example settings into your project:

```bash
mkdir -p .claude/hooks
cp ../.claude/hooks/ninai_post_tool_use.py .claude/hooks/
cp ../.claude/settings.example.json .claude/settings.json
chmod +x .claude/hooks/ninai_post_tool_use.py
```

The hook ignores Ninai itself, redacts common secret patterns, and stores only tool events that look durable. Treat this as a defense-in-depth capture filter, not a complete security boundary.

## 3. Run deterministic MVP verification

From the repository root, with the engine environment activated:

```bash
python scripts/verify_mvp.py
```

The verification simulates an existing Linear MCP result, captures only selected durable outcome fields, recalls a provenance-backed packet, reports estimated context reduction, revokes the `project` scope, proves the second recall is empty, and prints the disclosure log. It uses a temporary vault unless `--data-dir` is supplied.

## 4. Run the website

```bash
cd website
npm install
npm run dev
```

Open `http://localhost:3000`. Production output is generated with `npm run build` in `website/out/`.

## 4b. Run the hosted beta service

Hosted mode requires Python 3.11+ and PostgreSQL. OAuth/OIDC is the default. A separate opaque personal-access-token mode exists for a trusted private self-hosted beta; it must be explicitly enabled.

```bash
cd cloud
python3.12 -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
# Export the values from .env with real PostgreSQL and authentication settings.
python -m ninai_cloud.migrations
ninai-cloud-mcp
```

The service exposes `GET /health`, authenticated Streamable HTTP MCP at `/mcp`, and protected-resource metadata. See [hosted client setup and API examples](docs/HOSTED-BETA.md), the [compatibility matrix](docs/COMPATIBILITY.md), and [deployment guide](docs/DEPLOYMENT.md). A running service still needs provisioned users, workspaces, client connections, and grants before a client can access memory.

## 5. Publish and deploy

```bash
cd ninai-mvp-starter
git init
git add .
git commit -m "feat: launch Ninai MVP"
gh repo create HariDarshan2321/ninai --public --source=. --remote=origin --push
```

The recommended website host is Vercel with `website/` configured as the project root.
It provides a deployment preview before the domain is changed and native Next.js support
if the site later moves beyond a static export. The included GitHub Pages workflow remains
a supported static alternative.

The public website assumes the repository exists at
`https://github.com/HariDarshan2321/ninai`; create it before launch so the source links and
install command resolve. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for verified checks,
hosting alternatives, and domain setup.

## 6. Important product truth

Ninai does not claim that cloud AI providers never receive context. The full vault stays local; a selected AI receives only the smallest permissioned packet needed for a request. The receiving provider's policy applies after release.

## Current boundaries

- SQLite + FTS5 retrieval; no vector embeddings yet.
- Claude Code automatic capture through a local hook.
- Other clients use explicit `remember` and `recall` MCP calls.
- Hosted PostgreSQL and remote MCP are implemented, and the local PAT-backed real-host compatibility gate passed. Production deployment, issuer onboarding, billing, and automated local-to-hosted sync are not implemented. Local mode never uploads automatically.
- Vector search, local-model extraction, consolidation, and richer temporal state remain post-MVP evaluation work. They should be added behind explicit interfaces only when benchmarks justify the extra installation and security surface.

## Hosted beta evidence and release gate

- [Hosted setup, Claude Code, Codex, OpenAI, and Anthropic examples](docs/HOSTED-BETA.md)
- [Compatibility matrix](docs/COMPATIBILITY.md)
- [Security report](docs/SECURITY-REPORT.md)
- [Cross-provider smoke-test report](docs/CROSS-PROVIDER-SMOKE-TEST.md)
- [Hosted launch checklist](docs/HOSTED-LAUNCH-CHECKLIST.md)
- [Known limitations and deferred work](docs/KNOWN-LIMITATIONS.md)
- [Architecture decisions and open questions](docs/ARCHITECTURE-DECISIONS.md)

## Engine architecture

The engine keeps policy and transport separate:

- `models.py` defines valid memory types, scopes, and the core memory record.
- `store.py` owns SQLite persistence, permission checks, provenance, deletion, and disclosure logs.
- `retrieval.py` implements deterministic PACT ranking and token-budget composition as pure functions.
- `hook_capture.py` converts completed host tool events into compact durable outcomes and deduplicates hook retries.
- `server.py` exposes the engine through MCP without embedding policy in the transport layer.
- `cli.py` provides local administration and smoke-test commands.

SQLite is the authoritative store. FTS is a rebuildable index. Permission filtering occurs in SQL before candidates reach ranking.
