# Verified workflow (0.7.0)

The runtime tools ship inside `astra-code`. The model-evaluation runner lives in
the repository's `tools/`, because it tests skill revisions rather than solves
normal user coding tasks. All commands below use example paths; replace them.

## Installed runtime

```bash
python3 /installed/astra-code/scripts/doctor.py --server-command gopls
```

This checks Python, Git, SQLite FTS5 and bundled scripts, and locates explicitly
named server executables. It does not launch servers or certify compatibility.
Live reference smoke tests currently cover Python/Jedi and TypeScript only.

## Retain consumers before editing

```bash
python3 /installed/astra-code/scripts/project_context.py update --root /repo
# Make the requested change.
python3 /installed/astra-code/scripts/project_context.py impact --root /repo > /evidence/impact.json
```

The SQLite baseline is per Git worktree. `impact` refreshes current sources and
combines current and previous import edges; a removed module cannot silently
remove its former consumers from impact review. `status` checks freshness.
An explicit next `update` accepts a new baseline; do it after resolving the change.
Use the same `--source-root`, `--exclude` and `--contracts` options throughout.
The default output budget is 100 KB; increase `--max-bytes` for larger projects.
Oversized results fail without partial output or advancing the baseline.

`--contracts contracts.json` adds reviewed links across languages, generated
schemas, wire formats and configuration. The config must be an eligible file
inside the repository. Its schema is documented in the installed
[context reference](../skills/astra-code/references/project-context.md).
Owner/consumer hashes make stale declarations explicit gaps. These are reviewed
assertions, not automatic discovery or compiler-proven relationships.

## Record actual acceptance commands

```bash
python3 /installed/astra-code/scripts/verify_command.py run --root /repo \
  --argv '["python3","-m","unittest","discover","-s","tests"]' \
  --receipt /evidence/tests.json --timeout 120
python3 /installed/astra-code/scripts/verify_command.py verify --root /repo \
  --receipt /evidence/tests.json
```

Use the project's actual commands and an additional real-entrypoint test when
appropriate. Argv is explicit JSON, not shell text. Each new receipt keeps source
hashes before/after, exit status, elapsed time and a bounded adjacent log.
Existing receipts are never overwritten. Receipts/logs must be outside the repo.
Source edits, failed commands, timeouts and altered logs invalidate verification.
Ignored/excluded files and external systems are not automatically covered.
Use `--environment` to bind explicitly selected dependency/configuration files;
see [development checks](DEVELOPMENT_CHECKS.md).
Checksums detect accidental changes, not forgery by a writer of both files.

Complete the reviewed consumer ledger from [EVALUATION.md](../EVALUATION.md), then:

```bash
python3 /installed/astra-code/scripts/check_integration.py \
  /evidence/impact.json /evidence/ledger.json --root /repo --require-recorded
```

Every check must include its absolute `receipt` path. The strict mode rechecks
impact source inventory and receipt freshness. Coverage gaps and consumer
compatibility still require review. The legacy mode validates bookkeeping only.
A successful command does not establish that its assertions cover the requirement.

## Run baseline/candidate model evaluations

Install/authenticate Codex CLI separately in a dedicated evaluation environment
without the target skill installed globally. Preserve the same host policy,
reasoning configuration and tools for both variants. The adapter retains host
permissions; the runner is not a hostile-code security sandbox.

```bash
python3 tools/run_evals.py --model gpt-6-astra --repeats 3 \
  --executor '["python3","/checkout/tools/codex_executor.py","--workspace","{workspace}","--prompt","{prompt}","--model","{model}","--variant","{variant}"]' \
  --output /evidence/astra-v060
```

Replace `/checkout` with this checkout's absolute path and use the exact model ID
available in your host. No fallback model is silently substituted. The adapter
uses a fresh `codex exec --ephemeral --json --sandbox workspace-write` invocation.
Default prompts are identical; candidate skill discovery is implicit. Add adapter
`--explicit-skill` to evaluate explicit invocation as a separate experiment.
Implicit fixture success does not by itself prove the skill was activated: inspect
the retained trace. There is no invented trigger-success percentage.

The runner freezes fixtures/skill/graders, creates separate Git workspaces,
alternates variant order over repetitions, and keeps prompts, traces, diffs,
final workspaces, command outcomes and input provenance. Independent graders
exercise shared pricing, route registration, a Python/JavaScript wire contract,
SQLite legacy-data migration and concurrent retry/idempotency behavior.
Node.js is required for the cross-language fixture; missing tooling never passes.
`--synthetic` labels harness tests, not Astra runs. Missing token usage stays null.
The CLI returns 1 if any case fails; failures are retained for comparison.

Model access, executor authentication and host-level isolation must be available
before a real run. This release implements the runner; no live Astra performance
result is claimed. See [official exec documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
