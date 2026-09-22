#!/usr/bin/env python3
"""Report available context tools without starting servers or installing anything."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path


def inspect(server_commands: list[str]) -> dict:
    # Server names come from the caller: protocol support has no language allowlist.
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE VIRTUAL TABLE probe USING fts5(content)")
        fts5 = True
    except sqlite3.Error:
        fts5 = False
    finally:
        db.close()
    scripts = Path(__file__).resolve().parent
    required = ["repo_index.py", "project_map.py", "project_context.py",
                "lsp_context.py", "verify_command.py", "check_integration.py"]
    missing = [name for name in required if not (scripts / name).is_file()]
    git = shutil.which("git")
    return {"python": sys.version.split()[0], "git": git, "sqlite_fts5": fts5,
            "missing_bundled_tools": missing,
            "ready": sys.version_info >= (3, 10) and bool(git) and fts5 and not missing,
            "servers": [{"command": name, "executable": shutil.which(name),
                         "references_verified": False} for name in server_commands],
            "limitations": ["Executable discovery does not test server compatibility or indexing readiness",
                            "Host model selection and skill activation are not inspected",
                            "No executable discovered here has been run"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-command", action="append", default=[])
    args = parser.parse_args()
    report = inspect(args.server_command)
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
