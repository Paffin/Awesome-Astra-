#!/usr/bin/env python3
"""Evidence-backed Python import impact map; never executes target project code.

Import candidates are syntactic, not proof of runtime binding. Other languages,
dynamic loading and external consumers remain explicit coverage gaps.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path, PurePosixPath

import repo_index

VERSION = "1"


def facts(path: str, text: str) -> dict:
    result = {"definitions": [], "imports": [], "dynamic_lines": [], "parse_error": None}
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError) as exc:
        result["parse_error"] = type(exc).__name__
        return result
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result["definitions"].append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({"module": alias.name, "level": 0,
                    "names": [], "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            result["imports"].append({"module": node.module or "", "level": node.level,
                "names": [alias.name for alias in node.names], "line": node.lineno})
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name in {"__import__", "import_module", "getattr", "exec", "eval"}:
                result["dynamic_lines"].append(node.lineno)
    return result


def module_name(path: str, source_root: str) -> str | None:
    p = PurePosixPath(path)
    try:
        relative = p.relative_to(PurePosixPath(source_root))
    except ValueError:
        return None
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def build(db: sqlite3.Connection, root: Path, patterns: list[str], source_roots: list[str]) -> dict:
    stats = repo_index.refresh(db, root, patterns)
    db.execute("CREATE TABLE IF NOT EXISTS map_facts (path TEXT PRIMARY KEY, digest TEXT, version TEXT, data TEXT)")
    rows = list(db.execute("SELECT path,digest FROM files ORDER BY path"))
    parsed, reused = 0, 0
    records = {}
    with db:
        db.execute("DELETE FROM map_facts WHERE path NOT IN (SELECT path FROM files)")
        for path, digest in rows:
            if not path.endswith(".py"):
                continue
            cached = db.execute("SELECT data FROM map_facts WHERE path=? AND digest=? AND version=?",
                                (path, digest, VERSION)).fetchone()
            if cached:
                record = json.loads(cached[0])
                reused += 1
            else:
                source = repo_index.read_source(root, path)
                if source is None or source[1] != digest:
                    raise ValueError("Source changed while building map; retry")
                record = facts(path, source[0])
                db.execute("INSERT OR REPLACE INTO map_facts VALUES (?,?,?,?)",
                           (path, digest, VERSION, json.dumps(record)))
                parsed += 1
            records[path] = record
    # Detect edits, additions, deletions and policy changes during construction.
    current = []
    for path in repo_index.inventory(root):
        source = None if repo_index.excluded(path, patterns) else repo_index.read_source(root, path)
        if source:
            current.append((path, source[1]))
    if current != rows:
        raise ValueError("Working tree changed while building map; retry")
    modules: dict[str, set[str]] = {}
    identities: dict[str, set[str]] = {}
    for path in records:
        for prefix in source_roots:
            name = module_name(path, prefix)
            if name:
                modules.setdefault(name, set()).add(path)
                identities.setdefault(path, set()).add(name)
    edges, unresolved = [], []
    for path, record in records.items():
        for imp in record["imports"]:
            requested = set()
            if not imp["level"]:
                requested.add(imp["module"])
            else:
                for identity in identities.get(path, set()):
                    package = identity.split(".") if path.endswith("/__init__.py") else identity.split(".")[:-1]
                    if imp["level"] > len(package):
                        continue
                    base = package[:len(package) - imp["level"] + 1]
                    requested.add(".".join(base + ([imp["module"]] if imp["module"] else [])))
            targets = set()
            full_module_found = any(modules.get(module) for module in requested)
            for module in requested:
                # Importing a package executes its parents too.
                parts = module.split(".") if module else []
                for i in range(1, len(parts) + 1):
                    targets.update(modules.get(".".join(parts[:i]), set()))
                for name in imp["names"]:
                    targets.update(modules.get(".".join(filter(None, (module, name))), set()))
            if not full_module_found or "*" in imp["names"]:
                unresolved.append({"path": path, **imp, "reason": "external, missing, or wildcard import"})
            for target in sorted(targets):
                edges.append({"consumer": path, "provider": target, "line": imp["line"],
                              "evidence": "AST import candidate; runtime binding unverified"})
    signature = hashlib.sha256(json.dumps({"files": rows, "roots": source_roots,
        "exclude": patterns, "version": VERSION}, sort_keys=True).encode()).hexdigest()
    return {"snapshot_sha256": signature, "files": dict(rows), "facts": records,
            "edges": edges, "unresolved_imports": unresolved,
            "unsupported_files": [p for p, _ in rows if not p.endswith(".py")],
            "stats": {**stats, "parsed": parsed, "reused": reused},
            "whole_project_verified": False,
            "limitations": ["Syntactic Python imports, not compiler/LSP binding or call graph",
                "Dynamic loading, external consumers and other languages need separate verification",
                "Ignored, sensitive and unreadable files are excluded; snapshot is not a filesystem lock"]}


def impact(report: dict, changed: list[str]) -> dict:
    changed = list(dict.fromkeys(str(PurePosixPath(p)) for p in changed))
    reverse: dict[str, set[str]] = {}
    for edge in report["edges"]:
        reverse.setdefault(edge["provider"], set()).add(edge["consumer"])
    affected = set(changed)
    pending = list(changed)
    while pending:
        for consumer in reverse.get(pending.pop(), set()) - affected:
            affected.add(consumer)
            pending.append(consumer)
    return {"snapshot_sha256": report["snapshot_sha256"], "requested": changed,
            "missing_paths": [p for p in changed if p not in report["files"]],
            "affected_candidates": sorted(affected),
            "edges": [e for e in report["edges"] if e["provider"] in affected],
            "unresolved_imports": report["unresolved_imports"],
            "parse_errors": [p for p, f in report["facts"].items() if f["parse_error"]],
            "dynamic_files": [p for p, f in report["facts"].items() if f["dynamic_lines"]],
            "unsupported_files": report["unsupported_files"],
            "whole_project_verified": False, "limitations": report["limitations"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", action="append", help="explicit repo-relative import root; repeatable")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--max-bytes", type=int, default=100_000)
    args = parser.parse_args()
    try:
        prefixes = args.source_root or ["."]
        for value in prefixes + args.changed:
            if PurePosixPath(value).is_absolute() or ".." in PurePosixPath(value).parts or "\\" in value:
                raise ValueError("Paths must be repository-relative without traversal")
        if args.max_bytes < 512:
            raise ValueError("max-bytes must be at least 512")
        root, cache = repo_index.locations(args.root)
        db = repo_index.connect(cache, root)
        try:
            report = build(db, root, args.exclude, prefixes)
            if args.changed:
                report = impact(report, args.changed)
            output = repo_index.encoded(report)
            if len(output.encode()) > args.max_bytes:
                raise ValueError("Map exceeds byte budget; increase --max-bytes or use --changed. No partial map emitted")
            sys.stdout.write(output)
        finally:
            db.close()
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(f"project-map: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
