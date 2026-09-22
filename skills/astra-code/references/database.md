# Database and Postgres changes

Load for schema, SQL, indexes, migrations, RLS/tenant rules, connection behavior, or database
performance. Use the repository's migration and database tooling.

## Schema and query contract

- Model constraints in the database when they are durable domain invariants; keep application
  validation aligned rather than contradictory.
- Inspect real query shapes before adding indexes. For performance work, use EXPLAIN/ANALYZE or
  the project's equivalent in a safe representative environment and compare the same workload.
- Check cardinality, selectivity, pagination, N+1 behavior, lock scope, transaction boundaries,
  isolation assumptions, connection-pool pressure, and long transactions where relevant.
- For tenant/RLS changes, test visible and denied rows with representative roles. Application
  filtering is not a substitute for an intended database policy.

## Migration safety

Load data-failures.md for existing data or mixed versions. Prefer expand/migrate/contract when
rolling versions overlap. Verify defaults, nullability, backfills, indexes/constraints, reruns,
lock duration, and recovery using representative sanitized data.

Do not edit generated schema artifacts instead of their source of truth. Do not run destructive
DDL or production maintenance without the repository's normal authorization. A migration that
passes on an empty database is not sufficient evidence for existing data.
