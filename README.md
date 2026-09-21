# Astra Codex Skills

Two small, research-backed workflows for using GPT-6 Astra in Codex without turning the context window into a second codebase.

- `astra-code` — implement, debug, refactor, review, or design a code change with targeted context and proportionate verification.
- `astra-repo-audit` — find and remove stale, duplicated, conflicting, or over-broad Codex instructions while preserving real safeguards.

This repository is a portable [Agent Plugin](https://developers.openai.com/plugins/build/plugins) and each skill also follows the open Agent Skills layout.

## Why this is deliberately small

GPT-6 Astra needs less procedural handholding than earlier coding models. Every installed skill description consumes always-on context, and every loaded instruction competes with the task and repository. The design therefore uses:

1. two non-overlapping skill descriptions;
2. a short router in `astra-code`;
3. exactly one task route loaded at a time;
4. focused repository search instead of a mandatory repo dump;
5. the narrowest meaningful verification before broader checks;
6. explicit completion evidence so Astra continues past a first draft.

The pack does **not** claim a token, latency, or success-rate improvement without a paired evaluation. See [EVALUATION.md](EVALUATION.md) for the measurement protocol and [RESEARCH.md](RESEARCH.md) for the evidence behind each design choice.

## Install

### Ask Codex to install from GitHub

After this repository is public, invoke `$skill-installer` and ask it to install either or both folders:

```text
Install astra-code and astra-repo-audit from
https://github.com/Paffin/Awesome-Astra-/tree/main/skills
```

### Local Codex installation

Clone the repository and run:

```bash
python3 scripts/install.py
```

By default the installer copies both skills to `$HOME/.agents/skills`, the user-level location documented by Codex. It refuses to overwrite an existing skill unless `--force` is supplied; forced replacement first creates a timestamped backup.

Install only one skill or choose another destination:

```bash
python3 scripts/install.py --skill astra-code
python3 scripts/install.py --dest /path/to/repo/.agents/skills
```

### Plugin package

The repository root contains `plugin.json`, and portable hosts discover the two workflows under `skills/`. No MCP server, network permission, hook, or credential is required.

## Use

Explicit invocation is deterministic:

```text
$astra-code fix the race in the queue worker and verify the regression.
$astra-code review this branch against main.
$astra-repo-audit audit this repository's AGENTS.md and skills; report only.
$astra-repo-audit trim the instruction bloat and validate the edited skills.
```

Both skills also allow implicit invocation, but their descriptions are intentionally narrow to avoid routing unrelated work into them.

## Design

`astra-code` keeps only the shared operating contract in context, then selects one route:

| Route | Load when |
| --- | --- |
| `implement.md` | Feature, refactor, migration, or ordinary code change |
| `debug.md` | Failure, regression, flaky behavior, or incorrect output |
| `review.md` | Pull request, branch, commit, patch, or uncommitted diff |
| `design.md` | A consequential architecture choice blocks implementation |

`astra-repo-audit` is separate because instruction maintenance is a different job and should not burden normal coding turns. Its only script, `context_budget.py`, performs a read-only deterministic inventory and clearly labels token counts as estimates.

## Validate

The project uses only the Python standard library:

```bash
python3 tools/validate.py
python3 -m unittest discover -s tests -v
```

CI checks frontmatter, naming, links, context-size budgets, plugin metadata, eval fixtures, installer behavior, and the context-budget script.

## Contributing

Changes should remove more ambiguity than they add context. Read [CONTRIBUTING.md](CONTRIBUTING.md), add or update an eval case, and include measured evidence for performance claims.

## License

[MIT](LICENSE)
