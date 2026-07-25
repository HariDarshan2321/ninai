# Ninai hosted store

This package is the explicit opt-in PostgreSQL backend. It does not import,
inspect, or synchronize the local SQLite vault.

Apply migrations:

```bash
DATABASE_URL=postgresql://... python -m ninai_cloud.migrations
```

Run the authenticated Streamable HTTP MCP service after configuring the OAuth
issuer values shown in `.env.example`:

```bash
ninai-cloud-mcp
```

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

The real Claude → OpenAI → Claude round trip and existing-token revocation gate are still pending. Automated protocol tests do not establish compatibility with those live hosts.

## Authentication boundary

The hosted package is an OAuth protected resource, not an authorization
server. Configure an external OAuth/OIDC issuer using `.env.example`. Access
tokens must be asymmetric signed JWTs with matching `iss`, `aud`, `resource`,
and unexpired `exp` claims. The signed `sub`, `ninai_workspace_id`, and
`ninai_client_connection_id` claims identify the principal; request bodies and
query strings are never trusted for identity.

Every authenticated request also checks the current PostgreSQL client,
membership, workspace, and user state, so revoking a client takes effect on its
next request even if its token has not expired. Serve
`AuthSettings.protected_resource_metadata()` from
`/.well-known/oauth-protected-resource`; the configured issuer remains
responsible for authorization-server discovery, login, consent, and tokens.
