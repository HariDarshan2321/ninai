# Production sign-in preparation

Prepared 14 November 2026. No Auth0, Google, DNS or Render authentication settings
were changed. The reported Dev Keys warning has not been independently inspected
inside the owner's provider dashboards. It is consistent with Auth0's documented
shared social test credentials; it is not by itself proof of a failed sign-in.

## First: owned Google credentials, same Auth0 domain

The owner must use their own Google Cloud and Auth0 dashboards. Create or select
the appropriate Google OAuth application and configure its consent/branding and
authorized redirect URI using the exact callback shown in Auth0's Google
connection. With the current tenant domain this is that domain's
`https://…/login/callback`, not Ninai's control callback. Observe Google's current
publishing/verification requirements for the selected audience and scopes.

Enter the resulting client ID and secret directly in Auth0's existing Google
social connection. Do not paste the secret into chat, Git, Render, a recording,
or this document. Keep the same connection and avoid creating replacement user
accounts as a shortcut. This credential step does not require changing Ninai's
token issuer or Render environment. Check existing-account and new dedicated
reviewer-account sign-in, callback, logout and returning sessions, then verify
that existing workspace ownership and access remain intact.

Auth0's guidance:

- [Development-key warning and dedicated credentials](https://support.auth0.com/center/s/article/Warning-Occurs-About-Development-Keys-When-Tenant-Is-In-Production)
- [Google social production setup](https://developer.auth0.com/resources/labs/authentication/google-social-connection-to-login)
- [Why development keys fail with custom domains](https://support.auth0.com/center/s/article/Can-not-login-with-Google-on-a-custom-domain)

## Separately: optional custom authentication domain

Do not combine an untested domain migration with the first credential fix before
the Monday demo. Confirm current Auth0 plan eligibility, actual cost, billing
requirements and domain ownership in the owner's dashboard. No subscription,
credit-card action, DNS modification or custom-domain purchase is authorized by
this preparation. Obtain the exact DNS record from Auth0 rather than inventing
a target. Complete domain/certificate verification before changing applications.

For a proposed `auth.ninai.io`, retrieve its public OpenID configuration after
verification and use the returned issuer and endpoints verbatim. Render changes
to prepare and review together:

| Setting | Prepared source |
| --- | --- |
| `NINAI_OAUTH_ISSUER` | Discovery `issuer`, including its exact trailing slash |
| `NINAI_OAUTH_JWKS_URI` | Discovery `jwks_uri` |
| `NINAI_OAUTH_AUTHORIZATION_ENDPOINT` | Discovery `authorization_endpoint` |
| `NINAI_OAUTH_TOKEN_ENDPOINT` | Discovery `token_endpoint` |
| `NINAI_OAUTH_AUDIENCE` | Preserve the existing API identifier; do not replace it with the auth domain |

Keep `NINAI_PUBLIC_RESOURCE_URL`, `NINAI_CONTROL_BASE_URL`, control application
client identity and Ninai resource URLs unchanged unless a separate verified
requirement calls for changing them. Inspect any registration/discovery settings
used by the actual MCP clients as part of the acceptance run. Do not weaken
issuer/audience validation or disable TLS to make a migration pass.

Before applying, privately retain the old configuration for rollback and arrange
a change window. A new issuer affects validation of old tokens; canonical-domain
browser sessions do not automatically become custom-domain sessions. Require
fresh sign-in/authorization in the acceptance checks, preserve workspace and
connection ownership, and communicate any actual reconnect requirement. Do not
promise a seamless session migration.

Retest dedicated-account login, CSRF/state/nonce failures, callback/logout,
protected-resource metadata, OAuth authorization, real Claude Code/Codex cloud
recall and save, denied project access, revocation and a returning existing user.
Confirm `/ready` plus the deployed revision; health alone does not validate login.
If these fail, restore the prior coordinated settings and verify the old flow.

- [Auth0 custom-domain setup and token issuer/audience behavior](https://auth0.com/blog/custom-domains-complete-guide/)
- [Feature configuration and session implications](https://support.auth0.com/center/s/article/Configure-Features-to-Use-Custom-Domains)

## Demo scope and security wording

Demonstrate the actually verified Mac Claude Code → Codex flow. Present other
hosts as pending where that is their recorded status; do not repeat the broad
intro email as compatibility evidence. A configured connection is not a passed
recall test.

The local SQLite vault has no application-level encryption. Hosted memory is not
end-to-end encrypted. Those facts do not establish that Render lacks storage
encryption: verify the provider configuration before making an at-rest claim.
Live restore acceptance, legal operator details and retention/account-erasure
procedures remain separate open gates in the launch acceptance document.
