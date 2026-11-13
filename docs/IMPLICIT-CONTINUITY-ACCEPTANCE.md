# Natural-prompt continuity acceptance

A working connection is not sufficient acceptance evidence. A user should not
have to name Ninai, a tool, or a memory operation to continue prior work.

## Required behaviors

- Prior private decisions and commitments: retrieve permitted memory before
  answering or using public web search as a substitute for earlier context.
- Browse memories: use bounded `recall` with an empty query, not a literal search
  for words such as “some memories”. Keep purpose, provenance, live permissions,
  token limits, and disclosure auditing.
- Durable outcomes: save a compact decision with provenance only under the
  connection's existing grant. Activate only with `can_auto_activate`; otherwise
  propose for review. Proposals are not available for subsequent recall.
- Fresh continuation: another session must actually retrieve the new active
  memory. A model saying “saved” is not evidence.
- Negative control: ordinary general-knowledge questions need no memory call.
- Revocation: browsing must obey live read grants and revoked clients must fail.

## Repeatable cloud-only host test

With a disposable localhost hosted stack running, use the cloud environment's
Python interpreter:

```sh
cloud/.venv/bin/python scripts/test_implicit_cloud_host.py \
  --database-url "$NINAI_SYNTHETIC_DATABASE_URL" \
  --endpoint http://127.0.0.1:58046/mcp
```

This is opt-in and consumes existing Codex CLI model usage. The runner validates
localhost destinations, bootstraps a synthetic Atlas workspace, and creates one
fresh ephemeral Codex process per natural prompt. It ignores user configuration
and rules, disables apps and hooks, and configures only the synthetic HTTP server.
By default it does not install a continuity skill. The optional
`--with-continuity-skill` flag installs the bundled repository skill with the real offline installer into the temporary
workspace's `.agents/skills` directory to test implicit skill discovery; it does
not name the skill in user prompts. Neither mode reads the user's local vault,
inspects credentials, or modifies global configuration. The temporary server alone is
preapproved for tool calls. Synthetic credentials are passed through an environment
variable and redacted from retained host output. Database fixture cleanup runs in
`finally`, including host failures. Evidence lives in a private temporary directory.

Success is checked against actual database memory IDs and disclosure records,
not a model's claim. This test establishes neither browser OAuth behavior nor
registered desktop-connector metadata refresh, other assistants, or universal
automatic capture. Natural language behavior is probabilistic; one passing run
is a regression example, not a reliability percentage.

## Observations — 12 November 2026

A projectless Codex desktop chat asked “What do we know about our savings-plan
commitments from earlier work?” without naming Ninai. It selected the **local**
Ninai connection (`list_projects`, then `recall`) and made no web call. This does
not verify cloud routing when both modes are available.

The cloud connector tool metadata exposed to that chat had five tools, generic
recall/search descriptions, and no project-selection tool or `project_id` recall
parameter. Repository code exposes ten tools and project-aware descriptions.
This is a metadata mismatch; deployed service version versus connector caching
has not been established. Do not assume a repository change refreshes an existing
registered connector.

The isolated HTTP baseline at commit `861fe40` retrieved an earlier commitment,
activated a durable Thursday-review decision, and avoided memory for a geography
question. Browsing failed: the host searched for “some memories”, got no match,
and incorrectly stated the project had no active memories. Hosted recall also
rejected an empty query, unlike the local tool.

A second URL-only run after the browsing fix passed prior-work recall, browsing,
and the general-knowledge negative control. Durable activation and fresh
continuation failed: a review proposal left the old active decision available.
After grant-routing instructions were strengthened, another run still omitted
write tools entirely for both decision prompts. These are failed behavioral gates,
not transport failures. Tool metadata alone is insufficient evidence of reliable
automatic saving.

With the repository continuity skill installed only in the isolated workspace,
all six natural-prompt cases passed: prior-work recall, browsing, automatic active
save under an existing grant, fresh-session retrieval of the updated decision,
review-only proposal after auto-activation was removed, and no memory call for a
general-knowledge question. Host output confirms implicit skill selection and
reading of the installed skill; prompts did not name Ninai or the skill. Synthetic
workspace cleanup completed. Evidence:
`/var/folders/6x/8p3927h171s5rzgrvtrtcw340000gn/T/ninai-implicit-cloud-oqylf2jl`.

This is one controlled Codex CLI run, not proof of desktop plugin installation,
browser OAuth, other hosts, or a statistical reliability rate. Cloud setup now explains the explicit `ninai integration-skill install --client codex`
command for installed Ninai users. A URL alone still does not install it. The
cloud-only novice distribution gap and registered-connector metadata mismatch
remain launch gates for the automatic-continuity promise. Changes in this report were tested locally and have
not been deployed as part of this check.

Regression checks for this change: 121 cloud tests passed against disposable
PostgreSQL with zero skips; 94 engine tests passed; the continuity skill passed
its structural validator. These tests do not override the failed host gate.

## Activation and host boundaries

Server instructions and tool descriptions help selection; an installed continuity
skill adds a workflow. Adding an HTTP URL does not install that skill. Lifecycle
hooks are separate and host-specific. Existing local Claude Code/Codex session
capture does not provide cloud capture or Gemini capture. No change here uploads
local archives or observes conversations in unsupported hosts.

OpenAI documents [skill discovery](https://developers.openai.com/plugins/concepts/skills)
and [MCP server instructions](https://developers.openai.com/plugins/build/mcp-server).
Mem0's published [Claude Code integration](https://docs.mem0.ai/integrations/claude-code)
uses lifecycle hooks plus a background worker for capture and prompt injection;
its documented automatic first-prompt search has conditions. This is evidence for
host integration work, not proof that an MCP connection alone delivers automatic
memory in every client.
