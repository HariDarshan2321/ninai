# Ninai hosted store

This package is the explicit opt-in PostgreSQL backend. It does not import,
inspect, or synchronize the local SQLite vault.

## Local hosted development stack

From the repository root, Docker Compose can start an isolated PostgreSQL
database, apply migrations, and run the PAT-mode cloud service:

```bash
scripts/ninai-cloud-local setup
scripts/ninai-cloud-local doctor
scripts/ninai-cloud-local bootstrap --email you@example.com
```

The bootstrap command prints separate Claude, Codex and owner operator tokens
once, plus `control_pat_sha256`. Keep them out of shell history and source control.
For the local owner dashboard, set `NINAI_CONTROL_PAT_SHA256` to that digest in
the environment used by Compose, then run `scripts/ninai-cloud-local start` to
recreate the service with the new setting. Open `/control` and use only
`tokens.operator` in the self-hosted access-token field. Keep it out of assistant
and editor configurations; give those only their respective Claude/Codex tokens. The compose defaults are
intentionally development-only (`ninai-local-dev-only`) and may be overridden
with `NINAI_DEV_DB_PASSWORD`, `NINAI_DEV_DB_PORT`, and
`NINAI_DEV_CLOUD_PORT`. The MCP endpoint is `http://localhost:8000/mcp` by
default. Run `scripts/ninai-cloud-local stop` to stop containers; the named
PostgreSQL volume is retained. This stack has no mount for `~/.ninai` and never
reads, uploads, or synchronizes the independent desktop SQLite vault.

The local compose stack is for loopback development only: it uses HTTP and PAT
authentication and is not a production deployment recipe.

Apply migrations:

```bash
DATABASE_URL=postgresql://... python -m ninai_cloud.migrations
```

Run the authenticated Streamable HTTP MCP service after configuring the OAuth
issuer values shown in `.env.example`:

```bash
ninai-cloud-mcp
```

The included container runs `python -m ninai_cloud.migrations` before executing
the service, stops on migration failure, runs the service as a non-root user,
and includes a `/health` container check. The image remains provider-neutral and
requires externally managed PostgreSQL, HTTPS ingress, secrets, OAuth/OIDC, and
initial provisioning for a public deployment.

The service exposes `GET /health`, MCP at `/mcp`, and RFC 9728 protected-resource
metadata. Its `search`, `fetch`, and `recall` tools enforce live client grants and
write disclosure logs. `propose_memory` requires propose permission; `remember`
requires a separate auto-activate grant. Every returned or stored memory includes
its source URI. Local SQLite data is never read or synchronized by this process.

### Self-hosted personal access tokens

OAuth remains the default. For a private self-hosted server, explicitly set
`NINAI_AUTH_MODE=pat` and `NINAI_PUBLIC_RESOURCE_URL` to the externally reachable
MCP URL. Bootstrap a workspace, project, distinct Claude/Codex clients, grants,
and credentials with:

```bash
DATABASE_URL=postgresql://... ninai-cloud-bootstrap --email you@example.com
# Set NINAI_CONTROL_PAT_SHA256 in the service environment to the bootstrap
# control_pat_sha256 value before starting the owner dashboard.
NINAI_AUTH_MODE=pat NINAI_PUBLIC_RESOURCE_URL=https://ninai.example/mcp ninai-cloud-mcp
```

The bootstrap command prints each token exactly once. Ninai stores only SHA-256
digests. Tokens expire (90 days by default), and token, client, membership, or
workspace revocation takes effect on the next request. Use a different token for
Claude and Codex, keep them out of source control, and terminate TLS at the server
or a trusted reverse proxy.

The bootstrap also creates a distinct `operator_client` with no memory grants.
Use its one-time `tokens.operator` only in the owner dashboard at `/control`.
Set the server environment `NINAI_CONTROL_PAT_SHA256` to the returned
`control_pat_sha256` and restart the service. The setting accepts comma-separated
SHA-256 hex digests for explicitly approved operator PATs. Its empty default
blocks PAT dashboard access while agent PATs continue to work for scoped MCP
requests. Never put the operator PAT into Claude, Codex, editor settings or chat,
and never allowlist an existing agent PAT to restore dashboard access.
Operator PATs still require active membership, workspace, connection and
owner/admin role checks; the allowlist does not bypass revocation.

