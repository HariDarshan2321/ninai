# Claude connector submission

## Live acceptance status

Validated on July 26, 2026 with Claude.ai. Claude completed Ninai OAuth, loaded
all five hosted MCP tools, invoked **Search Ninai memory**, and returned
`0 results` for the synthetic query `NINAI_CLAUDE_ACCEPTANCE_2026`. The connector
call completed successfully.

The target customer experience is an Anthropic-directory connector: choose
**Ninai**, click **Connect**, authenticate with Ninai OAuth, and enable its tools
for a conversation. Until directory approval, the same hosted connector can be
added manually as a custom remote MCP connector.

## Test the custom connector now

In Claude, open **Customize → Connectors → Add custom connector** and use:

- Name: **Ninai**
- Remote MCP URL: `https://ninai-cloud.onrender.com/mcp`

Claude connects from Anthropic's cloud and completes OAuth in the browser. The
connector uses Ninai's hosted PostgreSQL vault and cloud dashboard; it cannot
read the private SQLite vault in the macOS app.

## Directory submission data

- Website: `https://ninai.io`
- Dashboard: `https://ninai-cloud.onrender.com/control`
- Privacy: `https://ninai.io/privacy/`
- Terms: `https://ninai.io/terms/`
- Support: `hello@ninai.io`
- Authentication: OAuth 2.1 authorization-code flow with PKCE
- Tools: search, fetch, recall, propose_memory, remember

All tools publish titles and explicit MCP safety annotations. Search, fetch, and
recall are read-only. Proposal and memory activation are non-destructive write
operations and are marked accordingly. Idempotency keys prevent duplicate writes, permission
checks precede retrieval, provenance is preserved, and disclosures are logged.

## Policy readiness inventory

Ready:

- public HTTPS Streamable HTTP endpoint and secure OAuth;
- successful Claude.ai OAuth, five-tool scan, and read-tool invocation;
- tool names below 64 characters, narrow descriptions, titles, and applicable
  `readOnlyHint`, `destructiveHint`, and idempotency annotations;
- bounded outputs, structured errors, provenance, permission checks, and
  disclosure logging;
- public website, privacy URL, support and security addresses.

Prepared in the repository:

- public terms and hosted privacy details covering collection, use, retention,
  deletion, subprocessors, and the local/hosted boundary;
- an idempotent synthetic reviewer-workspace seeder plus reviewer instructions,
  listing copy, screenshot plan, and evidence matrix in
  [`DIRECTORY-SUBMISSION-KIT.md`](DIRECTORY-SUBMISSION-KIT.md).

Still required before submission:

- create a controlled reviewer mailbox/account, run the seeder, and supply its
  credentials only through Anthropic's protected review flow;
- record the pending positive and negative reviewer cases in the kit;
- public troubleshooting documentation and a support/incident runbook;
- production availability/latency, backup/restore, deletion, and refresh-token
  evidence;
- verified ownership/control of every connected endpoint and acceptance of the
  current MCP Directory Terms at submission time.

## Release gate

1. Add Ninai as a custom connector and complete a real Claude.ai OAuth test.
2. Use a dedicated reviewer account and workspace containing synthetic data.
3. Record at least three functional examples: scoped recall with a source,
   review-first proposal and approval, and denial after connection revocation.
4. Confirm the OAuth callback and refresh-token flow used by Claude.
5. Submit the remote server through Anthropic's MCP Directory review form with
   reviewer credentials, documentation, privacy policy, and support contact.

The public one-click listing exists only after Anthropic accepts the submission.
No repository or Render deployment can bypass that external review.

## Official references

- Anthropic, *Connectors Directory FAQ*:
  https://support.anthropic.com/en/articles/11596036-anthropic-mcp-directory-faq
- Anthropic, *MCP Directory Policy* (requirements 1–27):
  https://support.anthropic.com/en/articles/11697096-anthropic-mcp-directory-policy
- Anthropic, *MCP Directory Terms and Conditions*:
  https://support.anthropic.com/en/articles/11697081-anthropic-mcp-directory-terms-and-conditions
- Anthropic, *Getting Started with Custom Connectors Using Remote MCP*:
  https://support.anthropic.com/en/articles/11175166-about-custom-integrations-using-remote-mcp
