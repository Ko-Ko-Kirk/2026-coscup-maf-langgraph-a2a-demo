# Security policy and demo limitations

## Supported version

This repository is a conference-oriented reference implementation. Security
fixes apply to the latest commit on the default branch.

## Reporting

Do not open a public issue containing credentials, tenant identifiers, private
prompts, or production endpoint details. Contact the repository owner privately
before publishing a security report.

## Deliberate demo limitations

The local A2A servers:

- bind to `127.0.0.1` by default;
- do not add HTTP authentication or authorization;
- use in-memory task, session, and checkpoint stores;
- do not enforce tenant isolation;
- do not persist cancellation state across restart;
- do not provide production rate limiting.

Do not expose them directly to a public network.

The inventory scenario also calls an unauthenticated external demo endpoint.
Its quantity and echoed product are untrusted observations. The application
does not interpret them as catalog validation, authorization, or reservation.
Live failures may use a visibly labelled fixture fallback, but that path always
returns `manual_review`.

## Production requirements

Before deployment:

1. Put authenticated ingress in front of every A2A endpoint.
2. Authorize the caller for the target agent, task, context, and artifact.
3. Bind context/task identifiers to a trusted tenant; identifiers are not
   bearer credentials.
4. Validate Agent Cards and sanitize all remote messages and artifacts before
   including them in model input.
5. Replace in-memory stores with durable, encrypted, tenant-partitioned stores.
6. Add idempotency keys around every external side effect.
7. Propagate trace context without logging secrets or unnecessary prompt data.
8. Apply request limits, timeout budgets, retry policy, and circuit breaking.
9. Pin A2A and framework versions and run compatibility tests before upgrade.
10. Replace the demo inventory endpoint with an authenticated, authorized,
    idempotent inventory/reservation API before any production use.

Microsoft Entra credentials should come from Azure CLI for local development or
managed/workload identity in production. Never commit `.env` or API keys.
