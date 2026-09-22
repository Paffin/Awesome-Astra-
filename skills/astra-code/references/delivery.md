# Delivery through real boundaries

Load only sections implicated by the change. Use existing project conventions,
permissions, toolchain and tests; no global checklist for a local text edit.

## External contracts and runtime configuration

Trace public schemas, routes, events and configuration keys beyond this repository.
Identify known external consumers and mixed-version expectations. Preserve the old
contract or verify the agreed versioned migration; unavailable clients stay unresolved.
Update the source schema and use its generator for derived clients.

Exercise effective configuration through the actual application startup: config
loading, flag defaults, provider/route registration, dispatch and observable effect.
Test malformed values and the disabled path where relevant. Verify deployed chart,
container or service config reaches the consumer. A declared variable is not proof
of use. Do not turn a test command into an unauthorized deployment.

## Security and user journeys

For changed access boundaries, test allowed AND denied roles, ownership/tenant
separation and cross-user resource IDs. Inspect injection surfaces, error messages
and logs for sensitive data. Use the project's security tooling where applicable.

For visible behavior, exercise the real UI/API/CLI journey: normal result, invalid
input, empty state and recoverable failure. Preserve keyboard navigation, focus and
accessible names on changed UI. A component snapshot is not end-to-end acceptance.
If the target browser/device is unavailable, record the unverified platform.

## Performance and resources

Measure affected hot paths against explicit workload and budget. Include N+1 calls,
query counts, payload sizes, memory/queue growth, cancellation and resource cleanup
where relevant. Use comparable environments and repeat noisy measurements.
The acceptance tool can enforce a whole-command wall-time ceiling; this is not a
service latency percentile, capacity test or memory budget. Use real benchmark
assertions for those metrics, record their environment and keep full evidence.

## Observability and recovery

Check that a failed operation can be diagnosed with actionable, non-sensitive
errors and correlation identifiers. Use existing metrics/logging conventions;
avoid logging every input or adding high-cardinality labels by default.
Exercise shutdown/restart, rollback or forward repair in a disposable environment
when the change affects them. Verify that diagnostics detect the failure and that
recovery restores the user-visible outcome. Configured alerts alone do not prove it.

## Reproducible evidence

Record the selected lock/toolchain/config files and non-secret environment facts
with the verification recorder. Distinguish automatically hashed files/executables
from declared database/image/service versions. A declared version is a reviewed
assertion; verify it against the actual test target when its identity matters.
Do not dump environment variables, credentials or complete configuration into logs.
Re-run affected checks after a covered dependency or configuration changes.
