# Compatibility matrix

Status is deliberately evidence-based. “Implemented” means the repository contains the code and automated coverage; “verified” requires a recorded run against the named real host.

| Client or surface | Transport | Repository status | Real-host status |
| --- | --- | --- | --- |
| Claude Code, local | stdio MCP | Implemented and locally tested | Available path |
| Claude Code 2.1.219, self-hosted | Streamable HTTP MCP + PAT | Implemented | Verified 2026-07-25: write, read, provenance, continuity after peer revocation |
| Codex CLI 0.145.0, self-hosted | Streamable HTTP MCP + PAT | Implemented | Verified 2026-07-25: read, write, provenance, immediate denial after revocation |
| Claude Code / Codex, hosted OAuth beta | Streamable HTTP MCP + OAuth | Implemented and deployed | Login, PKCE, and DCR live; authenticated external-tester round trip pending |
| OpenAI Responses API | Remote MCP tool | Example documented | Acceptance run pending |
| Anthropic Messages API | MCP connector beta | Example documented | Acceptance run pending |
| Claude.ai / Claude Desktop / Cowork | Remote MCP + OAuth, host-dependent | Ninai endpoint and OAuth are implemented | Real-host tool scan and memory round trip pending |
| ChatGPT managed workspace custom app | Remote MCP + OAuth | Ninai endpoint exposes compatible hosted tools | Business/Enterprise/Edu admin setup and real-host acceptance pending |
| Local desktop control panel | Local PyWebView + SQLite | Implemented and tested | Runs only as local vault owner |
| Hosted control center | WSGI UI/API over PostgreSQL | Implemented and unit tested | Deployed with Auth0 login; external acceptance pending |

MCP gives a host access to named tools; it is not a universal conversation listener. Ninai cannot silently read Claude, ChatGPT, Codex, or API conversations. The host or integrating application decides when to call Ninai.

ChatGPT and Claude.ai use the hosted PostgreSQL vault. They cannot install,
connect to, or read a customer's private macOS SQLite vault. The macOS app and
cloud dashboard are separate product modes with no automatic synchronization.

The local real-host gate is recorded in [CROSS-PROVIDER-SMOKE-TEST.md](CROSS-PROVIDER-SMOKE-TEST.md), including post-revocation denial. The public OAuth beta is deployed, but authenticated cross-provider acceptance remains a separate launch gate; the public site therefore describes it only as an invitation beta.
