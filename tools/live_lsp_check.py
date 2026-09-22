#!/usr/bin/env python3
"""Opt-in real-server smoke test. Never installs a language server."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/astra-code/scripts"))
from lsp_context import query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=["python", "typescript"], required=True)
    parser.add_argument("--server", required=True, help="JSON argv using absolute executable path")
    args = parser.parse_args()
    command = json.loads(args.server)
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        parser.error("server must be nonempty string array")
    suffix, column = ("py", 5) if args.language == "python" else ("ts", 17)
    with tempfile.TemporaryDirectory(prefix="astra-live-lsp-") as raw:
        root = Path(raw).resolve()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for name in (f"core.{suffix}", f"consumer.{suffix}"):
            shutil.copyfile(ROOT / "tests/fixtures/live_lsp" / name, root / name)
        if suffix == "ts":
            shutil.copyfile(ROOT / "tests/fixtures/live_lsp/tsconfig.json", root / "tsconfig.json")
        report = query(root, f"core.{suffix}", 1, column, args.language, command,
                       open_files=[f"consumer.{suffix}"])
        paths = {r["path"] for r in report["references"]}
        if not {f"core.{suffix}", f"consumer.{suffix}"} <= paths:
            raise SystemExit("FAIL: real server did not return definition and cross-file consumer")
        print(json.dumps({"language": args.language, "passed": True,
                          "references": report["references"], "opened_files": report["opened_files"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