For an existing private PAT workspace, provision a separate operator credential
with the existing workspace and active owner/admin user UUIDs:

```bash
# DATABASE_URL is already supplied securely in the operator environment.
ninai-cloud-bootstrap --operator-workspace WORKSPACE_UUID --operator-user OWNER_USER_UUID
```

This adds only a dedicated operator connection and PAT; it does not create a new
workspace or grant memory access. Set its returned digest in
`NINAI_CONTROL_PAT_SHA256`, restart the service, and keep the operator token in
the owner dashboard only. Do not pass `--email` in this mode. A normal bootstrap
with `--email` creates a new workspace and does not adopt an existing one.
For rotation, configure only approved operator digests and revoke the old token;
removing a digest blocks its dashboard access on the next request.

### Machine clients (PAT in OAuth mode)

Clients that cannot complete OAuth, such as Claude Code cloud routines, can use a
personal access token against an OAuth-mode server. Set `NINAI_OAUTH_ALLOW_PAT=true`
(default `false`); tokens starting with `ninai_pat_` are then verified as PATs and
everything else as OAuth JWTs. The control plane stays OAuth-only.

Mint a token as a workspace owner/admin for an existing, active connection:

```bash
curl -X POST https://app.ninai.io/api/control/connections/<connection_id>/tokens \
  -H "Authorization: Bearer <control OAuth token>" -d '{"label":"claude-routine"}'
```

The response contains `personal_access_token` exactly once and expires in 90 days.
Store it as a Claude cloud network secret for host `app.ninai.io`, so the proxy
injects `Authorization: Bearer ninai_pat_...`. The token acts as the connection: it
is read, propose and remember by scope, but project grants on the connection are
still required for any memory access, and the usual rate limits apply. Revoking the
connection revokes its tokens.

Run tests (integration tests require a disposable database):

```bash
python -m unittest discover -s tests -v
NINAI_TEST_DATABASE_URL=postgresql://... python -m unittest discover -s tests -v
```

Deployment, client, and release evidence:

- [Deployment guide](../docs/DEPLOYMENT.md)
- [Claude Code and Codex setup plus OpenAI/Anthropic API examples](../docs/HOSTED-BETA.md)
- [Compatibility matrix](../docs/COMPATIBILITY.md)
- [Hosted security report](../docs/SECURITY-REPORT.md)
- [Cross-provider release-gate report](../docs/CROSS-PROVIDER-SMOKE-TEST.md)
- [Launch checklist](../docs/HOSTED-LAUNCH-CHECKLIST.md)
- [Known limitations](../docs/KNOWN-LIMITATIONS.md)

The real Claude Code → Codex → Claude Code round trip and existing-token revocation gate passed locally in explicit PAT mode on 25 July 2026. Automated protocol and PostgreSQL tests also pass. Production OAuth/HTTPS deployment remains a separate unverified gate.

## Authentication boundary

OAuth is the default hosted boundary, and Ninai is a protected resource rather
than an authorization server. Configure an external OAuth/OIDC issuer using
`.env.example`. OAuth access tokens must be asymmetric signed JWTs with matching
`iss`, `aud`, and unexpired `exp` claims. The signed external `sub` and OAuth
`client_id` (or Auth0 `azp`) map to Ninai's internal UUID user, workspace, and
client connection. Explicit PAT mode instead resolves the opaque token's stored digest
to that same fixed principal; request bodies and query strings are never trusted
for identity in either mode.

Every authenticated request also checks the current PostgreSQL client,
membership, workspace, and user state, so revoking a client takes effect on its
next request even if its token has not expired. Serve
`AuthSettings.protected_resource_metadata()` from
`/.well-known/oauth-protected-resource`; the configured issuer remains
responsible for authorization-server discovery, login, consent, and tokens.

See [Auth0 deployment adaptation](../docs/AUTH0.md) for DCR and tenant setup.
