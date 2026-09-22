# Changelog

## 0.7.0 — 2026-09-22

- Add scoped acceptance criteria and risk-specific scenario coverage, bound to
  exact plan bytes recorded before and after commands.
- Integrate acceptance with the strict consumer ledger; unresolved external
  boundaries and exceptions cannot silently become successful acceptance.
- Bind new receipts to executable/runtime identities, permissions, platform and
  explicitly declared dependency/configuration files, including external paths.
- Add conditional migration, concurrency, security, performance, deployment,
  recovery and user-journey instructions with behavioral specifications.
- Add SQLite migration and retry/idempotency executable fixtures with graders
  tested against plausible broken implementations.
- Preserve schema-1 receipt compatibility; those legacy receipts lack environment
  binding. No real Astra benchmark or universal language coverage is claimed.


## 0.6.0 — 2026-09-22

- Add paired executable behavior runner with isolated baseline/candidate fixtures.
- Record real command results with bounded logs and source-bound receipts.
- Add strict recorded-evidence mode to the integration checker.
- Preserve pre-change import consumers across deletions and renames.
- Add hash-bound, language-neutral reviewed contract/architecture declarations.
- Add installed-runtime diagnostics without starting language servers.
- Keep model measurements separate from synthetic harness tests.


## 0.5.0 — 2026-09-22

- Add generic stdio LSP reference client with explicit server argv/language ID,
  UTF-16 position conversion, request deadlines, bounded frames and source hashes.
- Handle server configuration requests; reject workspace mutation requests.
- Surface external/excluded references and indexing-completeness limitations.
- Bundle the integration checker inside astra-code; retain root CLI compatibility.
- Add language routing reference and installed-package smoke checks for every tool.
- Protocol fixtures are synthetic; cross-language server compatibility is not
  established by these tests. No automatic server download or all-language claim.
- Separately run live Python/Jedi and TypeScript-server cross-file fixtures;
  add explicit additional-document opening after observing cold-start omissions.

## 0.4.0 — 2026-09-22

- Add project-wide integration guidance: canonical owners, real entrypoints,
  consumers, generated contracts, configuration and compatibility evidence.
- Add incremental Python AST import facts and transitive impact candidates with
  content-bound snapshots, explicit coverage gaps and no target-code execution.
- Add a reviewed integration-ledger gate; it validates evidence completeness,
  not the truth of supplied claims or whole-project correctness.
- Fix shifted BM25 weights and fallback starvation after per-file result caps.
- Add six integration behavior specifications and regression tests (59 total tests).
- Independent tool review reproduced two additional defects; normalize changed
  paths and retain missing-module diagnostics even when parent packages exist.

Compiler/LSP-backed binding, other-language dependency graphs, external-consumer
verification and live Astra paired performance evaluations remain unimplemented.

## 0.3.0 — 2026-09-22

- Rank path and symbol matches above body text and require all query terms before a controlled any-term fallback.
- Add lightweight declaration-aware chunks for JavaScript/TypeScript, Go, Rust, Java/Kotlin/C#, and shell alongside Python AST chunks.
- Expand conservative secret-file and credential-marker exclusions.
- Add the supported `.codex-plugin/plugin.json` compatibility manifest and validate it against the portable manifest.
- Test the package on Python 3.10, 3.12, and 3.13 in CI, including bytecode compilation.

Existing index schema 1 caches must be purged once before using 0.3.0. No end-to-end Astra speed, token, or task-quality gain is claimed for this tooling release.

## 0.2.0 — 2026-09-22

- Keep two entry points; let obvious local edits skip procedural references.
- Add conditional context, evidence-based delegation, and controlled-experiment guidance.
- Add optional incremental Git/SQLite FTS5 code retrieval with content revalidation and bounded UTF-8 JSON.
- Stage installations before replacement, isolate backups from discovery, lock concurrent installs, and restore the exact backup on publication failure.
- Add strict paired-run comparison and expand behavioral specifications to 24 cases.
- Add primary-source research, Cursor comparison, operational limits, and an evidence-gated roadmap.
- Retain the MIT license and existing portable plugin layout.

No end-to-end Astra speed, token, or task-quality gain is claimed for this tooling release.

## 0.1.0

Initial coding and repository-instruction audit skills, installer, structural validation, and evaluation protocol.
