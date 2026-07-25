# Hosted cross-provider beta

## Status

The hosted service is implemented and covered by unit and PostgreSQL integration tests. It is an explicit opt-in service: it never reads or synchronizes the local SQLite vault. A production deployment and the real Claude → OpenAI → Claude acceptance run are still required before hosted compatibility may be described as verified.

The public MCP endpoint is `https://<host>/mcp`. It uses Streamable HTTP and requires an OAuth access token. `GET https://<host>/health` is unauthenticated. The MCP protected-resource metadata is published at `/.well-known/oauth-protected-resource/mcp`.

## Available MCP tools

| Tool | Required database grant | Behavior |
| --- | --- | --- |
| `search` | `can_read` | Searches active memories within the connection's live scopes and logs the disclosure. |
| `fetch` | `can_read` | Fetches one active, in-scope memory and logs the disclosure. |
| `recall` | `can_read` | Returns a source-backed packet bounded to 12 items and 2,000 estimated tokens. |
| `propose_memory` | `can_propose` | Creates a reviewable proposal; proposals are not recalled. |
| `remember` | `can_auto_activate` | Creates active memory only for connections explicitly granted auto-activation. |

All write calls require `source_uri` and `idempotency_key`. Requests cannot choose their user, workspace, or client identity: OAuth mode takes those values from signed token claims, while self-hosted PAT mode resolves them from the token's stored digest. Both modes check live PostgreSQL state on every request.

## Authentication modes

OAuth is the default and is required for a normal multi-user hosted deployment. A private operator can explicitly set `NINAI_AUTH_MODE=pat`, run `ninai-cloud-bootstrap`, and receive separate opaque credentials for Claude and Codex. PAT plaintext is printed once and only its SHA-256 digest is stored. PAT mode has no browser login or refresh flow; it is intended for a trusted self-hosted beta, not as a substitute for public OAuth onboarding.

## Claude Code setup

Prerequisites: a deployed HTTPS endpoint, a Ninai client connection and grants, plus either the configured OAuth issuer or a self-hosted PAT.

For an issuer that supports the MCP OAuth discovery and authorization flow:

```bash
claude mcp add --transport http --scope user ninai https://<host>/mcp
claude
```

Then run `/mcp`, select `ninai`, and complete the issuer's sign-in and authorization flow. Confirm that the server exposes `search`, `fetch`, `recall`, `propose_memory`, and `remember` before testing it. Do not put a long-lived token directly in a committed project configuration.

For a pre-issued short-lived token, use an environment-backed header in `.mcp.json`:

```json
{
  "mcpServers": {
    "ninai": {
      "type": "http",
      "url": "https://<host>/mcp",
      "headers": {
        "Authorization": "Bearer ${NINAI_ACCESS_TOKEN}"
      }
    }
  }
}
```

Start Claude Code from a shell where `NINAI_ACCESS_TOKEN` is set. Treat this token path as beta/operator setup; interactive OAuth is preferable for normal users.

Official reference: [Claude Code MCP setup and remote OAuth](https://docs.anthropic.com/en/docs/claude-code/mcp).

## Codex CLI and IDE setup

For an issuer that supports MCP OAuth discovery:

```bash
codex mcp add ninai --url https://<host>/mcp
codex mcp login ninai
codex mcp list
```

The equivalent configuration is:

```toml
[mcp_servers.ninai]
url = "https://<host>/mcp"
```

For a pre-issued short-lived token, skip `codex mcp login` and configure it directly:

```bash
codex mcp add ninai --url https://<host>/mcp \
  --bearer-token-env-var NINAI_ACCESS_TOKEN
codex mcp list
```

The equivalent configuration is:

```toml
[mcp_servers.ninai]
url = "https://<host>/mcp"
bearer_token_env_var = "NINAI_ACCESS_TOKEN"
```

Restart the Codex client after changing its MCP configuration, then verify that Ninai's five tools are visible. Codex CLI 0.145.0 and Claude Code 2.1.219 passed the local PAT-backed real-host acceptance run on 25 July 2026; production OAuth/HTTPS compatibility remains to be recorded after deployment.

The checked-in commands match the installed Codex CLI's `mcp add` and `mcp login` interfaces. Recheck `codex mcp add --help` and the current official Codex documentation when recording the release run.

## OpenAI Responses API example

The application must explicitly provide Ninai as a remote MCP tool. The bearer token must identify a registered Ninai connection and workspace.

```python
import os
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    input="Recall the current database decision and include its source.",
    tools=[{
        "type": "mcp",
        "server_label": "ninai",
        "server_url": "https://<host>/mcp",
        "authorization": os.environ["NINAI_ACCESS_TOKEN"],
        "allowed_tools": ["recall", "fetch"],
        "require_approval": "never"
    }]
)
print(response.output_text)
```

Only use `require_approval: "never"` for read tools whose Ninai grants have already been reviewed. Keep `remember` and `propose_memory` out of `allowed_tools` unless the application deliberately needs writes. This example is an integration recipe, not evidence that the live OpenAI gate has passed.

Official reference: [OpenAI Responses API remote MCP tool schema](https://platform.openai.com/docs/api-reference/responses/create).

## Anthropic Messages API example

The Anthropic MCP connector is a beta API surface. The application explicitly names the Ninai server and supplies a bearer token:

```python
import os
from anthropic import Anthropic

client = Anthropic()
message = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": "Recall the current database decision and include its source."
    }],
    mcp_servers=[{
        "type": "url",
        "url": "https://<host>/mcp",
        "name": "ninai",
        "authorization_token": os.environ["NINAI_ACCESS_TOKEN"]
    }],
    betas=["mcp-client-2025-04-04"]
)
print(message.content)
```

Pin SDK and model versions used for the release run and verify the current Anthropic beta header before deployment. This example does not imply that Ninai can observe unrelated Claude conversations.

Official reference: [Anthropic Messages API MCP connector](https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector).
