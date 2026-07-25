# Deployment

Ninai has two independent deployment surfaces: the static marketing website and the opt-in hosted MCP beta. Local SQLite remains a separate on-device mode and is never uploaded by either deployment.

## Hosted MCP beta

For local development, the repository-level `compose.yaml` is the supported
bootstrap path. `scripts/ninai-cloud-local setup` starts PostgreSQL, waits for
it, runs all migrations exactly once per version, starts the cloud service, and
checks readiness. `scripts/ninai-cloud-local doctor` checks containers,
database connectivity, migration state, and HTTP health. The compose stack uses
documented development-only credentials and must not be exposed publicly. It
does not mount or access the local desktop vault.

### Prerequisites

- Python 3.11+ or the included Python 3.12 container
- PostgreSQL reachable only from the application network
- For public/multi-user hosting, an external OAuth/OIDC issuer that issues asymmetric-signed JWTs; or, for private self-hosting only, explicit PAT mode
- A public HTTPS URL for MCP and, in OAuth mode, public issuer discovery/JWKS
- Provisioned users, workspaces, memberships, projects, client connections, and grants

In OAuth mode, Ninai does not issue tokens. The issuer must place `sub`, `ninai_workspace_id`, and `ninai_client_connection_id` in signed tokens, plus matching `iss`, `aud`, `resource`, and unexpired `exp` claims.

### Configure and migrate

Start from `cloud/.env.example`. Required values are:

```dotenv
DATABASE_URL=postgresql://ninai:<secret>@<private-host>:5432/ninai
HOST=0.0.0.0
PORT=8000
NINAI_OAUTH_ISSUER=https://<issuer>
NINAI_OAUTH_AUDIENCE=ninai-cloud
NINAI_OAUTH_JWKS_URI=https://<issuer>/.well-known/jwks.json
NINAI_OAUTH_AUTHORIZATION_ENDPOINT=https://<issuer>/oauth2/authorize
NINAI_OAUTH_TOKEN_ENDPOINT=https://<issuer>/oauth2/token
NINAI_PUBLIC_RESOURCE_URL=https://<api-host>/mcp
NINAI_OAUTH_WORKSPACE_CLAIM=ninai_workspace_id
NINAI_OAUTH_CLIENT_CONNECTION_CLAIM=ninai_client_connection_id
```

Apply migrations from the `cloud/` directory before starting the new application version:

```bash
python -m ninai_cloud.migrations
ninai-cloud-mcp
```

For a private self-hosted smoke test, explicitly use PAT mode and bootstrap one personal workspace. The command prints two credentials once; save them only in a protected secret store and never commit them:

```bash
export DATABASE_URL='postgresql://ninai:<secret>@<private-host>:5432/ninai'
ninai-cloud-bootstrap --email you@example.com --workspace 'Personal Ninai' --project 'Shared AI Memory'
export NINAI_AUTH_MODE=pat
export NINAI_PUBLIC_RESOURCE_URL='https://<api-host>/mcp'
export HOST=0.0.0.0
ninai-cloud-mcp
```

The bootstrap creates distinct Claude and Codex connections with project read, propose, and auto-activate grants. Tighten those grants after the acceptance run. PATs expire after 90 days by default and can be configured with `--expires-days`.

Or build and run the included image:

```bash
docker build -t ninai-cloud:beta cloud
docker run --rm -p 8000:8000 --env-file cloud/.env -e HOST=0.0.0.0 ninai-cloud:beta
```

The image does not include PostgreSQL, TLS termination, an OAuth issuer, provisioning, migrations at startup, the control-center WSGI deployment, or a reverse proxy. Operate those separately; do not treat the image as a complete production stack.

### Verify staging

```bash
curl --fail https://<api-host>/health
curl --fail https://<api-host>/.well-known/oauth-protected-resource/mcp
curl -i -X POST https://<api-host>/mcp -H 'content-type: application/json' -d '{}'
```

The final request must be rejected with `401` and a `WWW-Authenticate` challenge pointing to resource metadata. Then run the suites:

```bash
cd cloud
python -m unittest discover -s tests -v
NINAI_TEST_DATABASE_URL=postgresql://... python -m unittest discover -s tests -v
```

Use a disposable database for integration tests. Confirm the PostgreSQL lifecycle tests ran rather than reporting `skipped`. Complete [CROSS-PROVIDER-SMOKE-TEST.md](CROSS-PROVIDER-SMOKE-TEST.md) against the deployed release; the hosted gate remains failed until the signed report is complete.

The deterministic service-level semantics can also be checked with:

```bash
NINAI_TEST_DATABASE_URL=postgresql://... python ../scripts/verify_cross_provider.py
```

That verifier models distinct Claude and Codex principals but deliberately records `host_invocation: not_run`; it does not replace the recorded real-host gate. The local PAT-backed real-host run passed on 25 July 2026, while a production OAuth/HTTPS run remains outstanding.

Client registration and API examples are in [HOSTED-BETA.md](HOSTED-BETA.md). Deployment security requirements and unresolved risks are in [SECURITY-REPORT.md](SECURITY-REPORT.md) and [HOSTED-LAUNCH-CHECKLIST.md](HOSTED-LAUNCH-CHECKLIST.md).

## Static website

### Vercel (recommended)

Import the repository, set the project root to `website`, keep Next.js detection and `npm run build`, deploy a preview, then add `ninai.io` and `www.ninai.io`. Make the apex canonical and redirect `www` to it.

Official references:

- <https://vercel.com/docs/frameworks/full-stack/nextjs>
- <https://vercel.com/docs/deployments/overview>
- <https://vercel.com/docs/domains/working-with-domains/add-a-domain>

### GitHub Pages

The repository includes `.github/workflows/pages.yml`. Select GitHub Actions as the Pages source, configure the custom domain, update DNS using GitHub's apex-domain instructions, and enable HTTPS after verification.

- <https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>
- <https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site>

### Cloudflare Pages

Use root `website`, build command `npm run build`, and output directory `out`. An apex domain on Cloudflare Pages requires the domain to be a Cloudflare zone.

- <https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/>
- <https://developers.cloudflare.com/pages/configuration/custom-domains/>

### Website release checks

```bash
cd website
npm ci
npm audit --audit-level=moderate
npm run typecheck
npm run build
python3 ../scripts/validate_website.py
```

Verify the production URL, canonical redirect, TLS, forms, source links, sitemap, robots file, and visible compatibility claims after DNS changes. Keep hosted wording at “in development” until the production OAuth/HTTPS gate passes.
