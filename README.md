# Ninai MVP

**Your AI should remember. You decide what it knows.**

Ninai is a local-first, permissioned memory layer for AI tools. This repository contains:

- `engine/` — an installable Python MCP server with local SQLite memory, scoped permissions, provenance, access logs, and compact context packets.
- `website/` — a statically exported Next.js launch site for `ninai.io`, including an interactive permission model, sitemap, robots.txt, JSON-LD, Open Graph metadata, privacy page, install guide, and research page.
- `.claude/` — an optional Claude Code `PostToolUse` hook that captures durable results from existing MCP tools without asking users to reconnect Linear, GitHub, or other services.
- `docs/` — product architecture, brand guidance, deployment instructions, and the SEO launch checklist.

The MVP intentionally keeps the trust boundary small: memory is stored on the user's machine and only permission-filtered context packets are returned to an AI client.

## 1. Run the engine locally

Requirements: Python 3.11+

```bash
cd engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .

# Grant Claude Code access to selected scopes.
ninai permission grant claude-code work
ninai permission grant claude-code project
ninai permission grant claude-code preference

# Register the MCP server.
claude mcp add ninai -- ninai-mcp
```

In Claude Code, try:

```text
Remember that the Ninai permission dashboard must be ready before launch.
```

Then begin a new session and ask:

```text
What should I finish before launch?
```

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

## Current MVP boundaries

- SQLite + FTS5 retrieval; no vector embeddings yet.
- Claude Code automatic capture through a local hook.
- Other clients use explicit `remember` and `recall` MCP calls.
- No cloud sync, accounts, billing, Gmail OAuth, or production encryption.
- Vector search, local-model extraction, consolidation, and richer temporal state remain post-MVP evaluation work. They should be added behind explicit interfaces only when benchmarks justify the extra installation and security surface.

## Engine architecture

The engine keeps policy and transport separate:

- `models.py` defines valid memory types, scopes, and the core memory record.
- `store.py` owns SQLite persistence, permission checks, provenance, deletion, and disclosure logs.
- `retrieval.py` implements deterministic PACT ranking and token-budget composition as pure functions.
- `hook_capture.py` converts completed host tool events into compact durable outcomes and deduplicates hook retries.
- `server.py` exposes the engine through MCP without embedding policy in the transport layer.
- `cli.py` provides local administration and smoke-test commands.

SQLite is the authoritative store. FTS is a rebuildable index. Permission filtering occurs in SQL before candidates reach ranking.
