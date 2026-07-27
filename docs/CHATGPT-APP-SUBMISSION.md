# ChatGPT app / plugin submission

> Current platform terminology (checked 27 July 2026): OpenAI moved public
> discovery from the App Directory to the **Plugin Directory** on 9 July 2026.
> An app remains the authenticated MCP integration; an approved public listing
> may distribute that app inside a plugin. Publishing a custom app to one
> workspace does not publish a public plugin listing.

## Live acceptance status

Validated on July 27, 2026 with a ChatGPT Plus account in developer mode. ChatGPT
completed Ninai OAuth, loaded the hosted MCP app, invoked the Ninai search tool,
and returned `0 results` for the synthetic query
`NINAI_CHATGPT_ACCEPTANCE_2026`. The connector call completed successfully.

The customer experience target is a Plugin Directory-listed Ninai integration:
choose Ninai, click **Connect**, complete Ninai OAuth, and use the hosted memory tools.
This is the hosted PostgreSQL product; it does not connect to the local macOS
SQLite vault.

## Technical endpoint

- App name: **Ninai**
- MCP server: `https://ninai-cloud.onrender.com/mcp`
- Authentication: OAuth 2.1 authorization-code flow with PKCE through Auth0
- Protected-resource discovery:
  `https://ninai-cloud.onrender.com/.well-known/oauth-protected-resource`
- Dashboard: `https://ninai-cloud.onrender.com/control`
- Website: `https://ninai.io`
- Privacy policy: `https://ninai.io/privacy/`
- Support: `hello@ninai.io`

The server exposes bounded search, fetch, recall, review-first proposal, and
explicitly granted remember tools. Every returned memory retains its source, and
all reads are disclosure-logged. Connecting an OAuth client must never silently
grant it a workspace or project scope.

## Submission inventory

Ready:

- production HTTPS Streamable HTTP MCP endpoint;
- OAuth authorization-code flow with PKCE, protected-resource discovery, and
  refresh-token support;
- successful external ChatGPT tool scan, OAuth, and read-tool invocation;
- tool titles, narrow descriptions, structured outputs, and safety annotations;
- public website, privacy URL, support address, and brand assets.

Still required before submission:

- a final public terms-of-service URL (the privacy architecture page is not a
  substitute for contractual terms);
- a reviewer account/workspace containing synthetic sample memories and
  least-privilege grants;
- recorded tests for search, fetch, recall, proposal, approval, revocation, and
  reconnect/refresh-token behavior—not only the successful empty search;
- final listing copy, category, icon/logo files, screenshots, example prompts,
  reviewer instructions, supported countries/plans, and a support runbook;
- OpenAI Platform organization ownership or an assigned role with **Apps
  Management: Write**, plus verified individual/business identity;
- five positive and three negative test cases with expected behavior;
- domain-verification access for the MCP host and a portal-generated token at
  `/.well-known/openai-apps-challenge` during submission;
- acceptance of the terms and policy attestations shown at submission time;
- production reliability, incident, deletion, retention, and backup evidence
  required by Ninai's own hosted launch gate.

## Public release gate

1. Keep the verified developer-mode app installed as a private acceptance target.
2. Bind each resulting OAuth client connection in the Ninai dashboard and grant
   only the acceptance-test project.
3. Record search, fetch, recall, propose, approval, revocation, and disclosure
   evidence against the production endpoint.
4. Verify the app name, logo, description, privacy policy, support contact,
   screenshots, test prompts, and reviewer instructions.
5. Submit using OpenAI's current public app/plugin submission flow and respond
   to review. A public one-click Plugin Directory listing exists only after
   external acceptance; repository deployment alone cannot publish it.

OpenAI documents developer mode as the private build/test path. Workspace admins
control private publication, actions, and access; public discovery is a separate
review path. Treat plan, regional, workspace-policy, and review requirements as
platform dependencies, not capabilities Ninai can bypass.

## Official references

- OpenAI, *Apps in ChatGPT* (including the 9 July 2026 Plugin Directory change):
  https://help.openai.com/en/articles/11487775-apps-in-chatgpt
- OpenAI, *Submit plugins* (authoritative portal fields and review process):
  https://developers.openai.com/plugins/deploy/submission
- OpenAI, *Plugin guidelines*:
  https://developers.openai.com/plugins/app-guidelines
- OpenAI, *Developer mode and MCP apps in ChatGPT*:
  https://help.openai.com/en/articles/12584461
- OpenAI, *Build with the Apps SDK*:
  https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk
