# Installed local Claude Code and Codex acceptance — 9 November 2026

Result: **PASS for the synthetic local host handoff and revocation scenario**.
This is operator-run evidence, not an independent beginner installation test or
a hosted OAuth acceptance result.

- Installed engine interpreter: `/private/tmp/ninai-install-e2e.EytGix/venv/bin/python`
- Claude Code: `2.1.319`
- Codex CLI: `0.145.0`
- Actual model calls: six invocations; two writes, two peer reads, one denied
  read after revocation, and one remaining-client continuity read.
- Observed database event window: `2026-11-09T18:30:34Z`–`18:31:10Z`.
- Synthetic marker: `NINAI_GATE_10A47BFE72C0`.
- Named project: `c2e2c7a1-f1da-5a0e-a20a-443c13efac53`.
- Temporary evidence directory:
  `/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-real-host-un6agd4v`.

| Gate | Observed evidence |
| --- | --- |
| Claude writes | Memory `524d191c-4d43-47c9-a8f4-dcc92d121430`, source `synthetic://host-gate/NINAI_GATE_10A47BFE72C0/claude-code` |
| Codex writes | Memory `21d144df-4a08-4798-900f-63414b18e00c`, source `synthetic://host-gate/NINAI_GATE_10A47BFE72C0/codex` |
| Claude reads peer memory | Disclosure contains both exact IDs and sources; 187 estimated tokens |
| Codex reads peer memory | Disclosure contains both exact IDs and sources; 187 estimated tokens |
| Codex project access revoked | Its next real model recall logs no memory IDs and zero tokens |
| Claude continuity | Its next recall still contains both memories; 187 estimated tokens |

Database rows and disclosure records were inspected independently of model prose.
The final fixture contains two memories and four disclosures. Stored content
contains the exact marker and authoring host for each record.

## Isolation and repeatability

Run `scripts/test_local_hosts.py` with a fresh installed Ninai Python interpreter.
It creates a new synthetic vault and working directory on every run. Claude uses
restricted tools, explicit MCP configuration, disabled hooks and session
persistence. Codex ignores the user config, disables hooks and apps, and uses an
ephemeral read-only session with only the synthetic MCP server configured.
Existing authenticated CLI sessions authorize model calls; credentials are not
read or printed by the runner. Global connector configuration and the real Ninai
vault are not modified. Temporary synthetic evidence is retained for inspection.

## Host setup friction discovered

Earlier attempts were not passes. Claude's variadic `--mcp-config` consumed a
positional prompt until an explicit `--` separator was added. Codex's noninteractive
MCP consent returned `user cancelled MCP tool call` under the default and `auto`
tool approval modes, despite general command approval being set to `never`.
The passing runner explicitly sets `default_tools_approval_mode="approve"` for
the temporary synthetic MCP server only. It does not change global approval
settings or bypass the command sandbox. A shipped integration should explain
host tool consent rather than report a configured server as fully tested.

## Remaining limits

This exercise does not prove clean-machine signed installer trust, Windows,
offline model operation, browser OAuth signup, personal-data deletion, or
independent nontechnical usability. Model subscriptions and existing host login
were available on the operator's machine. The model versions were not pinned;
host versions and exact tool/database evidence are the reproducible observations.
