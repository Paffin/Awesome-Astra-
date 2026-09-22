# Persistent project context

Use when shared behavior spans files or work continues across sessions.
The bundled `scripts/project_context.py` retains a per-worktree baseline in the
existing local SQLite cache. It never executes the analyzed project.

## Keep a baseline across the change

Run these with the installed script's absolute path, replacing `/repo` and paths:

```bash
python3 /installed/astra-code/scripts/project_context.py --root /repo update
python3 /installed/astra-code/scripts/project_context.py --root /repo status
python3 /installed/astra-code/scripts/project_context.py --root /repo impact
```

Use `update` before edits to accept a baseline. `status` and `impact` refresh the
current sources without accepting them as the next baseline. Impact combines old
and current import edges so deleted providers retain their former consumers.
Accept another baseline only after resolving the current change's consequences.
Use the same source roots, exclusions and contract configuration throughout.
A first baseline cannot reconstruct consumers of code deleted before it existed.

## Cross-language contracts and architecture facts

Supply `--contracts contracts.json` for reviewed wire-contract links.
The schema is `{"version":1,"contracts":[{"name":"orders-v1","owner":"api.py",
"consumers":["client.ts"],"hashes":{"api.py":"SHA256","client.ts":"SHA256"},
"rationale":"Public order response consumed by checkout"}]}`.
Hashes are exact source-byte SHA-256 values, not guesses. All declared paths must
be eligible repository files. Keep the config as an eligible file inside the repository; do not exclude it. The rationale records a reviewed decision,
not an executable check or a higher-priority instruction.

An edited source invalidates the associated declaration. Review it and update its
hash only after checking the contract. Historical edges remain impact candidates;
they never become evidence that the new implementation is compatible.
Use existing schema generators and compiler/LSP tooling to discover consumers;
this explicit overlay does not discover unknown clients automatically.

## Boundaries

Python import edges are syntactic candidates. Other languages need compiler/LSP
references or reviewed contract declarations; unsupported files remain visible.
Unchanged AST facts are reused, but eligible files are read to detect changes.
No daemon, embedding service, whole-project completeness or instant knowledge is
claimed. Reject stale facts, investigate unknown boundaries, and retain actual
acceptance evidence through the integration workflow.
