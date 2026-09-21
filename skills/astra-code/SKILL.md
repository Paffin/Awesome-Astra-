---
name: astra-code
description: Implement, fix, refactor, or review code with GPT-6 Astra using a minimal-context, verification-first workflow.
---

# Astra Code

## Route once

Choose one route and read only its reference:

- Failing behavior, error, regression, or flaky test: [debug](references/debug.md)
- PR, branch, patch, or code-quality review: [review](references/review.md)
- Architecture choice or large ambiguous change: [design](references/design.md)
- Any other implementation or refactor: [implement](references/implement.md)

Read another route only if the task genuinely changes.

## Operating contract

1. Infer the requested outcome, constraints, and evidence of completion from the prompt and repository. Ask only when a material choice cannot be inferred safely.
2. Read applicable repository instructions, then build the smallest useful working set: entry point, affected symbols, direct dependencies, and nearest tests or configuration.
3. Make the smallest coherent change that fully solves the task. Preserve user changes and avoid unrelated cleanup, dependency churn, or speculative abstractions.
4. Continue through inspection, implementation, verification, and cleanup. Stop only when the requested outcome is demonstrated or a concrete blocker requires the user.
5. Verify in proportion to risk. Start with the narrowest meaningful check; broaden only when failures, shared interfaces, or high-impact behavior justify it. Treat passing tests as evidence, not a substitute for checking the requested behavior and final diff.

## Context discipline

- Prefer targeted search and bounded reads over repository-wide loading. Use `rg` or `rg --files` when available.
- Let each observation refine the next search; stop retrieving when the relevant execution path and contract are explained.
- Batch independent read-only operations. Reuse collected facts; do not reread unchanged content.
- Bound noisy command output and inspect the relevant slice first.
- Do not create plans, summaries, or progress narration unless they help execution or the user requests them.
- Delegate only independent, non-overlapping work when the expected wall-clock gain exceeds the added coordination and context cost.

## Handoff

Lead with the outcome. State changed behavior, meaningful verification, and any residual risk or blocker. Omit the work diary.
