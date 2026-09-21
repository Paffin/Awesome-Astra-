# Measured experiments

Use for explicitly requested performance work or skill evaluation, not routine edits.

1. Establish a baseline on a fixed repository revision, task, environment, model, reasoning effort, tool permissions, and time/tool budget. Preserve the user's work.
2. Choose one falsifiable change and an independent acceptance check. Keep the evaluator and held-out cases out of the optimization target.
3. Run baseline and candidate under comparable conditions; alternate their order over repetitions. Count failed attempts and retries, not just the successful final call.
4. Record actual usage separately: input tokens, cached-input subset, output tokens, elapsed time, accepted result, and safety outcome. Do not add cached tokens twice or invent missing telemetry. Token estimates are not usage measurements.
5. Keep a candidate only when required correctness and safety gates hold and its measured tradeoff is worthwhile. A lower token count caused by abandoning a task is a regression.
6. Stop at the agreed experiment budget or when new evidence no longer justifies another attempt. Keep an experiment log and report negative results. Do not change the acceptance check to manufacture a win.

For skills, test routing, non-routing, prompt injection, dirty worktrees, unavailable tools, cross-file contracts, and completion behavior. Unit tests for bundled scripts do not establish model quality.
For runtime optimizations, test realistic workloads and worst cases. For instruction changes, use paired held-out tasks and report dispersion, not a single cherry-picked run.
Do not disable approvals, mutate production, or auto-promote modified skills to achieve a benchmark score. The host controls model choice, tool concurrency, caching, and isolation; prose does not implement those capabilities.
