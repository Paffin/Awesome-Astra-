# Data changes and failure semantics

Load only for persistence, migrations, queues, asynchronous work or concurrency.
Use the project's existing tools; do not introduce a new framework for the checks.

## Persistent data and mixed versions

- Inspect actual schema, historical records, migration runner and deployment order.
  New empty databases do not represent production data.
- Define old-reader/new-writer and new-reader/old-writer compatibility where versions
  coexist. Include null/default values, legacy enum values, constraints and indexes.
- Exercise the migration on representative sanitized old data. Verify invariants,
  restart/re-run behavior and failed partial execution. Do not copy production secrets.
- Prefer expand/migrate/contract when mixed versions require it. Identify lock time,
  backfill resource limits and when old fields can be removed.
- Verify recovery of data as well as binaries. An irreversible migration needs an
  explicit tested restore/forward-repair path; never promise a nonexistent downgrade.
- Preserve deployment authorization. Run destructive checks only in disposable fixtures
  or an already authorized test environment; never run them against production by default.

## Repeated, concurrent and partially failed operations

- Identify atomicity boundaries, transaction isolation, uniqueness constraints and
  durable state. Define which effects may repeat and which must occur once.
- Exercise duplicate request/event IDs, concurrent delivery, cancellation, timeout
  and failure between durable steps. A retry counter alone is not idempotency.
- Use deterministic barriers or fault injection at the real boundary; avoid sleeps
  as the sole proof of a race. A lock in one process may not protect other workers.
- Verify bounded retries/backoff, dead-letter or recovery behavior, cancellation and
  release of resources. Distinguish transient from permanent validation errors.
- Check external side effects separately. A local transaction cannot atomically commit
  a remote call; use existing outbox/idempotency protocols where required.
- Record the public-path result and persisted effect count. A successful response with
  duplicated charges/jobs is a failed acceptance result.

## Strength of the checks

Show that the reproducer fails on the original defect or a deliberately broken
variant in a disposable copy. Do not mutate a live user's checkout merely to prove
red/green. Keep a legacy-data test plus the new contract test for a migration.
Use independent graders for model evaluations; code under evaluation cannot edit
its grader. If the required backend or version is unavailable, retain an unresolved
gap and state the boundary; a mock does not establish real transaction semantics.
