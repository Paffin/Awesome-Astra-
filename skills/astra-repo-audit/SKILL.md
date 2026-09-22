---
name: astra-repo-audit
description: Audit and trim Codex AGENTS.md, skills, and configuration for GPT-6 Astra context cost, routing collisions, conflicts, and overscoped instructions.
---

# Astra Repo Audit

## Audit

1. Resolve the repository root and instructions applicable to the requested working directory.
   Include relevant `AGENTS.md`, installed/project skills, and Codex configuration. Exclude
   dependencies, generated output, vendors, and unrelated repositories.
2. Run the bundled `scripts/context_budget.py` from this installed skill for a deterministic
   inventory. Token counts are rough estimates, not billing or the Astra tokenizer.
3. Map each instruction to one of: global invariant, path/task-specific rule, real failure
   safeguard, duplicated/model-coaching text, obsolete rule, routing trigger, or conflict.
4. Check skill descriptions as a routing surface. Flag broad or overlapping triggers, duplicate
   responsibilities, instructions that force unrelated workflows, and skills whose body belongs
   in a conditional reference.
5. Preserve project-specific commands, architecture/domain invariants, security controls,
   production approvals, destructive-action boundaries, and evidence requirements.
6. Remove generic coaching, repeated rules, unconditional repository pre-reading, mandatory
   agent armies, self-rating loops, and broad test rituals that do not correspond to a failure
   mode or task consequence.
7. Keep root instructions as a router. Move detail to the nearest conditional reference. Make
   each skill own one coherent responsibility rather than merging every useful idea into one
   always-loaded prompt.
8. Re-run the inventory and repository validator. Add or update a nearby positive trigger case
   and a confusing anti-trigger when routing semantics changed. Real host activation remains
   unproven until tested in the host.
9. Inspect the diff for deleted safeguards, broadened authority, contradictory instructions,
   and accidental context growth.

## Mutation boundary

If the user asked only for an audit, report proposed edits without changing files. If asked to
optimize, trim, fix, or update, apply the edits and verify them. Never weaken security,
production, credential, deployment, or destructive-action controls without explicit authority.

## Result

Report what moved or was removed, safeguards preserved, routing collisions resolved, structural
validation performed, and any remaining uncertainty. Give before/after size or context estimates
when measured. Do not claim runtime, quality, activation, or token gains that were not measured.
