# Hosted onboarding test: 2026-11-15

## Verified outcome

The real hosted Codex CLI path passed: OAuth login, discovery with no grants, explicit Read + Propose access to a new synthetic project, proposal storage, exclusion before approval, owner approval in the dashboard, source-backed recall from a fresh client session, immediate denial after grant revocation, and rejected MCP initialization after connection disconnect. The synthetic active memory remains in the cloud dashboard. The test connection is deliberately left revoked, with no test project access. Existing connections and the prior memory in this account were not modified.

This is not a verified branded ChatGPT plugin flow, reconnect recovery test, fresh-account signup, or production-readiness certification. The current chat still exposes only local Ninai tools; the hosted tests ran in fresh ephemeral Codex CLI sessions configured with the canonical hosted server and without the local server. No local vault contents were uploaded.

After the owner-approved assistant registration reset, a separate direct ChatGPT custom connector also passed real OAuth, no-grant discovery, recall of the Codex-created synthetic decision with its original source, and immediate denial after its Read grant was revoked. This test connector is named **Ninai cloud verification**. It is not the branded ZIP plugin version 0.1.2.

## Owner-approved Auth0 cleanup and direct ChatGPT test

The owner explicitly approved permanent deletion of the nine assistant OAuth registrations shown in the dashboard: ChatGPT ×1, Claude ×2, Claude Code ×1, Codex ×4, and Ninai Claude Codex ×1. Each deletion was performed through its own Auth0 confirmation dialog after checking its client ID. The Ninai website sign-in application was preserved. A refreshed application list showed only that website application after cleanup.

The existing signed-in Ninai dashboard remained accessible and showed both approved memories, including the synthetic test decision. No user or memory deletion was performed.

A single changed-condition retry of ChatGPT's Add custom MCP server flow then succeeded:

1. Canonical URL https://app.ninai.io/mcp; OAuth discovery completed with DCR available.
2. Base/OIDC scopes limited to openid/profile/email.
3. Create as a plugin reached the real Connect dialog, unlike earlier attempts at full capacity.
4. Auth0 consent identified ChatGPT and chatgpt.com; OAuth callback returned successfully.
5. ChatGPT settings showed a connected account, canonical MCP URL, and Authorization used: OAuth.
6. In an actual ChatGPT web conversation, the connector's projects tool initially returned count=0.
7. The exact new client appeared in the matching Ninai dashboard. Only Read access was granted to the synthetic project.
8. Asked to discover the project and browse its approved decision without providing the decision text, ChatGPT returned the emerald-checklist decision created via Codex and source ninai-test://2026-11-15/cloud-onboarding.
9. The owner UI revoked that Read grant. A fresh ChatGPT recall call returned ok=false, forbidden, Client lacks can_read for requested scope, with no memory content.

Final provider inventory: two application registrations, Ninai website sign-in and the new ChatGPT test client. The new ChatGPT connector remains authenticated with no project grant. The branded ZIP installation, ChatGPT proposal/approval writes, and reconnect recovery are not verified by this read/revoke test.

Operational distinction: deleting OAuth registrations is not the same as revoking Ninai's own connection records or already-issued access tokens. Historical Ninai connection records remain and can still be labelled active. Do not claim every previously issued token was immediately invalidated by the Auth0 cleanup; Ninai-side grant/connection revocation is the tested immediate enforcement mechanism. Registration capacity/reuse still needs a sustainable launch decision.

## Initial observations in a different dashboard identity

- Approved memories: 0.
- Awaiting review: 0.
- Project: Fresh onboarding test · 2026-11-15.
- Active connection records: 1, an older Claude connection.
- No new ChatGPT connection record was visible.

Local installation separately saved a synthetic decision and retained it after restarting. That is not a hosted storage or ChatGPT test.

## Current blocker

The imported branded plugin is version 0.1.2 and declares https://app.ninai.io/mcp. Installation exposes its continuity skill, but this chat exposes only ninai_local tools. A reported local vault health result cannot verify hosted authentication. The old custom connector uses the retired Render resource and is disconnected. Earlier custom connector creation against the canonical resource was rejected before OAuth; its cause remains unverified.

The plugin overview has no visible Connect control. Automated inspection of the desktop host was denied by the computer-use safety policy. Do not work around that restriction or repeat the blocked external-app launch. Owner inspection of the installed plugin's server connection settings is required to resolve the missing hosted registration/authentication evidence.

## Test chronology and remaining acceptance

### Confirmed registration failure

The desktop configuration contains a remote server named `ninai` pointing to the canonical hosted URL, alongside a separate local server. Running `codex mcp login ninai` failed before opening authorization:

