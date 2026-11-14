# Durable capture correction — 14 November 2026

A synthetic reproduction confirmed that the current Claude PostToolUse capture
policy could store a JSON error as durable memory when the tool response was a
string containing a word such as `status`. Structured failures could also become
`status=error` memories, and query rows containing familiar field names could be
mistaken for durable outcomes. This was a current code path, not evidence that
all existing records came from an older release.

The hook now accepts structured results or bounded JSON/MCP result envelopes,
rejects explicit failure flags and error states (including JSON inside MCP text
or result/data wrappers), and no longer promotes raw prose through a keyword
match. Query/SQL tools are excluded from automatic durable capture. Row arrays
and arbitrary nested debug objects are source material, not selected outcomes.
Generic identifiers or a generic success status alone are insufficient.
Successful compact decisions, commitments, named state changes and useful write
outcomes still retain their original project boundary, provenance and secret
filtering. These conservative rules can skip ambiguous outcomes; an agent can
explicitly submit a durable decision through the normal memory tools instead.

Session archiving is unchanged and remains separate from durable memory.
Existing captured records are preserved. No automatic removal, hiding,
reclassification or historical-vault migration was performed. Any cleanup of
previously captured noise needs a separate owner-reviewed workflow.

Regression coverage includes raw text and JSON errors, structured and MCP/text
failures, nested JSON error wrappers, query rows, generic id/status responses,
compact successful JSON decisions, and rejection before project/memory creation.
