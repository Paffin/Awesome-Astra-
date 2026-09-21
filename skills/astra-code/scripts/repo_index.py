#!/usr/bin/env python3
"""Local, incremental Git working-tree search. Python 3.10+, Git, SQLite FTS5.

No network, code execution, embeddings, or background watcher. Source excerpts
are untrusted data. Exclusions reduce exposure; they are not a security sandbox.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
from pathlib import Path

SCHEMA = "2"
MAX_FILE_BYTES = 262_144
MAX_FILES = 20_000
CHUNK_LINES = 60
OVERLAP = 8
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "vendor",
             "dist", "build", "target", "coverage", "__pycache__", ".next", ".cache"}
SECRET_NAMES = {".npmrc", ".pypirc", ".netrc", "auth.json", "credentials",
                "credentials.json", "kubeconfig", "id_rsa", "id_ed25519",
                "secrets.yml", "secrets.yaml", "terraform.tfstate",
                "terraform.tfstate.backup"}
SECRET_EXTS = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".kdbx"}
SECRET_MARKER = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|"
                           r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bAKIA[A-Z0-9]{16}\b|"
                           r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b|"
                           r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")

DECLARATIONS: dict[tuple[str, ...], tuple[re.Pattern[str], ...]] = {
    (".js", ".jsx", ".ts", ".tsx"): (
        re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"),
    ),
    (".go",): (
        re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("),
        re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+(?:struct|interface)\b"),
    ),
    (".rs",): (
        re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:fn|struct|enum|trait|type|mod)\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?impl(?:<[^>]+>)?\s+([A-Za-z_]\w*)"),
    ),
    (".java", ".kt", ".kts", ".cs"): (
        re.compile(r"^\s*(?:(?:public|private|protected|internal|abstract|final|sealed|static|data|open|partial)\s+)*(?:class|interface|enum|record|object|struct)\s+([A-Za-z_]\w*)"),
    ),
    (".sh", ".bash", ".zsh"): (
        re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w-]*)\s*\(\)\s*\{"),
    ),
}


def git(root: Path, *args: str, data: bytes | None = None,
        allowed: tuple[int, ...] = (0,)) -> bytes:
    # Disable configurable fsmonitor commands: inventory must not execute them.
    result = subprocess.run(["git", "-C", str(root), "-c", "core.fsmonitor=false",
                             *args], input=data, capture_output=True, timeout=60)
    if result.returncode not in allowed:
        raise ValueError("Git inventory failed: " + result.stderr.decode("utf-8", "replace")[:500])
    return result.stdout


def locations(root: Path) -> tuple[Path, Path]:
    root = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).rstrip("\n")).resolve()
    metadata = Path(os.fsdecode(git(root, "rev-parse", "--absolute-git-dir")).rstrip("\n"))
    return root, metadata / "awesome-astra-index"


def inventory(root: Path) -> list[str]:
    raw = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    paths = set(raw.split(b"\0")) - {b""}
    if len(paths) > MAX_FILES:
        raise ValueError(f"More than {MAX_FILES} files; use focused rg instead of this baseline index")
    if paths:
        ignored = git(root, "check-ignore", "--no-index", "--stdin", "-z",
                      data=b"\0".join(sorted(paths)) + b"\0", allowed=(0, 1))
        paths.difference_update(ignored.split(b"\0"))
    # Undecodable filenames cannot be represented reliably in UTF-8 JSON/SQLite.
    return sorted(path.decode("utf-8", "strict") for path in paths)


def excluded(path: str, patterns: list[str]) -> bool:
    parts = Path(path).parts
    name = parts[-1].lower() if parts else ""
    return (not parts or Path(path).is_absolute() or ".." in parts
            or any(part in SKIP_DIRS for part in parts)
            or name == ".env" or name.startswith(".env.")
            or name in SECRET_NAMES or Path(name).suffix in SECRET_EXTS
            or any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns))


def read_source(root: Path, path: str) -> tuple[str, str] | None:
    """Reject symlinks (including parents), nonregular/binary/oversized files."""
    if Path(path).is_absolute() or ".." in Path(path).parts:
        return None
    current = root
    for part in Path(path).parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        fd = os.open(current, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                return None
            raw = stream.read(MAX_FILE_BYTES + 1)
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return None
    if len(raw) > MAX_FILE_BYTES or b"\0" in raw:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if SECRET_MARKER.search(text) or any(len(line.encode("utf-8")) > 8_000 for line in text.splitlines()):
        return None
    return text, hashlib.sha256(raw).hexdigest()


def terms(text: str) -> list[str]:
    split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", split.lower(), flags=re.UNICODE)


def declared_symbols(path: str, text: str) -> list[tuple[int, int, str]]:
    """Return conservative declaration starts for non-Python source."""
    suffix = Path(path).suffix.lower()
    patterns = next((value for suffixes, value in DECLARATIONS.items() if suffix in suffixes), ())
    found: list[tuple[int, int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                found.append((number, number, match.group(1)))
                break
    return found


def chunks(path: str, text: str) -> list[tuple[int, int, str, str, str, str, str]]:
    lines = text.splitlines(keepends=True)
    starts = {1, len(lines) + 1}
    symbols: list[tuple[int, int, str]] = []
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
            for node in tree.body:
                decorators = getattr(node, "decorator_list", [])
                starts.add(min([node.lineno] + [d.lineno for d in decorators]))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append((node.lineno, node.end_lineno or node.lineno, node.name))
        except (SyntaxError, ValueError, RecursionError):
            pass  # Unfinished source stays searchable via the line-based fallback.
    else:
        symbols = declared_symbols(path, text)
        starts.update(start for start, _, _ in symbols)
    result = []
    boundaries = sorted(starts)
    for low, high in zip(boundaries, boundaries[1:]):
        start = low
        while start < high:
            end = min(start + CHUNK_LINES, high) - 1
            body = "".join(lines[start - 1:end])
            labels = " ".join(name for a, b, name in symbols if a <= end and b >= start)
            path_tokens = " ".join(terms(path))
            symbol_tokens = " ".join(terms(labels))
            body_tokens = " ".join(terms(body))
            if body.strip():
                result.append((start, end, labels, body, path_tokens, symbol_tokens, body_tokens))
            if end + 1 == high:
                break
            start = end + 1 - OVERLAP
    return result


def connect(cache: Path, root: Path) -> sqlite3.Connection:
    if cache.is_symlink():
        raise ValueError("Refusing a symlink cache directory")
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(cache, 0o700)
    db = cache / "index.sqlite3"
    if db.is_symlink() or (db.exists() and not db.is_file()):
        raise ValueError("Refusing a nonregular cache database")
    fd = os.open(db, os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.close(fd)
    os.chmod(db, 0o600)
    connection = sqlite3.connect(db, timeout=30)
    try:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        expected = {"schema": SCHEMA, "root": str(root)}
        stored = dict(connection.execute("SELECT key, value FROM meta"))
        if stored and stored != expected:
            raise ValueError("Cache version/root mismatch; purge it before rebuilding")
        connection.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", expected.items())
        connection.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, digest TEXT)")
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS excerpts USING fts5("
                           "path UNINDEXED, start UNINDEXED, end UNINDEXED, symbols UNINDEXED, "
                           "body UNINDEXED, path_tokens, symbol_tokens, body_tokens)")
        connection.commit()
    except Exception:
        connection.close()
        raise
    return connection


def refresh(db: sqlite3.Connection, root: Path, patterns: list[str]) -> dict[str, int]:
    paths = inventory(root)
    stats = dict(considered=len(paths), updated=0, unchanged=0, removed=0, skipped=0)
    db.execute("BEGIN IMMEDIATE")
    try:
        old = dict(db.execute("SELECT path, digest FROM files"))
        live = set()
        for path in paths:
            source = None if excluded(path, patterns) else read_source(root, path)
            if source is None:
                stats["skipped"] += 1
                continue
            text, digest = source
            live.add(path)
            if old.get(path) == digest:
                stats["unchanged"] += 1
                continue
            db.execute("DELETE FROM excerpts WHERE path = ?", (path,))
            db.executemany("INSERT INTO excerpts(path,start,end,symbols,body,path_tokens,symbol_tokens,body_tokens) "
                           "VALUES (?,?,?,?,?,?,?,?)",
                           [(path, *chunk) for chunk in chunks(path, text)])
            db.execute("INSERT OR REPLACE INTO files VALUES (?,?)", (path, digest))
            stats["updated"] += 1
        for path in old.keys() - live:
            db.execute("DELETE FROM excerpts WHERE path = ?", (path,))
            db.execute("DELETE FROM files WHERE path = ?", (path,))
            stats["removed"] += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return stats


def encoded(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def search(db: sqlite3.Connection, root: Path, query: str, stats: dict,
           max_bytes: int = 12_000, limit: int = 6) -> dict:
    if not 512 <= max_bytes <= 2_000_000 or not 1 <= limit <= 50 or len(query) > 1_024:
        raise ValueError("Require 512..2000000 bytes, 1..50 results, query <=1024 characters")
    words = list(dict.fromkeys(terms(query)))[:32]
    if not words:
        raise ValueError("Query must contain searchable words or identifiers")
    quoted = ['"' + word + '"' for word in words]
    strict = " AND ".join(quoted)
    relaxed = " OR ".join(quoted)
    sql = ("SELECT excerpts.rowid,excerpts.path,start,end,symbols,body,files.digest "
           "FROM excerpts JOIN files ON files.path=excerpts.path WHERE excerpts MATCH ? "
           "ORDER BY bm25(excerpts,0,0,0,0,0,8.0,12.0,1.0), excerpts.path, start LIMIT ?")
    strict_rows = db.execute(sql, (strict, limit * 12)).fetchall()
    rows = [(row, "all-terms") for row in strict_rows]
    if relaxed != strict:
        seen = {row[0] for row in strict_rows}
        rows.extend((row, "any-term") for row in db.execute(sql, (relaxed, limit * 12)).fetchall()
                    if row[0] not in seen)
    report = {"retrieval": "weighted-lexical-fts5", "query_terms": words,
              "budget_unit": "UTF-8 bytes",
              "stats": stats, "stale_hits": 0, "budget_exhausted": False, "results": []}
    counts: dict[str, int] = {}
    for row, match_mode in rows:
        _, path, start, end, symbols, body, digest = row
        if counts.get(path, 0) >= 2 or len(report["results"]) == limit:
            continue
        current = read_source(root, path)
        if current is None or current[1] != digest:
            report["stale_hits"] += 1
            continue
        item = {"path": path, "start": int(start), "end": int(end), "symbols": symbols,
                "match": match_mode,
                "sha256": current[1], "text": body, "truncated": False}
        report["results"].append(item)
        while len(encoded(report).encode("utf-8")) > max_bytes and item["text"]:
            report["budget_exhausted"] = True
            kept = item["text"].splitlines(keepends=True)[:-1]
            item.update(text="".join(kept), end=int(start) + len(kept) - 1, truncated=True)
        if not item["text"]:
            report["results"].pop()
        else:
            counts[path] = counts.get(path, 0) + 1
    if len(encoded(report).encode("utf-8")) > max_bytes:
        raise ValueError("Output metadata exceeds byte budget; increase --max-bytes")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--exclude", action="append", default=[],
                        help="additional case-sensitive whole-path fnmatch pattern; repeatable")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index")
    sub.add_parser("purge")
    query = sub.add_parser("search")
    query.add_argument("query")
    query.add_argument("--max-bytes", type=int, default=12_000)
    query.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    try:
        root, cache = locations(args.root)
        if args.command == "purge":
            if cache.is_symlink():
                raise ValueError("Refusing a symlink cache")
            # Do not purge while another invocation is running. No recursive deletion.
            for name in ("index.sqlite3", "index.sqlite3-journal", "index.sqlite3-wal", "index.sqlite3-shm"):
                (cache / name).unlink(missing_ok=True)
            print('{"purged":true}')
            return 0
        db = connect(cache, root)
        try:
            stats = refresh(db, root, args.exclude)
            report = search(db, root, args.query, stats, args.max_bytes, args.limit) if args.command == "search" else stats
            sys.stdout.write(encoded(report))
        finally:
            db.close()
        return 0
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(f"repo-index: {str(exc)[:600]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
