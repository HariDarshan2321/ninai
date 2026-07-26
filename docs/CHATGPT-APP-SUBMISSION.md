# ChatGPT app submission

The customer experience target is a directory-listed Ninai app: choose Ninai in
ChatGPT, click **Connect**, complete Ninai OAuth, and use the hosted memory tools.
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

## Directory release gate

1. Complete the external ChatGPT tool scan and OAuth flow in a supported
   Business, Enterprise, or Edu workspace using developer mode.
2. Bind the resulting OAuth client connection in the Ninai dashboard and grant
   only the acceptance-test project.
3. Record search, fetch, recall, propose, approval, revocation, and disclosure
   evidence against the production endpoint.
4. Verify the app name, logo, description, privacy policy, support contact,
   screenshots, test prompts, and reviewer instructions.
5. Submit the app from the OpenAI developer/workspace account and respond to the
   platform review. A public one-click directory listing exists only after that
   external review is accepted; repository deployment alone cannot publish it.

OpenAI currently documents custom MCP apps and full write support as a beta for
managed ChatGPT workspaces. Workspace admins control developer mode, publishing,
available actions, and user access. Treat those plan and review requirements as
platform dependencies, not capabilities Ninai can bypass.
