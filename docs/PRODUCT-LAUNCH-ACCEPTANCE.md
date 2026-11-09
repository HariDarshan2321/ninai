# Ninai product launch acceptance

This document defines the launch journey for the product itself. It does not
change the marketing website and it does not treat a passing unit test as proof
that installation works on a clean computer.

## Launch promise

A first-time user should be able to install Ninai, see which supported
assistants were found, confirm that at least one is connected, save one project
decision, recall it from an allowed assistant, and understand how to revoke
access. The product should explain the next action whenever that journey stops.

The target is five minutes on a supported, clean Mac with one already-installed
supported assistant. This target is not achieved until it is timed with an
independent tester using the signed and notarized installer.

## Beginner journey and evidence

| Stage | User-visible success | Automated evidence | Real-device evidence still required |
| --- | --- | --- | --- |
| Open account setup | Page responds without an unexplained error | Control UI, OAuth redirect, state, PKCE, callback, cancellation, and session-cookie tests | New private-browser signup with a real email |
| Download | One obvious Mac download is available after sign-in | Authentication and installer checksum/receipt tests | Browser download on Safari, Chrome, and Edge |
| Install | App appears in Applications and opens normally | Installer safety, rollback, configuration-merge, and uninstall tests | Signed/notarized DMG or PKG on a clean Mac |
| Detect assistants | Installed tools show `Connected`, `Needs attention`, or `Not installed` | Read-only Claude Code, Codex, and Gemini status probes | Current stable releases of each supported tool |
| Repair | A broken connection explains how to recover without losing memory | Status and recovery-copy tests | Interrupt install, corrupt one config, rerun installer |
| First memory | User saves one decision with only content and access choice required | Desktop API add/search tests | Beginner completes it without documentation |
| First handoff | An allowed assistant recalls the decision with its source | End-to-end remember, permission, recall, audit, and token-budget tests | Real Claude Code to Codex handoff in a fresh project |
| Revoke | The next request returns no revoked memory | End-to-end revocation test | Repeat in both assistants and inspect sharing history |
| Uninstall | Ninai configuration is removed and data is recoverable | Uninstaller isolation and Trash tests | Finder uninstall/reinstall and recovery check |

## Product rules derived from competitor onboarding

The comparison is about onboarding patterns, not a claim that another product
is weak.

- Letta offers a web path that starts with sign-in and a preconfigured Tutor,
  while its local path is a CLI. Ninai should similarly provide a guided first
  success, but preserve the local ownership boundary.
- Zep creates the first project during signup and guides the developer from an
  API key to a sample memory and visible graph. Ninai should create or select a
  sensible project automatically and seed a reversible test memory only with
  explicit user action.
- Zep's recent onboarding work masks credentials and seeds a richer sample
  graph. Ninai should never display or ask users to copy credentials during the
  standard local flow.
- Claude Code documents `doctor` and explicit connection commands. Ninai should
  run equivalent checks itself and translate them into `Connected`, `Needs
  attention`, and a single recovery action.
- Mem0, Zep, and Letta primarily document SDK or agent-building flows. Ninai's
  opportunity is an owner-facing product flow across assistants, not another
  SDK quickstart.

Primary references:

- https://docs.letta.com/quickstart
- https://docs.letta.com/platform/letta-desktop
- https://help.getzep.com/v4/quick-start-guide
- https://help.getzep.com/v3/changelog/2026/7/13
- https://docs.mem0.ai/openmemory/overview
- https://docs.anthropic.com/en/docs/claude-code/getting-started
- https://docs.anthropic.com/en/docs/claude-code/cli-usage

## Required automated suites

Every launch candidate must pass these without production credentials:

1. Engine unit and policy tests.
2. Local remember, recall, provenance, disclosure-log, and revocation journey.
3. Installer merge, rollback, update, and recoverable uninstall tests.
4. Desktop connection-state tests for installed, connected, missing, timeout,
   malformed configuration, and repair states.
5. Hosted account tests for signup redirect, PKCE, callback, cancellation,
   cookie security, expired identity, installer download, connection creation,
   connection test, grants, revocation, and account deletion.
6. Cross-provider acceptance against disposable synthetic accounts when a
   release owner explicitly supplies credentials.
7. Accessibility and visual checks for the desktop app at supported desktop
   sizes. The desktop app does not currently claim mobile support.

## Real launch rehearsal

Use a clean macOS user account and screen-record the complete attempt. The
tester must not have the repository, Python tooling, or Ninai configuration
already present.

1. Start at the account page in a private browser window.
2. Create an account and return from the identity provider.
3. Download and open the signed installer.
4. Confirm the operating-system trust dialog is expected and understandable.
5. Open Ninai and record detected assistant states.
6. Save the supplied reversible test decision.
7. Recall it from assistant A, then assistant B.
8. Revoke project access for assistant B and repeat the request.
9. Break one connection, use the product's repair path, and retest.
10. Uninstall, confirm unrelated assistant configuration remains, then restore
    or permanently remove the recoverable Ninai data copy.

Record elapsed time, every hesitation, every external page opened, all manual
commands, and whether the tester needed help. A release fails if the tester
cannot identify the next action from the product itself.

## Render cold start

An application cannot remove a platform scale-to-zero cold start with HTML,
JavaScript, or a faster loading message. The account service must be available
before it can create OAuth state and redirect safely.

Launch decision:

- Run the account service on a Render plan/configuration that does not scale to
  zero.
- Keep the service and PostgreSQL in the same region and use the private
  database URL.
- Keep `/ready` as the Render health check and verify it performs a database
  query.
- Configure an independent monitor for `/health` and `/ready`; monitoring is
  detection, not a substitute for an always-on instance.
- Measure p50 and p95 response time for `/control/login`, `/health`, and `/ready`
  after at least 30 minutes of inactivity before launch.

Do not add a self-ping loop to the application. It hides the capacity decision,
does not guarantee availability, and complicates shutdown and deployment.

## Launch blockers

- Signed and notarized macOS installer with clean-machine evidence.
- Signed Windows installer with clean-machine evidence.
- One real external-tester journey completed without repository access.
- Always-on Render service confirmed by the release owner.
- Restore drill and alert-delivery evidence completed.
- Real Claude Code and Codex handoff plus revocation recorded for the release
  candidate.
