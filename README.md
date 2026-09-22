# Awesome Astra

**Lean Codex skills. Relevant code context. Verifiable results.**

[Русский](README.ru.md) · [Research](RESEARCH.md) · [Cursor indexing](docs/CURSOR_INDEXING.md) · [Evaluation](EVALUATION.md) · [MIT](LICENSE)

Two focused skills for GPT-6 Astra, not a giant system prompt or a mandatory agent army. The pack combines a short coding workflow, an instruction audit, and an optional local repository index. No API key, MCP server, hook, telemetry, or Python package installation is required by the bundled tools.

| Skill | Purpose |
| --- | --- |
| [`astra-code`](skills/astra-code/SKILL.md) | Implement, debug, refactor, design, and review with targeted context and proportionate verification. |
| [`astra-repo-audit`](skills/astra-repo-audit/SKILL.md) | Trim obsolete or conflicting Codex instructions without removing real safeguards. |

Version **0.6.0** adds recorded command evidence, persistent before/after impact context and an executable paired-evaluation runner. The installed skill includes all runtime tools. External language servers and model executors remain separate. **End-to-end Astra quality, latency, and token gains have not been measured.** This is not an official OpenAI product.

## Project-wide integration

The skill now requires tracing changed contracts to consumers and verifying the
real entrypoint. For Python, a bundled impact map caches AST import facts by hash:

```bash
python3 skills/astra-code/scripts/project_map.py --root /repo --source-root src --changed src/pkg/core.py
```

The output includes transitive import candidates, a working-tree snapshot hash,
parse/dynamic/external gaps and unsupported files. These are syntactic facts,
not compiler binding or a universal call graph. Unchanged facts are reused;
changed/deleted files invalidate the map. It refuses oversized output rather
than silently omitting consumers. `tools/check_integration.py` validates a reviewed
ledger against this report; see [the evidence format](EVALUATION.md).

## Install

Requires Python 3.10+. The optional index also requires Git and SQLite with FTS5.

```bash
git clone https://github.com/Paffin/Awesome-Astra-.git
cd Awesome-Astra-
python3 tools/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/install.py
```

The GitHub repository currently has a trailing hyphen. Review downloaded code before executing it; pin a reviewed commit for reproducible deployment.

The installer copies to `~/.agents/skills`. Use `--skill astra-code` for only the coding skill, or `--dest /path/to/repo/.agents/skills` for project scope. Select GPT-6 Astra in your Codex host; the installer never changes model settings or approvals.

Existing skills are protected. `--force` stages a complete copy before replacement and keeps the previous installation under `.astra-skill-backups` **beside**, not inside, the destination directory. An installation lock prevents overlapping writes. A crash may require inspecting and removing a stale `.astra-install-*.lock`; backups are retained for manual recovery. Transactions are per skill, not across the entire pack. Older backups already inside a skills directory are not deleted automatically.

Alternatively, ask Codex's `$skill-installer` to install `skills/astra-code` and `skills/astra-repo-audit` from this repository. Root `plugin.json` is the portable manifest; `.codex-plugin/plugin.json` is the Codex compatibility manifest, and validation requires them to agree. GitHub publication is not marketplace publication. See [official installation and packaging documentation](https://learn.chatgpt.com/docs/build-plugins).

## Use

The installable skill is [skills/astra-code/SKILL.md](skills/astra-code/SKILL.md),
with UI metadata, conditional workflow references and all runtime scripts in the
same folder. It runs independently of this repository after installation.
Invoke it once with the task; the skill chooses the relevant workflow and tools:

```text
$astra-code implement this change through the existing entrypoint, trace every
affected contract and consumer, verify integration, and report coverage gaps.
```

For non-Python semantic references, use the host's compiler/LSP tools or the
bundled [language-independent client](skills/astra-code/references/languages.md).
It accepts an explicit server argv and language ID, without a language allowlist.
Protocol tests use a synthetic server; this release does not claim validated
compatibility with every named server or completed workspace indexing.
Live Python and TypeScript cross-file smoke tests also pass; exact versions,
fixtures and reproducible commands are recorded in EVALUATION.md.

```text
$astra-code fix the worker's retry race and verify the regression.
$astra-code review this branch against main; report material defects only.
$astra-repo-audit audit AGENTS.md and skills; report only, do not edit.
```

Explicit invocation selects the intended skill; it does not make model behavior deterministic. Small edits take a direct path. Substantial tasks load one relevant implementation/debug/design/review reference. Context retrieval, delegation, and measured experiments are conditional, not mandatory preambles.

## Optional local code retrieval

```bash
python3 skills/astra-code/scripts/repo_index.py --root /path/to/project search "invoice retry" --max-bytes 12000
python3 skills/astra-code/scripts/repo_index.py --root /path/to/project --exclude 'internal/*' index
python3 skills/astra-code/scripts/repo_index.py --root /path/to/project purge
```

Run from this clone, or use the installed script's absolute path. Apply additional exclusions consistently on every invocation.

The index uses Git inventory, content hashes, Python AST boundaries, conservative declaration boundaries for JavaScript/TypeScript, Go, Rust, Java/Kotlin/C#, and shell, plus line-based fallbacks. Weighted SQLite FTS5 ranks symbols and paths above body text, tries all query terms first, then fills remaining slots with clearly labeled any-term matches. Searches refresh changed files and remove deleted/excluded entries. Results contain source paths, line ranges, hashes, match mode, and bounded excerpts. It is **not** an embedding service, a full cross-language dependency graph, or a Cursor clone. It scans eligible files on each invocation; incremental means unchanged files are not rechunked or reinserted.

If you used the 0.2.0 index, run `purge` once before the first 0.3.0 search; schema changes are rejected rather than migrated silently.

Code stays in a per-worktree cache under Git metadata. The tool performs no network calls, but feeding results into a cloud Codex session still sends that selected context to its provider. Exclusions are not a complete secret scanner or a security boundary. Read [limits and data handling](docs/CURSOR_INDEXING.md).

## Recorded checks and persistent context

See [the v0.6 workflow](docs/VERIFIED_WORKFLOW.md) for command receipts, retained
pre-change consumers, hash-bound cross-language contract declarations and the
executable baseline/candidate runner. Use `scripts/doctor.py` inside the installed
skill to check bundled dependencies; it does not start or install language servers.

## Measure instead of guessing

```bash
python3 tools/compare_runs.py /path/to/measured-runs.jsonl
```

The comparator validates paired telemetry, rejects mismatched setups, counts cached input only once, and flags observed quality/safety regressions. It neither launches nor grades a model. [EVALUATION.md](EVALUATION.md) specifies the input format and controls. Behavior specifications are separate from executed model results.

The instruction audit uses byte-based token estimates, not Astra's tokenizer or billing records. Package validation enforces two entry points, compact metadata, reference links, and byte/line budgets.

## Design lineage

Ponytail informs reuse and restraint; Superpowers informs causal debugging; Agency Agents informs evidence-based handoffs; Karpathy's autoresearch informs controlled experiments. Astra-specific OpenAI guidance takes precedence over inherited ceremony. No upstream skill is concatenated into this pack. [RESEARCH.md](RESEARCH.md) records adopted ideas, rejected mechanisms, and sources.

[Contributing](CONTRIBUTING.md) · [Roadmap](docs/ROADMAP.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)