> Registration failed: HTTP 403 Forbidden. You reached the limit of entities of this type for this tenant. errorCode: too_many_entities.

This establishes an Auth0 dynamic-client-registration quota failure for this desktop connection. It does not independently establish the cause of the earlier ChatGPT custom-plugin creation rejection. No token or header is needed in the screenshot's empty fields to solve this quota. Next inspect Auth0 application registrations with the owner: identify recoverable capacity or configure a dedicated, supported pre-registered public client. Do not delete active applications or reuse a confidential web application's credentials in a public client.

The owner confirmed Default App was unused and explicitly approved permanent deletion. It was deleted through the Auth0 dashboard; after refresh it was absent and nine applications remained. Only this approved application was removed. Retrying `codex mcp login ninai` then passed DCR and produced an authorization URL. The real Ninai login page opened for Codex, with credentials left to the owner. The authorization request was narrowed to openid/profile/email/offline_access rather than the provider's full advertised profile-scope list. Only email/password is visible on this client login page; Google sign-in was not offered. OAuth completion, new cloud connection, and memory tests are still pending. The CLI login session remains waiting for its callback; do not start repeated new registrations.

Subsequently the owner completed email/password authentication. The CLI exited 0 with `Successfully logged in to MCP server 'ninai'`. A fresh ephemeral Codex CLI session configured with only the canonical hosted server successfully called `ninai/projects` and returned `{"ok":true,"projects":[],"count":0}`. This is a real hosted read call with no project grants; it is not a local-vault result or a ChatGPT plugin acceptance test. The previous dashboard still showed only its older Claude connection after refresh. Because that earlier dashboard session used Google and the owner confirmed email/password for Codex, a possible distinct-identity mismatch is being checked. The dashboard was signed out and its real login page reopened; owner must use the same email/password identity as Codex before further grants. No accounts have been linked, no new grants created, and no cloud memories written.

### Completed after matching dashboard sign-in

The owner signed into the dashboard with the same email/password identity used for Codex. This account displayed the exact new OAuth client connection, seven active connections, one prior approved memory, and an existing continuity-test project. This confirmed that the initial zero-memory dashboard represented a different identity. Accounts were not linked by matching email.

| Check | Actual result |
| --- | --- |
| New isolated project | Fresh cloud onboarding test · 2026-11-15 created through the dashboard |
| Explicit access | Only the new client received Read + Propose on the synthetic project; auto-activation false |
| Proposal | Stored as proposed through hosted propose_memory |
| Pending recall | Fresh hosted recall returned facts=[] before approval |
| Approval | Dashboard approval increased approved memories from 1 to 2 and cleared the review queue |
| Fresh-session recall | Exactly one active decision returned, with the expected content and original source |
| Disclosure history | The two successful recall requests appeared in the dashboard, including the empty preapproval recall |
| Grant revocation | Dashboard confirmed Project access revoked |
| Fresh recall after revocation | projects returned count=0; recall returned forbidden: Client lacks can_read for requested scope; no memory content |
| Disconnect | Only the new test connection was disconnected; active connection count changed from 7 to 6 |
| Fresh client after disconnect | MCP handshake failed with Auth required before a projects tool became available |
| Stored data after disconnect | Dashboard Memories search still showed the active synthetic decision with its source |

Synthetic content: `Fresh cloud onboarding test decision: use the emerald checklist for release reviews.`

Source: `ninai-test://2026-11-15/cloud-onboarding`. No personal content or local memory was used.

### Remaining blockers

- The branded ChatGPT plugin still needs its own hosted authentication and complete test. Do not treat Codex CLI success as ChatGPT acceptance.
- Reconnecting a disconnected client has not been tested. Revoked bindings must not silently reactivate. A clear owner-approved recovery path remains to be verified.
- Freeing one application slot allowed this one registration; it is not a sustainable solution to the tenant's 10-application limit. The new registration consumes that slot. Provider capacity or supported client reuse needs a deliberate launch decision, not automatic deletion of existing clients.
- The UI says only Signed in and shows generic OAuth MCP client names. The account and connection identity confusion encountered here remains an onboarding usability issue.
- Source-only skill hardening and this report have not updated the installed plugin.

The following sequence is now completed for Codex CLI and remains pending for the branded ChatGPT plugin:

1. Complete the canonical hosted connector OAuth flow; verify its new record in this dashboard.
2. Grant Read and Propose only to the synthetic test project.
3. Through that hosted assistant, propose one harmless decision with a source.
4. Approve it in the dashboard; confirm the persisted memory and provenance.
5. Recall through a fresh hosted tool request; confirm the disclosure record.
6. Revoke the project grant; confirm the next fresh recall is denied.
7. Disconnect/reconnect and check the actual grant state without assuming it resets.

