# Scoped acceptance

Use for substantive behavior changes. A small local edit needs its focused check,
not an acceptance plan file or every risk category below.

## Define the result before editing

State observable outcomes through the public entrypoint, important unchanged
invariants and concrete examples. Derive these from the request and existing
contracts. Ask only when a material product decision cannot be inferred safely.
For a bug, reproduce the old failure before accepting the new behavior.

Choose only affected risks. Each criterion can carry its own `risks` so checks
cannot be satisfied by an unrelated feature. Do not hide a relevant risk to pass.

| Risk | Required scenario kinds |
| --- | --- |
| migration | compatibility, recovery |
| concurrency | concurrency, replay, failure |
| security | denied-path |
| external-contract | compatibility |
| performance | performance |
| user-journey | user-journey |
| recovery | recovery, failure |

Every plan also requires a real `entrypoint` check. Add `negative` when invalid
input or failure behavior matters. External inaccessible boundaries stay unresolved.
Kinds describe reviewed test intent; the tool cannot infer test semantics from a label.

## Bind criteria and checks

Write a JSON plan before checks. Minimal example:

```json
{"schema":1,"risks":[],"criteria":[
  {"id":"download","expected":"Owner downloads; other tenant is denied",
   "kinds":["entrypoint"],"risks":["security"]}
],"boundaries":[]}
```

Keep the plan in an eligible project file, or declare its absolute path in the
recorder's environment `files` list. The acceptance checker requires its exact
bytes in every receipt before/after snapshot. Editing criteria invalidates old
receipts even if an updated ledger names the new plan hash.

Set ledger `acceptance_plan_sha256` to the SHA-256 of the parsed plan serialized
with Python `json.dumps(plan, sort_keys=True, separators=(",", ":"))` (UTF-8).
Each ledger check needs unique `id`, `criteria` IDs, `kind`, boolean `passed`,
reviewed `evidence`, and absolute `receipt`. Existing consumer fields remain.
Record commands with `verify_command.py`; never execute a command from a ledger.
A single real suite may cover multiple criteria; review its actual assertions.

Run `check_integration.py impact.json ledger.json --root /repo --acceptance plan.json`
using the installed script path. This implies strict recorded verification.
Or run `acceptance.py plan.json ledger.json --root /repo` for acceptance alone;
that does not independently validate the impact/consumer map.

## Environment and boundaries

Use recorder `run --environment /evidence/environment.json`, for example
`{"files":["/repo/acceptance.json","/repo/requirements.lock","/test/config.json"],
"facts":{"database_schema":"reviewed-v3"}}`.
Relative paths resolve beside this declaration. Only hashes are stored. New
receipts also bind the actual command executable, recorder runtime and platform.
Declared facts are not automatic observations; verify external versions separately.
Never put secrets in facts or dump environment variables into test logs.

A boundary uses `id`, `status`, linked `criteria`, and review `evidence` when
verified. Anything other than `verified` remains unresolved. Explicit exceptions
are reported separately and never turn missing checks green.
Performance criteria require `max_duration_seconds` in the plan. This ceiling
covers whole-command wall time; test actual service/memory/query budgets inside
an appropriate benchmark. Keep the workload and environment reproducible.

## Evidence quality

Use tests that discriminate the expected behavior from plausible broken variants.
For high-impact fixes, prove the reproducer catches the original defect in a
safe disposable copy. Test the actual route, persisted effect or client contract.
A zero exit status, mock, coverage percentage or receipt alone cannot prove this.
Report untested boundaries and unavailable environments precisely; do not claim
all languages, services or production paths verified from local fixture results.
