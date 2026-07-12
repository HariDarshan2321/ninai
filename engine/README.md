# Ninai engine

A focused local MCP memory service for the Ninai MVP.

## Design

Ninai separates domain rules, policy-aware persistence, retrieval, capture, and transport:

```text
Claude Code PostToolUse event
        -> hook_capture.py
        -> store.py (SQLite + scopes + logs)
        -> retrieval.py (PACT ranking + context budget)
        -> server.py (MCP stdio)
```

The permission query runs before retrieval. `retrieval.py` receives only rows in scopes already granted to the requesting client. The engine stores selected durable outcome fields rather than complete tool responses.

## MCP tools

- `remember` — stores a compact memory with provenance and a scope.
- `recall` — returns a permission-filtered compact context packet.
- `explain` — shows a memory and its provenance.
- `forget` — soft-deletes a memory.
- `status` — returns local vault statistics and granted scopes.

## CLI

```bash
ninai permission grant claude-code work
ninai permission list claude-code
ninai memories
ninai logs
ninai doctor
```

## Development

```bash
python -m pip install .
python -m unittest discover -s tests -v
```

The suite includes unit tests for permissions, provenance, secret rejection, type-aware decay, ranking and context budgets, plus an end-to-end test that starts the MCP stdio server and executes the Claude hook.

The client identity defaults to `claude-code` and can be changed with `NINAI_CLIENT_ID`.
The vault defaults to `~/.ninai/ninai.sqlite3` and can be changed with `NINAI_DATA_DIR`.
