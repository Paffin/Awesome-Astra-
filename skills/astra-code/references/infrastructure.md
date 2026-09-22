# Infrastructure, containers, and delivery

Load for Terraform/IaC, Docker images, Kubernetes/Helm, CI/CD, runtime configuration, or
deployment behavior. Treat infrastructure as executable product code with state and rollback
semantics, not as incidental YAML.

## Source of truth and change surface

1. Find the existing module/chart/workflow and environment inheritance before adding parallel
   variables or resources. Reuse provider/module conventions and pinning policy.
2. Keep configuration typed, validated, documented at the owning boundary, and consumed by the
   runtime. Trace values from declaration through rendered artifact to effective behavior.
3. For IaC, inspect formatting/validation plus the actual plan or equivalent diff when the host
   and credentials allow it. Review replacements, privilege changes, public exposure, state
   moves, dependency ordering, drift, and destroy actions explicitly.
4. For containers, preserve reproducibility, non-root/runtime permissions, bounded image
   contents, health/readiness semantics, signals, resource limits, and secret injection.
5. For Kubernetes/Helm, verify rendered manifests and selectors, ports, probes, RBAC, rollout
   ordering, disruption behavior, and rollback-relevant state for the affected workload.

## CI/CD and release

Change the narrowest pipeline path that owns the behavior. Keep caches and parallelism from
hiding missing dependencies. Verify failure propagation and artifact provenance. Never turn a
test task into an unauthorized apply, deploy, release, or secret read.

Use delivery.md for cross-environment acceptance and recovery. Report the exact environment or
plan that was verified; a static lint pass is not proof of a successful rollout.
