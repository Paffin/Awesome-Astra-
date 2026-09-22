# Implement or refactor

## Scope

Classify the change before reading broadly:

- **Local:** one behavior or isolated symbol. Inspect the target, direct callers, and nearest tests.
- **Cross-cutting:** shared contract, schema, public API, persistence, auth, concurrency, or deployment behavior. Trace every affected boundary.
- **Generated or vendored:** locate the source of truth; do not hand-edit generated output unless the repository requires it.

## Workflow

1. Check the working tree and preserve unrelated changes.
2. Localize hierarchically from task clues to files, symbols, callers, and tests. Use new evidence to refine the next search instead of loading the repository up front.
3. Define observable acceptance criteria and unchanged invariants from the user request.
   Choose affected risk scenarios using the acceptance reference; establish a
   reproducer for a reported failure before editing. Preserve project-native tests.
4. Patch the narrowest stable layer. Follow existing patterns before adding a new abstraction or dependency.
5. Inspect the diff immediately for accidental scope, duplicated logic, debug output, and compatibility breaks.
6. Run the nearest meaningful check: focused test, type check, linter rule, build target, or direct reproduction.
7. Verify new functionality through its real entry point. For shared contracts,
   follow the integration reference linked from SKILL.md and close every known
   affected consumer; a passing helper test is not completion evidence.

Add or change a test when it protects a behavioral contract or prevents a plausible regression. Avoid tests that merely mirror a reversible implementation detail.
