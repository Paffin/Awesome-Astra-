# Project-wide integration

Use for changed contracts, shared behavior, or new functionality. Scale the work
to the affected surface; a spelling correction does not need an impact ledger.

## Establish the affected surface

For Python projects, run the bundled `scripts/project_map.py --root /repo
--source-root src --changed src/pkg/core.py` (on one shell line) using the
actual import roots. Omit `--source-root` for repository-root imports.
It reuses AST facts by content hash and returns transitive import candidates,
snapshot identity and coverage gaps. It does not execute project code.
Use compiler/LSP references to resolve bindings; syntactic edges are not proof.

1. Identify the existing owner and canonical implementation before adding another
   helper, service, endpoint, setting, or data model. Extend the established path.
2. Trace backward from the changed contract to callers and forward to observable
   behavior. Search identifiers AND wire names: route, event/topic, config key,
   serialized field, database column, registry name and command name as relevant.
3. Use language-server references or compiler tools when available, plus exact
   repository searches for string-based registration and cross-language clients.
   Follow aliases, re-exports, factories, dependency injection and dynamic loading.
   Ranked search results are navigation hints, never an exhaustive consumer list.
4. Keep a compact impact ledger for cross-boundary work: contract, producer,
   consumers, disposition (changed / compatible / not applicable / unresolved),
   and evidence. Include tests, fixtures, generated clients and deployment config
   only where the changed behavior reaches them. Do not invent dependencies.

## Make one coherent change

- Connect new behavior to the actual entry point: route registration, CLI dispatch,
  worker subscription, provider binding, feature flag, or UI action as applicable.
- Preserve one source of truth. Update schemas and regenerate derived code using
  the project's generator; do not repair generated output alone.
- Propagate types, validation, defaults, error semantics, permissions and tenant
  boundaries consistently. Check alternate paths such as batch jobs and exports.
- For persisted/wire contracts, handle old data and mixed-version readers/writers.
  Identify rollout and rollback order. External consumers outside this checkout
  remain an explicit compatibility boundary, not an assumed successful migration.
- Do not expand scope into unrelated cleanup. Preserve intentional adapters and
  compatibility shims; remove only obsolete paths made obsolete by this change.

## Close the integration loop

Refresh the map after edits. For multi-boundary work, use the repository's
`tools/check_integration.py` with the fresh impact report and reviewed ledger
(format documented in EVALUATION.md). Standalone installations can follow the
same evidence checks manually; never assume repository tools are installed.

Run an acceptance check through the real entry point and across affected boundaries,
not only the new helper in isolation. Exercise relevant invalid-input, permission,
and compatibility cases. Use type/build checks to catch missed static consumers;
test behavior that mocks cannot establish at a real integration boundary.

Search again for old names, parallel implementations, stale fixtures and orphaned
registrations. Inspect the final diff against the impact ledger. Resolve each
known affected consumer or explain why its contract remains compatible.

If a service, consumer or required environment is unavailable, report that precise
gap. Do not claim whole-project consistency or full integration from unit tests,
an empty search, a successful process exit, or a worker's summary alone.
