# Evaluation protocol

Use paired runs to compare skill revisions. Script tests, instruction byte counts, and subjective impressions do not measure model success.

## Controls and evidence

Keep the model, reasoning effort, repository revision, prompt, tools/permissions, environment, time/retry budget, and cache conditions equivalent within each pair. Use clean isolated worktrees and fresh sessions. Alternate/randomize variant order; repeat noisy tasks and retain failures, retries, prompts, traces, diffs, command logs, and independent grader output.

Measure requested behavior, process/scope, correctness/security/maintainability, and efficiency. Passing tests are one signal; inspect the requested behavior and final diff. Do not let the candidate edit its evaluator or held-out cases. Attribute results to the exact model/harness/settings, not all future releases.

`evals/cases.jsonl` and `evals/advanced.jsonl` contain 24 routing and behavioral specifications, including anti-triggers, secret exfiltration instructions, stale source, dirty worktrees, unavailable workers, and overly broad verification. Their presence does not mean Astra passed them.

## Paired telemetry comparator

```bash
python3 tools/compare_runs.py /path/to/measured-runs.jsonl
```

Each nonempty JSONL line must have:

| Field | Meaning |
| --- | --- |
| `run_id` | Unique actual run identifier. |
| `task_id`, `repeat` | Shared task identity and nonnegative repetition index for the pair. |
| `variant` | `baseline` or `candidate`. |
| `setup` | Object containing exactly `model`, `harness`, `repo_revision`, `environment`, `reasoning_effort`, `cache_state`; each is a nonempty string. Include the relevant versions and policy/budget identity. |
| `input_tokens` | Actual total input usage across all attempts, including its cached subset. |
| `cached_input_tokens` | Actual subset of input tokens reported as cached. |
| `output_tokens` | Actual output usage; do not add reasoning tokens again when the host includes them here. |
| `elapsed_seconds` | Positive finite end-to-end elapsed time. |
| `accepted`, `safety_passed` | Explicit independent evaluation booleans. |
| `evidence` | Location/identifier of retained traces, checks, and grader evidence. |

No fabricated example benchmark is included. Unit-test fixtures use explicitly synthetic data and must not be reported as model measurements. Collect one row per variant per task/repetition, summing retries within that row. Missing usage is unknown: do not substitute zero or byte estimates. Use a separate qualitative report when the host lacks telemetry.

The tool rejects missing partners, duplicate runs, incompatible pair setups, negative or non-finite values, and impossible cache counts. Total tokens are `input_tokens + output_tokens`; cached input is not counted twice. Token counts are not prices: actual cost also depends on provider rates, cache writes, service tier, and context thresholds.

Exit status is 0 only when the observed candidate has at least one accepted-safe result, no safety failures, and no pair that regresses from an accepted-safe baseline. Status 1 means the observed gate fails; status 2 means invalid data. This conservative gate is not a statistical noninferiority test. Reports flag heterogeneous setups and provide descriptive medians; inspect strata and distribution before generalizing.

## Release policy

Run deterministic validation and tests. Preserve safety constraints. For a **performance claim**, additionally run the behavior cases and real held-out repository tasks, with blind review where practical, repeated paired measurements, dispersion/uncertainty, and reproducible artifacts. Report actual evidence of regressions as well as wins.

This 0.2.0 revision is a tested tooling/workflow release without an end-to-end Astra performance claim. Live model evaluation remains an explicit next gate rather than a fabricated completed benchmark.
