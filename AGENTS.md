# Instructions for coding agents

Read `docs/ARCHITECTURE.md` before making architectural changes.

## Product invariants

1. Ninai's implemented local mode is local-first: keep its vault on the user's machine and do not add cloud persistence to that mode. A hosted cloud mode may be developed separately, but it must be explicitly enabled and must never upload or sync local data automatically.
2. Never return memories outside the configured client scopes.
3. Never silently grant a client access to a new scope.
4. Preserve provenance (`source_uri`) for every stored memory.
5. Do not store credentials, private keys, bearer tokens, or obvious API keys.
6. Context packets must respect the requested token budget.
7. Raw tool output is not durable memory. Capture only compact outcomes, decisions, commitments, and state changes.
8. The website must remain accessible, fast, dependency-light, and truthful about current MVP boundaries.
9. Local and any future hosted mode must enforce the same permission, provenance, and disclosure-audit invariants.

## Engineering rules

- Python 3.11+.
- Prefer the standard library in the engine. The MCP SDK is the only required runtime dependency.
- Add or update tests for every engine behavior change.
- Run `python -m unittest discover -s tests -v` from `engine/`.
- Keep database migrations backward compatible during the MVP.
- Do not rename public MCP tools without updating docs and examples.
- Do not claim production-grade encryption, security certification, or universal automatic capture.

## Website rules

- Every indexable page needs a canonical URL, unique title, description, Open Graph fields, and one H1.
- Keep `robots.txt`, `sitemap.xml`, structured data, and visible page claims aligned.
- Do not add fake customer logos, fabricated metrics, fake reviews, or unsupported competitor claims.
