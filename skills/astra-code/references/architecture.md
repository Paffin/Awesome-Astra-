# Architecture and domain coherence

Load for cross-module features, shared interfaces, domain changes, or refactors that can
create a second source of truth. Do not load it for isolated text or formatting edits.

## Put behavior where it belongs

1. Identify the domain owner, existing public boundary, and current execution path before
   creating a helper, service, model, endpoint, or abstraction.
2. Extend the canonical owner when possible. A new module must have a clear responsibility,
   hide meaningful complexity, and reduce coupling; a wrapper that mirrors its internals is
   usually a shallow abstraction.
3. Trace the feature vertically from entrypoint through domain logic, persistence/external
   effects, and observable output. Do not leave a functional appendix that works only when
   called directly.
4. Use one vocabulary for the same domain concept across types, schemas, APIs, events,
   persistence, UI copy, tests, and docs. Resolve synonyms that create duplicate concepts.
5. Preserve stable interfaces and invariants. When a contract must change, make compatibility,
   migration, and ownership explicit rather than scattering adapters without an end state.

## Decide proportionately

Prefer the smallest design that makes the whole change coherent. Reuse project patterns and
native capabilities before inventing frameworks. Record an ADR only for a consequential,
long-lived tradeoff whose rationale would otherwise be lost.

For uncertain architecture, prove the boundary with a thin end-to-end slice or contract test
before expanding it. When the repository is already inconsistent, do not "clean everything";
repair the path needed for the requested outcome and leave unrelated debt explicit.
