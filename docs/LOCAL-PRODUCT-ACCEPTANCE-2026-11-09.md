# Local product acceptance — 9 November 2026

Decision: local engine and localhost hosted-service gates passed. Broad production launch remains blocked by signed releases, independent clean-machine usability, production OAuth/operations evidence, and the explicitly deferred editor-agent tests. Nothing was posted publicly.

## Fresh installation

Ran the real macOS installer twice with separate temporary installation/data directories, `--client none --session-capture off`. Dependency installation, diagnostics, icon generation, PyInstaller bundle creation and ad-hoc signing completed; the native app opened. Latest bundle: `/tmp/ninai-final-install.yRXRYY/Ninai.app`. No existing vault or global assistant configuration was overwritten. The final opt-out message was subsequently clarified to distinguish no configured connection from no installed assistant.

This is not a clean-machine test: Python, development tooling, and assistant authentication already existed on the machine. The installer still builds from source and uses ad-hoc signing, not Developer ID notarization. It is not the finished beginner distribution experience.

## Actual model handoff

See [installed host evidence](LOCAL-HOST-ACCEPTANCE-2026-11-09.md). Claude Code 2.1.319 and Codex CLI 0.145.0 executed real Ninai tools against a fresh installed interpreter and disposable named project. Both wrote source-backed records and read their peer's memory. Codex's next read after revocation disclosed nothing; Claude retained access. Records and disclosure logs were inspected independently of model prose.

Codex required an explicit per-server MCP tool-consent setting for the synthetic noninteractive test. General command approval did not authorize MCP calls. The test runner makes this visible; the shipped installer does not globally weaken host approval policies.

## Browser journey with real backend

`scripts/preview_desktop_acceptance.py` serves the actual desktop assets with a test bridge to real DesktopApi and SQLite. It always creates disposable synthetic data, binds loopback only, checks host/origin/token, bounds bodies, and exposes an allowlist. It is not a product web server or a mock backend.

Observed using the browser UI:

1. Open Memories, Add memory, create `Synthetic launch rehearsal`.
2. Save the synthetic reversible-migration memory under the automatically selected project.
3. Observe all named-project permissions initially off.
4. Grant Claude Read/Save and Codex Read independently.
5. Real backend recall returned one fact for both authorized clients and none for Cursor.
6. Revoke Codex Read in the UI; next backend recall returned no facts, while Claude still received one.
7. Sharing history displayed successful and denied disclosures with client/purpose/IDs/token estimates.

Screenshot: `/tmp/ninai-local-acceptance.png`. Native app opened, but native screen-capture/accessibility state was inconsistent during automated navigation. The complete interaction result above is browser rendering of the same product assets with the real backend; it must not be presented as complete native GUI automation.

## Editor connectors

Added native Cursor `mcpServers` and VS Code `servers`/stdio configuration, helper CLI, installer integration, and explicit desktop Configure actions. Existing entries are preserved, recovery backups retained, writes atomic; invalid/JSONC/conflicting/symlink configurations are refused rather than overwritten. No connector installation grants memory access. Hosted connectors are no longer removed while setting up local connections. Isolated data directory overrides propagate to configured clients.

Tests launch real MCP subprocesses from both generated configurations, initialize/list tools, verify default write denial, grant access, save/recall source-backed memory, and verify immediate read revocation. VS Code 1.142.0 accepted its schema using the native CLI. Cursor 3.21.16 and VS Code opened isolated workspaces/profiles. Cursor required login for AI; VS Code required Copilot sign-in and workspace trust. The user explicitly chose to leave actual editor-agent invocation pending. Do not call these two agents end-to-end verified.

Status displays now say Configured when only configuration is observed. They do not imply tool consent, authentication, model invocation, or successful memory access.

Official schemas: https://prod.cursor.com/help/customization/mcp and https://code.visualstudio.com/docs/agents/reference/mcp-configuration . Native profile schemas are not a guarantee for every extension/alternate agent harness.

An exploratory Cursor `agent --help` unexpectedly attempted to download its separate agent CLI. The exact spawned processes were stopped and the temporary installer artifact was cleaned automatically; no global agent installation completed. No credentials or personal editor configuration were changed.

## Docker/cloud

Separate Compose project `ninai-acceptance-20261109`, localhost PostgreSQL port55439 and cloud58039; existing development stack and data left untouched.

- All 107 cloud tests passed against real PostgreSQL16, zero skips.
- Existing cross-provider service harness: 12 checks passed.
- `scripts/verify_hosted_http.py`: six actual HTTP transport checks passed, including initialization, tools, write, peer recall/source, revocation HTTP401, and unaffected peer continuity. Credentials generated in memory and never printed.
- `/ready` returned HTTP200 (one local observation, approximately4.3ms; not a performance benchmark).
- Actual pg_dump/pg_restore into a separate fresh database passed structural verification: eight migrations, one workspace, two projects, two client connections, three memories, two disclosures.

This proves localhost PAT transport/database behavior, not production OAuth signup, public service availability or a production disaster-recovery drill.

## Automated checks and remaining gates

Engine:77 tests passed. Connector merge/transport and installer isolation/recoverable-uninstall tests included. JavaScript and Bash syntax checks and git whitespace checks passed. Windows script inspected/tested statically only; no Windows device validation. Uninstall coverage exercises the actual script in disposable test directories; the final native test bundle is retained for inspection.

Remaining: signed/notarized Mac release, signed Windows release and device test, independent beginner timing, current real hosted OAuth create/write/read/revoke, confirmed always-on production service, alert delivery, production restore/retention/deletion evidence, encryption/sensitivity gaps already documented, and the user-deferred Cursor/VS Code agent invocations. Native local ChatGPT/Claude web access and automatic local/cloud sync are not implied.
