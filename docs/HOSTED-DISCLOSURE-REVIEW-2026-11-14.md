# Hosted privacy and terms factual review

Prepared 14 November 2026. This is an implementation review, not a legal compliance assessment or a platform submission approval.

## Corrected product descriptions

The public Privacy Policy and Terms of Service said hosted storage and remote connections were unavailable. The repository implements an explicitly chosen hosted PostgreSQL workspace, separate from local SQLite. Draft page corrections now describe:

- Separate local and cloud storage, with no automatic local upload or synchronization.
- Hosted memory, sources, proposals, feedback, connection permissions, disclosure records, and optional session archives.
- Account/session cookies and the existing administrator account/download/hosted-usage dashboard.
- Auth0 authentication and Render-hosted cloud application/database, alongside the previously documented website/source providers.
- Local and cloud revocation, including the inability to recall content already sent to an AI provider.
- Workspace exports, soft deletion, session-content deletion, retained historical records and rotating backups.
- Retention settings requiring a service-side cleanup operation; no claim that changing a setting immediately purges old data.
- The absence of hosted end-to-end encryption, customer-trusted signed desktop packages, and independent security certification.

The existing agreement, warranty disclaimer, liability limit, prohibited-content rules, and contact address were preserved. The draft effective date is 14 November 2026; confirm the intended public effective date when publishing.

## Implementation evidence

- `cloud/README.md`: explicitly opt-in PostgreSQL backend; no import, inspection, or synchronization of the local SQLite store.
- `cloud/src/ninai_cloud/control_api.py`: `record_login`, administrator views, installer receipts, cookie-based login, workspace export, session deletion and workspace deletion.
- `cloud/src/ninai_cloud/postgres_store.py` and migrations: stored hosted content and permission-filtered retrieval with disclosure records, not end-to-end encrypted memory.
- `cloud/src/ninai_cloud/storage_admin.py`: session-retention cleanup is an explicit operator action.

## Owner decisions still needed

Do not invent the legal operator/controller identity, physical contact details, applicable legal bases, required jurisdiction-specific notices, or a regulated-data/compliance assurance. These require an owner-approved policy before platform publication. Also establish and document actual retention/purge periods for hosted memories, soft-deleted workspace records, account/security records, and operational logs; establish an account-erasure procedure and verify it against Auth0 and Ninai's database. A configured backup window alone does not establish a complete deletion policy.

Confirm the actual hosting/provider configuration before publication and keep this list aligned when it changes. No new pricing, availability guarantee, certifications, provider approval, or legal entity information is asserted in the corrections.

No public deployment or platform submission was performed by this review.
