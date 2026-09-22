# Development checks (0.7.0)

The new checks connect requested behavior, selected risk scenarios, actual command
runs and source/environment freshness. They do not infer test semantics or certify
unknown services. For small local edits, use the existing direct path.

## Choose affected risks

The skill routes migrations, persistence and concurrent/retried work to
`references/data-failures.md`. External contracts, effective configuration, security,
performance, diagnostics, recovery and visible user journeys use `delivery.md`.
`acceptance.md` explains how to record observable criteria and required scenarios.
These are language-neutral workflows. They use the target project's own compiler,
framework, test runner and deployment tooling; no language support is fabricated.

For a substantial change, create the acceptance plan before recording checks:

```json
{
  "schema": 1,
  "risks": [],
  "criteria": [
    {
      "id": "document-download",
      "expected": "Owners download documents; users from another tenant cannot",
      "kinds": ["entrypoint"],
      "risks": ["security"]
    }
  ],
  "boundaries": []
}
```

Place it in `/repo/acceptance.json`, an eligible source file, or include its path
in the recorder environment declaration. The security risk additionally requires
a `denied-path` check for this criterion. Other mappings:

| Selected risk | Required scenario kinds |
| --- | --- |
| migration | compatibility, recovery |
| concurrency | concurrency, replay, failure |
| external-contract | compatibility |
| performance | performance |
| user-journey | user-journey |
| recovery | recovery, failure |

Per-criterion risks keep checks tied to the affected behavior. Top-level risks
require the kinds somewhere in the plan. All plans require an entrypoint check.
Explicit `negative` kinds can cover invalid inputs independently of access control.

## Bind actual environment inputs

Example `/evidence/environment.json`:

```json
{
  "files": ["/repo/acceptance.json", "/repo/requirements.lock", "/test/build-config.json"],
  "facts": {"database_schema": "reviewed-test-v3"}
}
```

Only name existing, relevant files. Relative paths resolve beside the declaration,
not the target repository. Facts must be non-secret; they are declarations whose
hash is recorded, not verified observations of a database or container image.
No inherited environment variables or credentials are dumped.

```bash
python3 /installed/astra-code/scripts/verify_command.py run --root /repo \
  --argv '["python3","-m","unittest","tests.test_download"]' \
  --receipt /evidence/download.json --environment /evidence/environment.json
```

New schema-2 receipts also capture the resolved command executable, recorder
Python identity/version, platform and file permissions. They check before/after
and on re-verification; changed files, permissions or declarations invalidate them.
The recorder does not discover all tool dependencies, shebang interpreters, shared
libraries, inherited settings or remote service state. Add material local inputs
explicitly and verify external targets separately. Old schema-1 receipts remain
readable but have no environment binding.

## Connect acceptance to the existing integration ledger

Keep the existing `snapshot_sha256`, `consumers` and coverage reviews. Add
`acceptance_plan_sha256`, using the SHA-256 of Python canonical serialization:

```python
import hashlib, json
from pathlib import Path
plan = json.loads(Path('/repo/acceptance.json').read_text())
print(hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
```

Each check now identifies criteria and its scenario:

```json
{
  "id": "download-allowed",
  "criteria": ["document-download"],
  "kind": "entrypoint",
  "passed": true,
  "evidence": "Public download request returns the owner's document",
  "receipt": "/evidence/download.json"
}
```

Add a denied-path check tied to the same criterion and a real receipt whose
assertions exercise that scenario. A suite can serve multiple scenarios if its
actual assertions cover them. Merely relabeling a receipt is not semantic proof.

```bash
python3 /installed/astra-code/scripts/check_integration.py \
  /evidence/impact.json /evidence/ledger.json --root /repo \
  --acceptance /repo/acceptance.json
```

`--acceptance` implies strict recorded checks. Exact plan bytes must appear in
every receipt's source or explicit environment snapshots before and after command
execution. Changing the plan afterward cannot be repaired by just changing the
ledger hash. Freshness remains a local integrity check, not a cryptographic identity.
The standalone `acceptance.py PLAN LEDGER --root REPO` checks acceptance only;
it does not replace the consumer-impact gate.

A boundary contains `id`, `status`, linked `criteria` and review `evidence` when
verified. Unavailable/unresolved boundaries leave acceptance incomplete. Exceptions
are visible for review and cannot waive missing tests. Performance criteria use
`max_duration_seconds` for a whole-command limit; service percentiles, memory and
capacity need suitable benchmark assertions, not this timer alone.

## Stronger executable fixtures

The paired runner now includes five tasks. Two new ones use real SQLite files:

- Legacy-data migration: old reads/writes/inserts, existing balances, defaults,
  repeated startup, preservation of non-default values and failed-migration rollback.
- Retry/idempotency: atomic debit/credit, failure after debit, retry, concurrent
  duplicate delivery and conflicting reuse of the same event ID.

Fixture tests verify original bugs fail, known repairs pass and plausible shortcuts
are rejected. This validates the graders; it does not measure Astra. A real model
run still requires a separately available, authenticated Codex CLI environment.
