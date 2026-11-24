# Fictional refund idempotency rule

This fixture is for the Ninai Team approval and recall walkthrough.

## Decision

Persist the refund idempotency key before calling the payment provider.

## Rationale

A retry must reuse the same key after an ambiguous provider response.
