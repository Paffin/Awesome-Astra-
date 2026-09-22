# Security-focused change review

Load when code crosses a trust boundary or the user requests a security-sensitive review.
Keep findings concrete: a reachable failure or abuse path, affected asset, and smallest
credible correction.

## Differential review

1. Start from the actual diff and its base. Use history or blame only when it explains why a
   sensitive check, compatibility shim, or invariant exists.
2. Estimate blast radius from callers, registrations, shared schemas, permissions, and data
   flows. Combine semantic/compiler evidence with exact searches for dynamic wiring.
3. Inspect authentication, authorization, tenant/ownership checks, input parsing, output
   encoding, file/path handling, command execution, SSRF/network destinations, deserialization,
   secrets, logs, and insecure defaults only where the change reaches them.
4. Check both allowed and denied paths. A happy-path authorization test is incomplete.
5. Use existing SAST, dependency, secret, or policy tooling when available. Treat findings as
   leads until confirmed against repository behavior; suppress false positives with evidence,
   not wishful thinking.

## Adversarial and regression checks

For a material trust-boundary change, state a concrete attacker capability and abuse scenario.
Verify the fix closes the path without weakening normal behavior. When practical, keep a
regression test or invariant that fails on the vulnerable form.

Do not generate exploit theatrics when the task is ordinary code review. Do not expose secrets,
production data, or unsafe payloads to prove a point. Missing external systems remain an
explicit verification gap.
