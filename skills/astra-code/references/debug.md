# Debug and fix

## Evidence loop

1. Capture the exact symptom, failing command, expected behavior, and first actionable error. Reproduce when safe and practical.
2. Reduce the search space from the failure boundary: stack frame, log field, assertion, request, state transition, or recent diff.
3. Form one falsifiable hypothesis at a time. Run the cheapest observation that can reject it.
4. Trace the causal path far enough to distinguish the root cause from a downstream symptom. When existing tests or coverage expose executed paths, use them to prioritize rather than reading broadly.
5. Patch the smallest stable layer and preserve existing contracts unless the contract itself is wrong.
6. Re-run the original reproduction first, then the nearest related checks.

## Guardrails

- Do not change code before collecting enough evidence to explain the failure.
- Do not hide failures with broad exception handling, retries, sleeps, weaker assertions, or disabled validation unless that behavior is the explicit requirement.
- Treat environment, data, race, and version mismatches as hypotheses rather than assuming the source code is wrong.
- Add a regression test when it is deterministic and protects the observed contract.

If reproduction is impossible, state the missing evidence and validate the fix with the closest deterministic proxy.
