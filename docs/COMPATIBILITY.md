# Compatibility matrix

Status is deliberately evidence-based. “Implemented” means the repository contains the code and automated coverage; “verified” requires a recorded run against the named real host.

| Client or surface | Transport | Repository status | Real-host status |
| --- | --- | --- | --- |
| Claude Code, local | stdio MCP | Implemented and locally tested | Available path |
| Claude Code 2.1.219, self-hosted | Streamable HTTP MCP + PAT | Implemented | Verified 2026-07-25: write, read, provenance, continuity after peer revocation |
| Codex CLI 0.145.0, self-hosted | Streamable HTTP MCP + PAT | Implemented | Verified 2026-07-25: read, write, provenance, immediate denial after revocation |
| Claude Code / Codex, hosted OAuth beta | Streamable HTTP MCP + OAuth | Implemented and deployed | Login, PKCE, and DCR live; authenticated CLI external-tester round trip pending |
| OpenAI Responses API | Remote MCP tool | Example documented | Acceptance run pending |
| Anthropic Messages API | MCP connector beta | Example documented | Acceptance run pending |
| Claude.ai | Remote MCP + OAuth | Ninai endpoint and OAuth are implemented | Verified 2026-07-26: OAuth, five-tool scan, and successful empty search |
| Claude Desktop / Cowork | Remote MCP + OAuth, host-dependent | Ninai endpoint and OAuth are implemented | Separate real-host acceptance pending |
| ChatGPT custom app | Remote MCP + OAuth | Ninai endpoint exposes compatible hosted tools | Verified 2026-07-27: developer-mode install, OAuth, tool invocation, and successful empty search |
| Local desktop control panel | Local PyWebView + SQLite | Implemented and tested | Runs only as local vault owner |
| Hosted control center | WSGI UI/API over PostgreSQL | Implemented and unit tested | Deployed with Auth0 login; full external tester acceptance pending |

MCP gives a host access to named tools; it is not a universal conversation listener. Ninai cannot silently read Claude, ChatGPT, Codex, or API conversations. The host or integrating application decides when to call Ninai.

ChatGPT and Claude.ai use the hosted PostgreSQL vault. They cannot install,
connect to, or read a customer's private macOS SQLite vault. The macOS app and
cloud dashboard are separate product modes with no automatic synchronization.

The local real-host gate is recorded in [CROSS-PROVIDER-SMOKE-TEST.md](CROSS-PROVIDER-SMOKE-TEST.md), including post-revocation denial. Claude.ai and ChatGPT have each completed OAuth and a production read-tool call. A full hosted write/read/provenance/revocation pass with synthetic data remains a separate launch gate; the public site therefore describes hosted mode only as an invitation beta.
