# Ninai MVP

**Your AI should remember. You decide what it knows.**

Ninai is a local-first, permissioned memory layer for AI tools. This repository contains:

- `engine/` — an installable Python MCP server with local SQLite memory, scoped permissions, provenance, access logs, and compact context packets.
- `cloud/` — an explicit opt-in PostgreSQL store, authenticated Streamable HTTP MCP service, and hosted control-center API/UI.
- `website/` — a statically exported Next.js launch site for `ninai.io`, including an interactive permission model, sitemap, robots.txt, JSON-LD, Open Graph metadata, privacy page, install guide, and research page.
- `.claude/` and `.codex/` — merge-safe lifecycle hook examples for local Claude Code ↔ Codex session continuity, plus optional durable MCP-result capture.
- `docs/` — product architecture, brand guidance, deployment instructions, and the SEO launch checklist.

The MVP intentionally keeps the trust boundary small: memory is stored on the user's machine and only permission-filtered context packets are returned to an AI client.

Local mode is local-first and never uploads or syncs the vault automatically. A separate hosted beta is now implemented in `cloud/` for clients that cannot reach a local MCP server. It is not automatically enabled and does not inspect the local vault. Its local real-host Claude Code → Codex → Claude Code gate passed on 25 July 2026, and its public OAuth/HTTPS beta endpoint is live; external-tester acceptance and remaining operational hardening are still pending. Both modes share the same required permission, provenance, and disclosure-audit invariants.

## 1. Run the engine locally

Requirements: Python 3.11+. On macOS the default `python3` is often 3.9, which
is too old and will fail the install with a `requires-python` / build error.
Check with `python3 --version`; if it is below 3.11, use an explicit interpreter
(`python3.11`, `python3.12`, or `python3.13`) in the `venv` command below.

For the one-command desktop-and-engine installation used by the public setup guide:

```bash
# Claude Code + Codex (installs Ninai, grants project scope, registers both
# local MCP clients, and asks before enabling lifecycle session archive).
curl -fsSL https://raw.githubusercontent.com/HariDarshan2321/ninai/main/scripts/install-local | \
  bash -s -- --client both

# Open the local control panel.
open ~/.ninai-app/Ninai.app
```

The installer requires Python 3.11+ and selects `python3.13`, `python3.12`, or
`python3.11` automatically. Set `NINAI_PYTHON` to choose another compatible
interpreter or `NINAI_INSTALL_DIR` to change the stable installation directory.
Use `--client claude-code` or `--client codex` for only one client, or run `./scripts/install-local` from a cloned
repository. Review [`scripts/install-local`](scripts/install-local) before
running a downloaded script.

In Claude Code, try:

```text
Remember that the Ninai permission dashboard must be ready before launch.
```

Then begin a new session and ask:

```text
What should I finish before launch?
```

## 1b. Optional: open the desktop control panel

Ninai ships a native desktop control panel with Today, Memories, Sources,
Permissions, Sessions, and Activity screens for the vault owner to see and
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

## 2. Automatic local session handoff

With explicit consent, the installer merges `SessionStart`, `Stop`, and
`SessionEnd` hooks for Claude Code and Codex. A completed session is normalized
to user/assistant text, secret-redacted, stored only in the local vault, and
offered to the next supported agent only for the same project and only after a
project-scope permission check. Injected excerpts are token-bounded and marked
as untrusted historical data. Disable capture at any time:

```bash
~/.ninai-app/venv/bin/ninai capture disable
```

## 2b. Optional: capture results from existing MCP tools

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

For the smallest isolated developer stack (PostgreSQL, migrations, and the
cloud service), use Docker from the repository root:

```bash
scripts/ninai-cloud-local setup
scripts/ninai-cloud-local bootstrap --email you@example.com
scripts/ninai-cloud-local doctor
```

This explicit hosted stack uses development-only defaults, binds the service to
localhost, and does not mount, read, or synchronize the local desktop vault.
See [`cloud/README.md`](cloud/README.md) for overrides and lifecycle commands.

## 5. Publish and deploy

```bash
cd ninai-mvp-starter
git init
git add .
git commit -m "feat: launch Ninai MVP"
gh repo create HariDarshan2321/ninai --public --source=. --remote=origin --push
```

The website is deployed from `main` through Vercel with `website/` configured as
the project root. It provides deployment previews and native Next.js support if
the site later moves beyond a static export. Cloudflare Pages and GitHub Pages
remain documented alternatives, but no second deployment workflow runs on pushes.

The public website assumes the repository exists at
`https://github.com/HariDarshan2321/ninai`; create it before launch so the source links and
install command resolve. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for verified checks,
hosting alternatives, and domain setup.

## 6. Important product truth

Ninai does not claim that cloud AI providers never receive context. The full vault stays local; a selected AI receives only the smallest permissioned packet needed for a request. The receiving provider's policy applies after release.

## Current boundaries

- SQLite + FTS5 retrieval; no vector embeddings yet.
- Claude Code and Codex lifecycle continuity is automatic only in consented local installs.
- Claude.ai, ChatGPT, and hosted MCP clients use explicit scoped tools; they do not passively expose full chat transcripts to Ninai.
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
