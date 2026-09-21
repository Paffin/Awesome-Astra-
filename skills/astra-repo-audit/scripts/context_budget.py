#!/usr/bin/env python3
"""Inventory Codex instruction files and estimate their context footprint."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
MAX_FILE_BYTES = 1_048_576


def estimated_tokens(text: str) -> int:
    """Return a transparent, tokenizer-free estimate."""
    return math.ceil(len(text.encode("utf-8")) / 4)


def skill_description(text: str) -> str:
    if not text.startswith("---"):
        return ""
    lines = text.splitlines()
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def kind_for(path: Path) -> str | None:
    if path.name == "AGENTS.md":
        return "agents"
    if path.name == "SKILL.md" and any(part in {"skills", ".skills"} for part in path.parts):
        return "skill"
    if path.name == "config.toml" and ".codex" in path.parts:
        return "config"
    return None


def discover(root: Path) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".cache"))
        base = Path(current)
        for filename in sorted(files):
            path = base / filename
            if not path.is_symlink() and kind_for(path) is not None:
                found.append(path)
    return sorted(found)


def inspect(path: Path, root: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        return {
            "path": path.relative_to(root).as_posix(),
            "kind": kind_for(path),
            "bytes": size,
            "skipped": "larger than 1 MiB",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    record: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "kind": kind_for(path),
        "bytes": size,
        "lines": len(text.splitlines()),
        "estimated_tokens": estimated_tokens(text),
    }
    if record["kind"] == "skill":
        description = skill_description(text)
        record["description_words"] = len(description.split())
        record["catalog_estimated_tokens"] = estimated_tokens(description)
    return record


def build_report(root: Path) -> dict[str, Any]:
    records = [inspect(path, root) for path in discover(root)]
    measured = [record for record in records if "estimated_tokens" in record]
    return {
        "root": str(root),
        "method": "estimated_tokens = ceil(UTF-8 bytes / 4); not tokenizer or billing data",
        "files": records,
        "totals": {
            "files": len(records),
            "bytes": sum(record.get("bytes", 0) for record in records),
            "estimated_tokens": sum(record["estimated_tokens"] for record in measured),
            "skill_catalog_estimated_tokens": sum(
                record.get("catalog_estimated_tokens", 0) for record in measured
            ),
        },
    }


def render_text(report: dict[str, Any]) -> str:
    rows = ["kind\ttokens\tbytes\tpath"]
    for record in report["files"]:
        rows.append(
            f"{record.get('kind', '-')}\t{record.get('estimated_tokens', '-')}\t"
            f"{record.get('bytes', '-')}\t{record['path']}"
        )
    totals = report["totals"]
    rows.extend(
        [
            "",
            f"files: {totals['files']}",
            f"bytes: {totals['bytes']}",
            f"estimated tokens if all file bodies were loaded: {totals['estimated_tokens']}",
            f"estimated skill catalog tokens: {totals['skill_catalog_estimated_tokens']}",
            f"method: {report['method']}",
        ]
    )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    report = build_report(root)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
