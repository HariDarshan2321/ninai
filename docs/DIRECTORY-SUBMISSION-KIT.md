# Ninai directory submission kit

Use this kit for OpenAI app review and Anthropic's connector directory. Do not mark a manual gate complete without its evidence.

## Listing copy

**Name:** Ninai

**Tagline:** Permissioned, source-backed memory shared across AI tools.

**Category:** Developer tools / productivity

**Website:** https://ninai.io/

**MCP endpoint:** https://app.ninai.io/mcp

**Privacy:** https://ninai.io/privacy/

**Terms:** https://ninai.io/terms/

**Support:** hello@ninai.io

**Short description:** Remember a project decision once and recall it in Claude, ChatGPT, or another authorized MCP client—with sources, explicit project grants, review-first writes, and immediate revocation.

**Long description:** Ninai is a permissioned memory layer for AI work. A workspace owner creates project boundaries, connects an OAuth client, and grants only the read or propose capabilities that client needs. New clients start with no memory access. Memories retain source references; higher-risk writes remain proposed until reviewed. Local mode keeps a separate SQLite vault on a Mac and never automatically syncs it to the hosted workspace.

Suggested prompts:

- “Search Ninai for Project Atlas database migration decisions and include the source.”
- “What rule applies to test fixtures in Project Atlas?”
- “Propose a memory that Project Atlas release notes must include rollback instructions.”

## Reviewer account and workspace

1. Create a controlled mailbox such as `reviewer@ninai.io`. Never put its password in source, issue trackers, or submission copy.
2. Sign up at `https://app.ninai.io/control/login?screen_hint=signup` and finish email verification.
3. From a protected Render shell with `DATABASE_URL` set, run `ninai-cloud-reviewer-seed --email reviewer@ninai.io`.
4. Connect the reviewer's OpenAI or Anthropic client. The OAuth connection begins with zero grants.
5. In the Ninai control center, grant the generated **Project Atlas** project `read` and `propose`; leave auto-activate off.
6. Give credentials to the assigned reviewer only through the directory's protected reviewer-credential field.

The seed command is idempotent, refuses to take over another account's review workspace, and inserts only synthetic memories.

## Screenshot set

Capture at 1440×900 or the directory's required size:

1. Homepage: headline and “Get started” action.
2. Hosted onboarding: create account, connect AI, grant project.
3. Control center: Project Atlas, connection, and explicit grant (hide email and IDs).
4. Memory review: a proposed synthetic memory with approve/reject actions.
5. Recall result: content plus `reviewer://atlas/...` source.
6. Privacy page: hosted-data and permission sections.

Do not show tokens, authorization codes, database URLs, personal email addresses, or real customer content.

Prepared public-page assets are in `docs/submission-assets/`: homepage, hosted onboarding,
privacy policy, terms, and mobile onboarding. Dashboard, review-queue, and sourced-recall
screenshots remain pending until the dedicated reviewer account is created and connected.

## Acceptance evidence

| Test | Expected result | Current evidence |
| --- | --- | --- |
| OAuth sign-in and dynamic client registration | Account signs in; client exists with zero grants | Automated OAuth/binding tests pass; manual directory-review capture pending |
| Recall Project Atlas migration decision | Exact synthetic decision and source returned | Pending dedicated reviewer connection |
| Recall test-fixture constraint | Synthetic-data/no-credentials constraint and source returned | Pending dedicated reviewer connection |
| Propose a new memory | Proposal appears in review queue, not active recall | Automated write-policy tests pass; manual capture pending |
| Approve proposal, then recall | Approved content and source returned | Pending reviewer execution |
| No grant | No Project Atlas memory is disclosed | Automated tenant/grant tests pass; manual capture pending |
| Revoked connection | Existing client is denied on its next request | Automated revocation tests pass; manual capture pending |
| Cross-tenant ID supplied | Request remains denied; client cannot select another tenant | Automated tenant-isolation tests pass |

External reviewer sign-off remains **PENDING** until a reviewer performs the manual cases and records timestamped, redacted screenshots or logs. A developer self-test is not independent acceptance.
