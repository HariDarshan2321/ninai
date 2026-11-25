# Ninai Cloud Team repository handoffs

A Team workspace can share updates and approved decisions across checkouts of
the same GitHub repository. Recent handoffs report what a teammate is working
on, what's blocked and what to pick up next. Approved decisions keep their
review and source-authorization requirements.

## Team setup

1. In the Team control center, create or enable a workspace and invite each
   teammate using their verified dashboard identity.
2. Create a project with its GitHub repository, or select **Connect existing
   project**. Enter `owner/repo` or the GitHub clone URL. Assign each teammate
   to the project. The repository assignment stays fixed for that project.
3. Each teammate selects the project and issues their own assistant credential.
   Enable **Read context** and **Read team handoffs** for session briefs. Use
   **Publish team handoffs** and **Propose decisions** to opt in to writes.
   The preview credential expires after one hour and can be rotated or revoked.

Only project-authorized users receive handoffs. A handoff records the verified
author, status, and source identifier. It needs no PR. The brief includes up to
eight recent handoffs, subject to a 2,048-byte limit. A new update from the same
author on the same topic supersedes the earlier one in the brief. Updates age out
of the brief after 14 days. Shared handoff storage needs an approved purge policy
before a customer rollout.

## Connect an assistant

Install the cloud package from this checkout in a virtual environment with
`pip install ./cloud`. Activate the environment or use full executable paths
in the assistant configuration. Set these values in the shell that starts
the assistant, using the workspace and project IDs from the Team dashboard.

```sh
export NINAI_TEAM_ORIGIN=https://team-staging.example.com
export NINAI_TEAM_WORKSPACE="your-workspace-uuid"
export NINAI_TEAM_PROJECT="your-project-uuid"
export NINAI_TEAM_REPOSITORY=owner/repo
```

Set `NINAI_TEAM_TOKEN` from the issued assistant credential using your local
secret manager or a hidden shell prompt. Keep it out of project files and
command history. Launch the assistant from a checkout whose single Git
`origin` points to the configured GitHub repository. HTTPS and GitHub SSH
clone URLs resolve to the same project.

In Claude Code, register the stdio server from the checkout:

```sh
claude mcp add --scope local ninai-team -- ninai-team-mcp
```

In Codex, add this server to the trusted project's `.codex/config.toml`:

```toml
[mcp_servers.ninai_team]
command = "ninai-team-mcp"
env_vars = ["NINAI_TEAM_ORIGIN", "NINAI_TEAM_WORKSPACE", "NINAI_TEAM_PROJECT", "NINAI_TEAM_REPOSITORY", "NINAI_TEAM_TOKEN"]
```

Merge this hook into the existing Claude Code local project settings
(`.claude/settings.local.json`) or Codex project hooks (`.codex/hooks.json`).

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "ninai-team-session-start" }
        ]
      }
    ]
  }
}
```

The hook recognizes the checkout and loads recent handoffs plus a bounded
overview of approved decisions. The assistant can call `team_context` with
the current task and repository-relative selectors before editing. The hook
also prompts the assistant to post a compact checkpoint through
`team_publish_handoff` when the work changes. The assistant authors that
checkpoint. The hook reads only the startup event and does not process local
vault data or session transcripts. A stable topic links checkpoints for the
same workstream. Use `team_propose_decision` for a durable rule with supporting
evidence and human review.

## Preview acceptance

In two separate clones, start an opted-in session as each teammate. Publish a
work-in-progress update as the first teammate, then start a fresh session as
the second. The second should get the update without asking Ninai. Submit a
decision proposal, check that it is withheld before approval, then verify its
version and authorized source after approval. Revoke the second credential and
check that the next session receives neither payload.

An isolated fixture covers the MCP tools, both checkout formats, the startup
hook, review, source denial and credential revocation. Managed staging, live
provider verification, real-host onboarding, and release approval are separate
gates. The release entry point requires an approved requester-specific source
verifier before it can approve or release supported external evidence.
