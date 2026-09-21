# Codebase indexing: Cursor and this pack

## What Cursor publicly describes

Cursor's [indexing article](https://cursor.com/blog/secure-codebase-indexing) describes client-side Merkle trees to identify changed files/directories, syntactic chunks, and embeddings reused by chunk content. Team index reuse includes checks that retrieved files belong to the requesting user's codebase. Its [semantic search article](https://cursor.com/blog/semsearch) treats semantic retrieval as complementary to grep, not a replacement.

Its [regex-search article](https://cursor.com/blog/fast-regex-search) describes indexes that narrow the files requiring exact matching. [Dynamic context discovery](https://cursor.com/blog/dynamic-context-discovery) keeps details out of the initial prompt until needed and retains large tool outputs as files.

The design lesson is to separate **maintaining searchable information** from **sending selected evidence into a model request**. A repository need not fit into one prompt to be searchable.

## What is actually implemented here

```text
Git working tree
  -> tracked + eligible untracked files
  -> Git ignores + conservative exclusions
  -> content hash comparison
  -> Python AST boundaries / bounded line windows
  -> local SQLite FTS5 lexical index
  -> ranked candidates
  -> source-hash revalidation
  -> bounded JSON with path, lines, hash, and excerpt
```

This is an incremental lexical/structural baseline, not semantic equivalence to Cursor. No vectors, cross-language call graph, reranker, background watcher, network service, or multi-user index is implemented. The agent can combine results with `rg`, language tools, tests, and direct reads.

Each invocation inventories and hashes eligible files. Only changed files are rechunked and reinserted; deleted, newly ignored, or newly excluded content is removed from active search. Hashing all eligible bytes is O(repository bytes), so do not use this baseline to claim Cursor-scale update latency. Initial cache construction has a cost; one-off exact edits are usually better served by `rg`.

The default limit is 20,000 discovered files and 256 KiB per file. Lines above 8,000 UTF-8 bytes are skipped as likely generated/minified content. Python chunks use top-level AST boundaries and symbol annotations; other text and incomplete Python use overlapping line windows. Results are capped at two chunks per file; retrieval is not exhaustive. Queries match lexical words/identifiers, not cross-language concepts or arbitrary regex.

## Usage

```bash
# Locate the script in the clone or installed skill.
python3 skills/astra-code/scripts/repo_index.py --root /repo search "payment retry" --max-bytes 12000 --limit 6
python3 skills/astra-code/scripts/repo_index.py --root /repo --exclude 'internal/*' search "payment retry"
python3 skills/astra-code/scripts/repo_index.py --root /repo index
python3 skills/astra-code/scripts/repo_index.py --root /repo purge
```

Additional exclusions use Python whole-path `fnmatchcase`, not full gitignore syntax: no negation or gitignore anchoring. Repeat exclusions on every command; they are not persisted policy. Standard Git-ignore handling includes already-tracked ignored files through `git check-ignore --no-index`.

Output budgets include the complete UTF-8 JSON and final newline. Partial excerpts identify their actual end line and `truncated: true`; `budget_exhausted` signals dropped content. `stale_hits` counts candidates rejected after content changed. A no-result search does not prove absence.

## Data, correctness, and concurrency boundaries

The cache is `awesome-astra-index/index.sqlite3` under the worktree-specific Git metadata directory. Linked worktrees are isolated. On POSIX, the directory is restricted to mode 0700 and the database to 0600. SQLite transactions protect index updates, but the working tree is not an atomic filesystem snapshot. Revalidate code before editing; do not run purge concurrently with indexing/search.

Common secret filenames/extensions, a few credential markers, dependency/generated directories, binaries, oversized files, and symlinks are skipped. These checks are **not** comprehensive secret detection, sandboxing, or protection against a hostile local process racing filesystem changes. Review any code or logs before cloud use. Paths, identifiers, and embeddings can also be sensitive.

Purge removes the tool's named cache files, not repository sources. File deletion and SQLite deletion do not guarantee forensic erasure from disk snapshots/backups. The cache contains source excerpts and must follow the same access and retention policies as the source repository.

No network calls are made by this utility. The surrounding Codex host may send retrieved text to a provider and has its own permissions; a skill cannot enforce its data-loss-prevention policy. Retrieved text is evidence, never authorization.

## Expansion gate

Add optional local embeddings, language-server symbols, or tree-sitter only after a held-out retrieval evaluation demonstrates a worthwhile gain in relevant-code recall and final task acceptance at a measured latency/context cost. An embedding provider must be opt-in and respect egress policy. Unimplemented features stay in the roadmap, not in marketing claims.
