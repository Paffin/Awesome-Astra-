# Design a change

Use this route only when implementation depends on a consequential decision.

## Decision pass

1. Define the outcome, invariants, scale, compatibility, operational constraints, and failure tolerance.
2. Inspect only the repository boundaries that constrain the decision: existing interfaces, data model, deployment shape, and extension points.
3. Prefer the simplest design that satisfies current evidence. Separate required extensibility from imagined future needs.
4. Compare at most three viable options on correctness, migration cost, operability, reversibility, and implementation effort.
5. Choose one option and record rejected alternatives only when the tradeoff is non-obvious.

## Continue to delivery

If the user asked for implementation, treat the decision as an internal checkpoint and continue with the change. Do not stop after producing a plan unless a material product choice or irreversible migration requires confirmation.

Validate the design through a thin end-to-end path or contract test before expanding it.
