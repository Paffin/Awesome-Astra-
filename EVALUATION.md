# Evaluation and evidence

## 0.6.0 evidence boundary

This release implements executable paired evaluations, source-bound command
receipts and persistent impact context. Deterministic tests exercise the real
subprocess/filesystem paths with explicitly synthetic executors. They are not
Astra task-success, latency or token-saving measurements.

The live Codex adapter was attempted in the development environment and stopped
with `Codex CLI not installed; no model run performed`. Live model evaluation
remains unexecuted. No synthetic result is substituted for this missing evidence.

For execution commands and limitations see [VERIFIED_WORKFLOW.md](docs/VERIFIED_WORKFLOW.md).
`evals/executable.json` contains runnable fixtures with external graders.
The older `evals/*.jsonl` files are behavioral/routing specifications, not measured
passes. Installed-package and protocol tests do not prove host skill activation.

## Model experiment controls

Fix model, reasoning effort, host/version/configuration, repository/skill revision,
task, tools/permissions, time budget and cache conditions. Use fresh sessions and
isolated evaluation environments with no global copy of the candidate skill.
Alternate variant order; repeat noisy tasks and retain failures/retries. Keep
held-out evaluation criteria outside the implementation workspace and independently
inspect outcome and scope. The local runner checks grader hashes; that does not
sandbox hostile code with filesystem access to the evaluator.

`tools/run_evals.py` saves provenance and per-run output directories, JSONL outcomes,
final workspace copies and an aggregate summary. `accepted` covers the fixture's
assertions only. The runner does not independently grade safety or model reasoning,
and reports missing usage as null. Inspect traces for implicit skill activation;
use the Codex adapter's explicit invocation mode as a distinct experiment.

## Recorded integration checks

The legacy ledger mode checks completeness. `--root /repo --require-recorded`
also verifies current impact inventory and every supplied command receipt.
Generate the fresh impact report after editing, outside the target tree.
A minimal ledger shape is:

```json
{
  "snapshot_sha256": "COPY_FROM_FRESH_REPORT",
  "consumers": {
    "path.py": {"disposition": "changed", "evidence": "diff and acceptance reference"}
  },
  "checks": [
    {"kind": "entrypoint", "passed": true, "evidence": "command exercises real route",
     "receipt": "/evidence/entrypoint.json"}
  ],
  "coverage_review": {
    "unresolved_imports": {"resolved": true, "evidence": "external dependency reviewed"}
  }
}
```

Every affected candidate needs `changed`, `compatible` or `not-applicable` plus
specific evidence. Every nonempty gap category needs review, including stale
contract declarations. A receipt does not authenticate its writer or prove that
the recorded test is sufficient. Covered source edits invalidate it; ignored,
secret, binary, oversized and unreadable files and external state are not covered.
Never mark an inaccessible consumer resolved without compatibility evidence.

## Paired telemetry comparator

`python3 tools/compare_runs.py measured-runs.jsonl` compares separately collected
actual telemetry. Runner output with null usage is deliberately not valid input.
Required fields per line:

| Field | Meaning |
| --- | --- |
| `run_id` | Unique actual run identifier. |
| `task_id`, `repeat` | Pair identity and nonnegative repetition number. |
| `variant` | `baseline` or `candidate`. |
| `setup` | Exactly `model`, `harness`, `repo_revision`, `environment`, `reasoning_effort`, `cache_state`; nonempty strings identifying versions, policy and budget. |
| `input_tokens` | Actual total input usage, including cached subset, across retries. |
| `cached_input_tokens` | Reported cached subset; never added again. |
| `output_tokens` | Actual output usage. |
| `elapsed_seconds` | Positive finite end-to-end duration. |
| `accepted`, `safety_passed` | Explicit independently evaluated booleans. |
| `evidence` | Retained traces, logs and grader evidence. |

The comparator rejects unpaired runs, mismatched setups, duplicate IDs and invalid
usage. Total is input + output, not a monetary cost. Exit 0 requires at least one
accepted-safe candidate, no candidate safety failures and no pair regressing from
an accepted-safe baseline. Exit 1 is observed regression, 2 invalid data. This is
not a statistical noninferiority test. Report uncertainty and heterogeneous setups.

## Earlier live language-server evidence

On 2026-09-22 two-file fixtures passed with jedi-language-server 0.47.0 and
typescript-language-server 4.3.3 + TypeScript 5.7.3. TypeScript initially returned
only the definition until its consumer document was explicitly opened. These
results do not establish complete indexing or compatibility with other servers.
Reproduce using `tools/live_lsp_check.py --language python|typescript --server`
with a separately installed explicit JSON server argv. No automatic installation.

## Release gate

Run structural validation and deterministic tests; inspect integration behavior.
Before any model-performance claim, additionally run paired held-out tasks,
independent assessment, repeated measurements and publish reproducible redacted
artifacts including failures. Never manufacture missing telemetry or outcomes.
