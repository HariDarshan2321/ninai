# Ninai MVP

**Your AI should remember. You decide what it knows.**

Ninai is a local-first, permissioned memory layer for AI tools. This repository contains:

- `engine/` — an installable Python MCP server with local SQLite memory, scoped permissions, provenance, access logs, and compact context packets.
- `cloud/` — the account, authenticated installer, and private hosted-service code. Public hosted vaults are not part of the MVP.
- `website/` — a statically exported Next.js launch site for `ninai.io`, including an interactive permission model, sitemap, robots.txt, JSON-LD, Open Graph metadata, privacy page, install guide, and research page.
- `.claude/` and `.codex/` — merge-safe lifecycle hook examples for local Claude Code ↔ Codex session continuity, plus optional durable MCP-result capture.
- `docs/` — product architecture, brand guidance, deployment instructions, and the SEO launch checklist.

The MVP intentionally keeps the trust boundary small: memory is stored on the user's machine and only permission-filtered context packets are returned to an AI client.

The public MVP is local-only on Mac. It never uploads or synchronizes the vault automatically. Cloud-hosted vaults remain private development work until their security and external-acceptance gates are complete.

## 1. Run the engine locally

The official customer path is deliberately short:

1. Open [ninai.io/install](https://ninai.io/install/).
2. Create an account or sign in.
3. Download the authenticated Mac installer and run the one command shown there.

The installer checks for a compatible Python version, installs the Ninai app and local SQLite vault, detects Claude Code and Codex, connects every supported agent it finds, asks before enabling automatic session handoff, and opens Ninai. Advanced flags and contributor setup remain documented in [`scripts/install-local`](scripts/install-local).

Because this repository is public, developers can inspect and run its source directly. The official download and customer onboarding flow require an account; the open-source code itself is not access-controlled.

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

## 4b. Private hosted-service development

Hosted storage and remote connectors are not part of the public MVP. Maintainers can use [`cloud/README.md`](cloud/README.md) for private development and testing; customer-facing setup must not direct users to those endpoints.

## 5. Publish and deploy

The website deploys from `main` through Vercel with `website/` as the project root. The account and authenticated installer service deploy from the same branch through Render. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the maintained checks and domain configuration.

## 6. Important product truth

Ninai does not claim that cloud AI providers never receive context. The full vault stays local; a selected AI receives only the smallest permissioned packet needed for a request. The receiving provider's policy applies after release.

## Current boundaries

- SQLite + FTS5 retrieval; no vector embeddings yet.
- Claude Code and Codex lifecycle continuity is automatic only in consented local installs.
- Claude.ai, ChatGPT, and hosted MCP clients are not part of the public MVP.
- Hosted PostgreSQL and remote MCP remain private development surfaces. Local mode never uploads automatically.
- Vector search, local-model extraction, consolidation, and richer temporal state remain post-MVP evaluation work. They should be added behind explicit interfaces only when benchmarks justify the extra installation and security surface.

## Private hosted-service evidence and release gate

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
