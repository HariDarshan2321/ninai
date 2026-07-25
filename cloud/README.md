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

The bootstrap command prints the Claude and Codex development tokens once.
Keep them out of shell history and source control. The compose defaults are
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
NINAI_AUTH_MODE=pat NINAI_PUBLIC_RESOURCE_URL=https://ninai.example/mcp ninai-cloud-mcp
```

The bootstrap command prints each token exactly once. Ninai stores only SHA-256
digests. Tokens expire (90 days by default), and token, client, membership, or
workspace revocation takes effect on the next request. Use a different token for
Claude and Codex, keep them out of source control, and terminate TLS at the server
or a trusted reverse proxy.

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
