# Platform admin dashboard

The hosted account service now includes `/control/admin`. This is a read-only
operator dashboard, separate from each customer's workspace permissions.
A workspace owner or admin does **not** receive platform access.

## What it shows

- Active accounts, new accounts in seven days, unique accounts signed in during
  seven days, and unique active accounts that requested an official installer.
- Searchable, paginated accounts: name, email, signup date, last successful
  browser sign-in, login count, installer-download count, and hosted connections.
- Account detail: internal user ID, account status, workspaces and roles,
  hosted connection status/last activity, and the latest installer receipts.
  Each detail section is bounded to 100 records.

A download is not proof that installation succeeded. No local installation
telemetry, local agent activity, memory bodies, transcripts, tokens, or passwords
are available through these admin endpoints. Counts are real database values;
the page does not use demonstration data.

## Enable your owner account

The designated founder email is `darshan@ninai.io`; `hello@ninai.io` handles
support. Creating the mailbox alone does not create a Ninai account or grant
admin access. Complete the account sign-in and bind its verified UUID below.

1. Deploy migration `0008_account_login_activity.sql` before the new service.
   The existing container entrypoint applies migrations automatically.
2. Sign in using the owner account. With the new service deployed, open
   `/api/control/account` in that signed-in browser to obtain its `user_id`.
   Alternatively, resolve the exact `(issuer, subject)` in `oauth_identities`
   through your existing authenticated database operator workflow. Do not
   identify an administrator by an unverified email.
3. Set `NINAI_PLATFORM_ADMIN_USER_IDS` in Render to that internal UUID. More
   than one explicitly authorized UUID can be comma-separated. Empty disables
   all platform access. Invalid UUIDs stop startup rather than widen access.
4. Redeploy the service, sign out, and sign in again. Your dashboard login now
   redirects to `/control/admin`. Regular accounts still go to `/control`.
   Already signed-in admins can use the Admin dashboard link on Mac setup.
5. Verify a separate ordinary account receives 403 from the page and every
   `/api/control/admin/*` endpoint. Missing/invalid credentials receive 401.

The server checks the UUID allowlist and current undeleted account on every
admin request. OAuth mode additionally requires a token issued to the configured
dashboard client, so a token issued to a connected MCP client cannot be used for
platform administration, even when its account belongs to an administrator.
Do not use self-hosted PAT mode for the public service.

## Login tracking and profile data

The callback validates the exchanged access token before creating the session
cookie. Only completed dashboard callbacks increment `login_count` and update
`last_login_at`. Refreshes, API requests, and MCP calls do not increment them.
Historical login counts are not backfilled from OAuth `last_seen_at` because
that field changes on API token validation too.

Auth0 access tokens may omit email/name. The callback requests the profile from
the configured issuer's `/userinfo`, requires the profile subject to match the
verified token subject, and stores only display name/email. A profile network
failure leaves the account's existing details unchanged and does not block a
valid login. Missing profile fields use existing account values; historical
accounts gain profile details on their next successful sign-in.

Display-only `profile_email`/`profile_name` fields never merge accounts or grant
permissions. Internal UUIDs remain authoritative. See the
[Auth0 UserInfo reference](https://auth0.com/docs/api/authentication/user-profile/get-user-info).

## Deployment and rollback

The migration only adds nullable profile/time fields, a login counter with a
zero default, and indexes. Old code can run with this schema, so code rollback
does not require dropping collected activity. Keep normal backup/restore
procedures. Publish the privacy-page update with the account-service change.

Before launch, run the database integration suite against a disposable staging
database with `NINAI_TEST_DATABASE_URL` configured. Then test a real Auth0 signup,
login, account profile, installer download, and owner/ordinary-account access
against the release deployment. Local unit tests do not prove a live OAuth flow
or successful Mac installation.
