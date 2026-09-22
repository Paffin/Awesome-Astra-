# Testing strategy

Load when behavior changes, a regression must be locked down, or the affected contract is
high risk. Follow the project's native test stack; do not add a framework merely to satisfy
this reference.

## Choose the cheapest discriminating test

- For a bug, make the observed failure reproducible before the fix when safe.
- For new behavior, prefer a narrow red-green-refactor loop when a stable public seam exists.
- Test observable contracts and invariants, not private implementation choreography.
- Keep one vertical slice working through the real entrypoint before multiplying unit cases.
- Do not require a new test for a typo or other change whose nearest existing check proves it.

## Increase test strength only when risk warrants it

Use property-based testing for broad invariants, parsers, serializers, state machines, money,
ranges, or transformations where examples leave a large input space. Use mutation testing or
a deliberately broken disposable variant when confidence depends on proving that the suite
would catch plausible defects. Neither technique is a mandatory ceremony.

For migrations, retries, concurrency, security, and external contracts, load the dedicated
references from SKILL.md and exercise the real boundary where practical. Mocks can isolate a
unit but cannot establish database isolation, browser behavior, network compatibility, or
deployment wiring.

## Evidence

Run the original reproduction first, then focused checks, then broader type/build/integration
checks only when the changed surface justifies them. A passing test is evidence only for what
its assertions and environment actually cover. Record unavailable platforms or dependencies
instead of upgrading a proxy test into a stronger claim.
