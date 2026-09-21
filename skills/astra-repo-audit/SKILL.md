---
name: astra-repo-audit
description: Audit and trim Codex AGENTS.md, skills, and configuration for GPT-6 Astra context cost, conflicts, and overscoped instructions.
---

# Astra Repo Audit

## Audit

1. Resolve the repository root and the instructions applicable to the requested working directory. Include `AGENTS.md`, `.agents/skills/**/SKILL.md`, and relevant `.codex/config.toml` files. Exclude dependencies, generated output, and vendor trees.
2. Run the bundled `scripts/context_budget.py` by its path inside this skill and pass the repository root for a deterministic inventory. Treat token counts as rough estimates, not billing data.
3. Classify every instruction as:
   - global and non-obvious;
   - conditional on a task or path;
   - duplicated, obsolete, or already handled well by Astra;
   - conflicting or capable of stopping safe progress.
4. Preserve project-specific commands, invariants, safety boundaries, and irreversible-action approvals.
5. Remove generic model coaching, repeated rules, unconditional pre-reading, compulsory broad test runs, and progress-report requirements that do not improve the result.
6. Move conditional detail into the nearest task-specific document or skill. Keep root documents as routers, and keep skill descriptions narrow enough to trigger only on their real workflow.
7. Re-run the inventory and validate every edited skill. Inspect the diff for lost constraints or broadened permissions.

## Mutation boundary

If the user asked only for an audit, report proposed edits without changing files. If the user asked to optimize, trim, fix, or update the repository, apply the edits and verify them.

Do not weaken security, production, credential, deployment, or destructive-action controls without explicit authorization.

## Result

Report before/after size and estimated context, the instructions removed or rerouted, safeguards preserved, validation performed, and any unresolved conflict. Do not claim runtime or quality gains that were not measured.
