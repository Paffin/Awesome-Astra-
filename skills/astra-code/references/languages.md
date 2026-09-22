# Language-server context

Use an existing trusted compiler/LSP integration first. When none is exposed by
the host, the bundled [client](../scripts/lsp_context.py) can query any explicitly
selected stdio Language Server Protocol server advertising references support.
There is no fixed language allowlist. This is protocol support, not a claim that
every server or language has been tested.

Run bundled `scripts/doctor.py --server-command gopls` to check executable
availability and skill dependencies without launching servers. Supply any server
executable; discovery is not a compatibility test.

## Select the actual project toolchain

Read the affected package's build metadata and use its existing server/toolchain.
Do not download executables or execute repository-provided server commands blindly.
Servers may execute build tools/plugins and read more than the selected file;
the client's source exclusions do not sandbox the server. Use host permissions.

Common ecosystems and server families to look for:

| Language | Server family |
| --- | --- |
| Python | Pyright / python-lsp-server |
| JavaScript, TypeScript | typescript-language-server |
| Go | gopls |
| Rust | rust-analyzer |
| C, C++, Objective-C | clangd |
| Java | Eclipse JDT LS |
| C# | OmniSharp / compatible .NET server |
| Kotlin | Kotlin language server |
| Swift | SourceKit-LSP |
| Ruby | Ruby LSP |
| PHP | Phpactor / Intelephense |
| Lua | lua-language-server |
| Bash | bash-language-server |
| Dart | Dart language server |
| Elixir | ElixirLS |
| Scala | Metals |
| Haskell | Haskell Language Server |
| OCaml | ocamllsp |
| R | languageserver |
| Other | Supply its language ID and compatible stdio server argv |

These are routing examples, not installed dependencies or validated compatibility
claims. Use the server's documented startup arguments and project requirements.

## Query a symbol

```bash
python3 /installed/astra-code/scripts/lsp_context.py --root /repo \
  --file internal/service.go --line 12 --column 6 --language go \
  --server '["gopls"]'
```

Inputs are 1-based line and Unicode-character column in the current on-disk file.
Output ranges use LSP's 0-based UTF-16 units, with source hashes and a snapshot ID.
The client opens the target document, requests references, rejects source changes
during the request, bounds messages/time, and refuses truncated output.
External/excluded locations count as unresolved; source content is not returned.
Use repeatable `--open-file relative/path` to open relevant same-language files
before querying. The report records `opened_files`. In the TypeScript smoke test,
opening the consumer changed a definition-only answer into cross-file references.
This is not a guarantee of full-workspace indexing; prefer a persistent host LSP.

## Use the evidence

Treat references as server-provided evidence for this symbol. Query each changed
public symbol and inspect its consumers. A successful initialize response is not
proof that background indexing is finished; an empty list cannot certify absence.
If the server needs build metadata or warm indexing, use the host's persistent
LSP session or compiler tooling and record the remaining gap.

Wire contracts, route names, configuration and cross-language calls still require
the integration workflow. Never turn unavailable servers into regex-based claims
of semantic completeness. Continue authorized implementation, but report the exact
unverified boundary. Do not claim that all project consumers have been found.
