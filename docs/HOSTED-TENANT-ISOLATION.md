# Hosted tenant isolation

Ninai Cloud uses one PostgreSQL database with logical tenant isolation. It does
not create a database or schema per customer. Every durable customer record is
owned by a UUID `workspace_id`, and every externally reachable data operation
derives that workspace from authenticated server-side state rather than request
JSON, query parameters, or tool arguments.

## Authentication and client binding

1. Auth0 signs the access token. Ninai verifies its signature, issuer, audience,
   expiry, and MCP resource.
2. The issuer subject maps to one internal UUID user; accounts are never linked
   by email.
3. The OAuth client ID maps to a `client_connections` row for that user and
   workspace. Membership, workspace, user, binding, and connection revocation
   are checked on every MCP request.
4. A standards-based dynamically registered client may be auto-bound only when
   the user has exactly one active workspace (or a signed workspace claim picks
   one). The new connection receives **no memory grants**.
5. An owner/admin explicitly grants read, propose, or auto-activate capability
   for a workspace, project, or user scope. Grants can expire or be revoked.

The database also enforces that an OAuth binding and its connection have the
same workspace and owner. A client ID cannot be rebound across users or tenants
through malformed administrative data.

## Storage and query isolation

- Projects, connections, grants, memories, sources, disclosure logs, feedback,
  relations, and idempotency records carry `workspace_id`.
- Composite foreign keys keep child records in the same workspace as their
  parent connection, project, or memory.
- Memory reads join the requesting connection's live, unexpired read grant in
  the same SQL statement that retrieves memories. Unauthorized rows do not
  enter ranking or response composition.
- Writes first validate the live principal, then verify that the polymorphic
  scope belongs to that authenticated workspace, then require the matching
  propose or auto-activate grant. Project-scoped records always store a
  `project_id` equal to their project `scope_id`.
- Idempotency keys are namespaced by workspace and client connection.
- Control-center operations derive identity from the verified access token and
  scope all SQL by that workspace. Owner/admin checks protect grants, reviews,
  exports, revocation, and deletion.

## Customer-visible behavior

Each cloud customer signs in, creates a workspace and project, connects Claude
or ChatGPT with OAuth, and grants that connection only the desired scopes. Their
memories share infrastructure with other customers but are not queryable by
those customers. Revoking a grant removes that scope immediately; revoking the
connection or membership invalidates subsequent requests.

## Limits and operations

This is application-enforced logical isolation, not a separate database per
customer and not PostgreSQL Row-Level Security. Database administrators and the
production service role are trusted. Production must use a non-public database,
TLS, least-privilege credentials, encrypted provider storage, monitored backups,
and tested restoration. Repository tests are regression evidence, not an
independent security audit or certification.