The plugin source instructions now explicitly refuse local-tool fallback when invoked as the hosted plugin. Packaging policy and three packaging regression tests pass. These are source-only changes, not an installed-plugin update or a successful live authentication test. Do not announce this flow as verified or production ready.

## Follow-up: reconnect recovery and private connected package

These are source changes with automated tests. Live acceptance is recorded
separately below and is not implied by passing tests.

- **Reconnect recovery.** The dashboard now offers Reconnect on a disconnected
  OAuth connection. `POST /api/control/connections/{id}/reconnect` requires a
  workspace admin who owns the connection and an unrevoked OAuth binding. It
  restores only the connection. Every project grant stays revoked, and the
  owner must choose access again.
- **Old access tokens stay dead.** Disconnect marks the connection revoked but
  does not revoke its personal access tokens; they stopped working only because
  the connection was inactive. A first version of reconnect therefore made a
  token issued before the disconnect authenticate again. Reconnect now revokes
  every unrevoked token of that connection. A regression test reproduces the
  revival on the earlier code.
- **Private connected package.** `scripts/build_official_plugins.py
  --registered-app-id <id>` builds `ninai-openai-connected-<version>.zip`, which
  references an already registered ChatGPT connector through `.app.json` and
  ships no second MCP server definition. It is for private or workspace use,
  not public submission. A mapping grants no access.
- **Skill hardening.** Plugin 0.1.3 tells the assistant to use only this
  plugin's hosted tools and to stop, rather than fall back to `ninai_local`
  tools, when the hosted connection is unavailable.

Automated evidence: 147 cloud tests passed against a disposable PostgreSQL 16
container (one restore-rehearsal test skipped, as before), including three
reconnect tests; 4 packaging tests passed; package policy check passed for
0.1.3.

## Release status after the follow-up

- `a555074` added reconnect recovery, token revocation on reconnect and the
  private connected package. Its CI failed for two reasons that were fixed in
  `5d3978b`: the engine's bundled Codex skill no longer matched the plugin
  copy, and one browser test raced an automatic Home reload.
- CI run 43698976086 on `5d3978b` passed all five jobs.
- **Not deployed.** After that run, public `/health` still reported revision
  `cadeeff`. Render deploys the `cloud` root after passing checks; the commit
  with the cloud change failed its checks and the fixing commit changed nothing
  under `cloud/`. The reconnect endpoint and dashboard button are therefore not
  live. A deliberate deployment of `5d3978b` and a `/health` revision check are
  required first.

Still not verified live:

1. Reconnect recovery in the real dashboard: reconnect the disconnected test
   connection, confirm zero project access, confirm a fresh assistant session
   sees no projects until access is granted again.
2. The branded package in ChatGPT: build the connected package with the
   registered connector ID, install it, then run propose, approve, recall and
   revoke through it.
3. A fresh-account signup journey.

Do not describe hosted onboarding as production ready until these pass.

## Deployment of the follow-up

`b94d453` set the cloud service version to 0.1.2. CI run on that commit passed
all five jobs and Render deployed it automatically; no manual deployment was
used and the auto-deploy setting was not touched. Public `/health` reports
version 0.1.2 at revision `b94d453dee080970f0d84b992364a5fa6d75ed62`, and
`/ready` returns 200. The served dashboard script contains the reconnect
action, and the reconnect route answers 401 without a session.

This supersedes the "Not deployed" note above. It is a deployment check only.
The signed-in reconnect test, the branded package test in ChatGPT and the
fresh-account signup remain unverified.

## Live reconnect check in the owner dashboard

Run on the deployed 0.1.2 service, signed in as the same account that owns the
test connections, with the owner present.

| Check | Actual result |
| --- | --- |
| Before | Test connection `tpc_4G1Y…` shown as revoked with a Reconnect button; 7 active connection records |
| Confirmation | In-page prompt stated that previous project permissions stay off |
| After confirm | Notice: "Connection restored with no project access"; 8 active connection records |
| Connection state | Same client now active, with the project selector unset |
| Earlier grant | Still listed as Read Propose **Revoked** for the synthetic project; no active grant for this client |
| Other connections | Unchanged; two older disconnected connections were left disconnected |
| Memories | Unchanged; both approved memories still listed |

Not covered by this check: a fresh assistant session through the reconnected
client. The Codex account used for the earlier hosted test had no remaining
usage, so "projects returns none until access is granted again" is verified
by the database integration tests only, not by a live assistant call. The
reconnected test connection is left active with no project access.
