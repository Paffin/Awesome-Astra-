# Research and design decisions

Reviewed **2026-09-22**. This is a selected primary-source review, not a claim to have read every article or established AGI. Upstream project popularity and benchmark numbers do not establish improvement for this pack.

## Astra and skill packaging

| Primary source | Adopted here | Deliberately avoided |
| --- | --- | --- |
| OpenAI, [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) | Narrow descriptions, conditional guidance, clear completion criteria. | Long inherited recipes and mandatory context gathering for tiny edits. |
| OpenAI, [Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model) | Calibrate verification and delegation to the task and host. | Pretending prose implements API concurrency, caching, or steering. |
| OpenAI, [model reference](https://developers.openai.com/api/docs/models/gpt-6-astra) | Use the documented `gpt-6-astra` identity; keep model selection in the host. | Invented model aliases, hidden settings, or a universal best reasoning effort. |
| OpenAI, [Build skills](https://learn.chatgpt.com/docs/build-skills) | Metadata for discovery, lazy bodies/resources, user and repo skill directories. | Backups containing duplicate skills inside the discovery directory. |
| OpenAI, [Build plugins](https://learn.chatgpt.com/docs/build-plugins) | Portable root `plugin.json`, Codex `.codex-plugin/plugin.json`, `skills/`, optional UI metadata. | Unneeded MCP servers and lifecycle hooks. |
| OpenAI, [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills) | Evaluate behavior and efficiency with evidence beyond static lint. | Treating unit tests or case counts as model benchmark results. |
| [Agent Skills specification](https://agentskills.io/specification) | Standard `SKILL.md` entry points with frontmatter and supporting resources. | Copying host-specific role-card metadata into portable skill frontmatter. |

The official model reference lists `low`, `medium`, `high`, `xhigh`, and `max` reasoning levels. Selecting the largest one for every task is not an evaluated policy here. Use controlled task-specific comparisons, and retain host safety controls. We do not install a Codex configuration, infer account entitlement, or promise a particular host exposes every API capability.

## The requested projects: what survives the critique

| Project / inspected primary material | Useful idea | Adaptation, not wholesale copying |
| --- | --- | --- |
| [Ponytail](https://github.com/DietrichGebert/ponytail), [SKILL.md](https://raw.githubusercontent.com/DietrichGebert/ponytail/main/skills/ponytail/SKILL.md) | Reuse existing solutions; resist speculative machinery; fix the causal layer. | Smallest **complete** change. No always-active persona, automatic scope reduction, intensity modes, or strict line-count optimization. |
| [Superpowers](https://github.com/obra/superpowers), [systematic debugging](https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md) | Reproduce, narrow the cause, test one hypothesis, verify the actual fix. | Keep evidence, not the entire mandatory multi-phase ritual. No debug commands that expose credentials; no mandatory new test suite for every typo. |
| [Agency Agents](https://github.com/msitarzewski/agency-agents), [Reality Checker](https://raw.githubusercontent.com/msitarzewski/agency-agents/main/testing/testing-reality-checker.md) | Check deliverables against actual artifacts rather than accepting confident status reports. | Evidence must suit the task. No mandatory browser screenshots for backend work, invented grade, compulsory failure verdict, or claim of persistent memory. |
| Karpathy, [autoresearch](https://github.com/karpathy/autoresearch), [README](https://raw.githubusercontent.com/karpathy/autoresearch/master/README.md) | Fixed experiment scope/budget, measurable feedback, keep/discard changes. | Independent acceptance and safety gates, held-out tasks, bounded experiments. Do not transfer training results to software tasks or copy the suggestion to disable permissions. |

All new code and workflow prose are an original synthesis. These links credit ideas; this release does not vendor upstream implementations or claim endorsement. The repository retains its existing MIT license. Reuse of upstream text/code in future changes requires preserving the applicable notices.

## Cursor: observed mechanisms versus our implementation

| Cursor primary source | Relevant mechanism | This release |
| --- | --- | --- |
| [Securely indexing large codebases](https://cursor.com/blog/secure-codebase-indexing), 2026-01-27 | Merkle-based synchronization, syntactic chunks, content-based embedding reuse and access checks when sharing indexes. | Per-file content hashes, incremental replacement, per-worktree isolation. No server, Merkle sync, shared index, or embeddings. |
| [Improving agent with semantic search](https://cursor.com/blog/semsearch), 2025-11-06 | Semantic retrieval complements grep. | Lexical FTS5 retrieval complements targeted reads; semantics remain an explicit future option. |
| [Dynamic context discovery](https://cursor.com/blog/dynamic-context-discovery), 2026-01-06 | Load relevant context on demand; retain large outputs as accessible files. | Optional references, bounded excerpts, local evidence pointers, concise handoffs. |
| [Fast regex search](https://cursor.com/blog/fast-regex-search), 2026-03-23 | Index-assisted exact search complements semantic retrieval. | Use native `rg` for exact search. SQLite FTS5 is not Cursor's regex engine. |

See [CURSOR_INDEXING.md](docs/CURSOR_INDEXING.md) for operational limits. Cursor's published measurements concern its own harness and evaluations; none are claimed as gains for Awesome Astra.

## Release evidence and non-claims

### 0.4.0 application of the research

Astra guidance is applied as a compact conditional integration reference, not
mandatory full-repository reading. Context minimization must not omit affected
consumers. Cursor's indexing descriptions distinguish incremental maintenance,
semantic discovery and exact lookup; none establishes completeness of consumers.
The new AST map consequently labels syntactic import candidates, fingerprints
current source, reuses unchanged facts and exposes unknowns. It is not Cursor's
Merkle/embedding implementation and is not a compiler-backed graph.

Primary pages consulted for this change: the Astra skills article and model
guidance linked above, and Cursor's secure indexing, dynamic context discovery
and fast regex search articles linked above. This is selected-source coverage,
not a claim that every Astra article was read. Exact model selection remains
`gpt-6-astra` in the host; no hidden settings, account changes or invented gains.

The implementation has deterministic unit/integration tests using temporary Git repositories. Behavior cases specify intended model outcomes but are not model runs. The paired-run comparator analyzes supplied telemetry; it does not authenticate its provenance or grade correctness. No Astra benchmark, token-saving percentage, or speedup is claimed.

Prior research notes remain in [the 0.1.0 repository snapshot](https://github.com/Paffin/Awesome-Astra-/blob/e96fadce24e1c635a44a13058aebc74ead662d17/RESEARCH.md). The current review focuses on the primary material directly used for this revision rather than reasserting every earlier paper's conclusion.
