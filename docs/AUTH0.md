# Auth0 deployment adaptation

Auth0 owns authorization, login, consent, PKCE, refresh tokens, and dynamic
client registration (DCR). Ninai maps `(issuer, sub)` to an internal UUID user
and `(issuer, client_id/azp, user, workspace)` to an internal client connection.
An Auth0 subject such as `auth0|abc123` is never inserted into a UUID column.

Register the `tpc_…` client ID returned by DCR when creating the matching Claude
or Codex connection in the control center. Binding a client grants no memory
scope; read/propose/auto-activate grants remain explicit Ninai actions.

## Tenant configuration still required

1. Create an Auth0 API whose Identifier exactly equals the public MCP URL, for
   example `https://mcp.ninai.io/mcp`. Use RS256 and define `ninai:read`,
   `ninai:propose`, and `ninai:remember` permissions.
2. Enable the RFC 9068 access-token profile so tokens carry `client_id`. Ninai
   also accepts Auth0's default `azp` claim.
3. Enable DCR under **Settings → Advanced**. Auth0 DCR is open registration, so
   configure the DCR tenant ACL and operational monitoring before launch.
4. Configure third-party application default API access for the Ninai API.
   DCR-created clients otherwise receive no API access.
5. Configure Universal Login, consent, MFA, refresh-token rotation, attack
   protection, signing-key rotation, and callback/logout URLs for the tested
   Claude and Codex hosts.
   Create a separate public SPA application for the Ninai dashboard, allow the
   exact `${NINAI_CONTROL_BASE_URL}/control` as its callback, the base URL as
   its web origin, and place its
   non-secret client ID in `NINAI_OAUTH_CONTROL_CLIENT_ID`. The dashboard uses
   Authorization Code with PKCE; it never requires a client secret.
6. Set `cloud/.env.example` values. Preserve Auth0's canonical issuer trailing
   slash. OAuth audience and `NINAI_PUBLIC_RESOURCE_URL` must be identical.
7. For a user in multiple workspaces, add a Post-Login Action that emits the
   selected UUID as `https://ninai.io/workspace_id`. Single-workspace users do
   not require this custom claim.
8. Apply `0004_oauth_identity_mapping.sql`, sign into `/control`, create a
   connection with the DCR `tpc_…` client ID, then explicitly grant scopes.

## Dashboard customer journey

The customer opens `/control` and chooses **Create account** or **Sign in**.
Ninai creates a one-time PKCE verifier and state in Secure, HttpOnly, SameSite
cookies, then redirects to Auth0 Universal Login. Auth0 returns the authorization
code to `/control`; Ninai validates state, exchanges the code with the PKCE
verifier, and stores only the short-lived access token in a Secure, HttpOnly
cookie. Dashboard API requests use that cookie and require a same-origin check
for mutations. **Sign out** clears the Ninai browser session. Auth0 SSO logout
can be added later if product policy requires terminating the tenant-wide SSO
session as well.

## Universal Login branding still required in Auth0

The repository controls the Ninai dashboard after Auth0 redirects back. Auth0
Universal Login is tenant-hosted, so align it separately in **Branding →
Universal Login** and the `Ninai Dashboard` application:

- application name: `Ninai`;
- logo URL: `https://ninai.io/assets/ninai-app-icon.svg`;
- primary action: Signal `#FF6846`;
- page background: Paper `#F4EFE5`;
- text/contrast: Ink `#111512` and Vault `#0B302B`;
- concise prompt: `Your AI should remember the work. Not your whole life.`;
- support/privacy links on `ninai.io`, with no claims of universal capture,
  end-to-end encryption, or completed independent security audit.

Permit `#DCEF7B` is reserved for an explicitly allowed state and should not be
used as general login decoration. Preview sign-up, sign-in, consent, password
reset, MFA, error, and narrow mobile layouts before the external tester gate.

Auth0 DCR clients require PKCE and support authorization-code and refresh-token
grants. The host must store and reuse a registration rather than creating a new
application on each login.

Official references:

- [Auth0 Dynamic Client Registration](https://auth0.com/docs/get-started/applications/dynamic-client-registration)
- [Auth0 custom claims](https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims)
- [Auth0 token structure](https://auth0.com/docs/secure/tokens)
