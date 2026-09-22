#!/usr/bin/env python3
"""Validate a reviewed integration ledger against a fresh impact report.

Validates bookkeeping and optionally local execution receipts. Neither mode
authenticates reviewer claims or proves model quality.
Never executes commands from the ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def check(report: dict, ledger: dict, root: Path | None = None, require_recorded: bool = False) -> dict:
    errors = []
    snapshot = report.get("snapshot_sha256")
    if not isinstance(snapshot, str) or not snapshot or ledger.get("snapshot_sha256") != snapshot:
        errors.append("missing or stale snapshot")
    affected = report.get("affected_candidates")
    if not isinstance(affected, list) or not affected or any(not isinstance(p, str) for p in affected):
        raise ValueError("report requires nonempty affected_candidates")
    entries = ledger.get("consumers", {})
    if not isinstance(entries, dict):
        raise ValueError("consumers must be an object keyed by path")
    for path in affected:
        entry = entries.get(path)
        if not isinstance(entry, dict) or entry.get("disposition") not in {"changed", "compatible", "not-applicable"}:
            errors.append(f"unresolved consumer: {path}")
        elif not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
            errors.append(f"missing consumer evidence: {path}")
    checks = ledger.get("checks", [])
    if not isinstance(checks, list) or not checks:
        errors.append("missing acceptance checks")
    elif any(not isinstance(c, dict) or c.get("passed") is not True or
             not isinstance(c.get("evidence"), str) or not c["evidence"].strip() for c in checks):
        errors.append("failed or unevidenced acceptance check")
    if not isinstance(checks, list) or not any(isinstance(c, dict) and c.get("kind") == "entrypoint" and c.get("passed") is True
               for c in checks):
        errors.append("missing real entrypoint check")
    for key in ("missing_paths", "parse_errors", "dynamic_files", "unsupported_files", "unresolved_imports", "contract_gaps"):
        if report.get(key):
            review = ledger.get("coverage_review", {}).get(key)
            if not isinstance(review, dict) or review.get("resolved") is not True or not review.get("evidence"):
                errors.append(f"unreviewed coverage gap: {key}")
    if require_recorded:
        if root is None:
            errors.append("recorded checks require repository root")
        elif isinstance(checks, list):
            import sys
            script_dir = str(Path(__file__).resolve().parent)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            import verify_command
            files, exclude = report.get("files"), report.get("exclude")
            if (not isinstance(files, dict) or not isinstance(exclude, list)
                    or any(not isinstance(p, str) for p in exclude)):
                errors.append("impact report lacks source inventory provenance")
            elif verify_command.snapshot(verify_command.repo_index.locations(Path(root))[0], exclude)["files"] != files:
                errors.append("impact report source inventory is stale")
            for number, item in enumerate(checks):
                try:
                    receipt = item.get("receipt") if isinstance(item, dict) else None
                    if not isinstance(receipt, str) or not Path(receipt).is_absolute():
                        raise ValueError("absolute receipt path required")
                    result = verify_command.verify(root, Path(receipt))
                    errors.extend(f"check {number}: {message}" for message in result["errors"])
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    errors.append(f"check {number}: {exc}")
    return {"ledger_gate_passed": not errors, "errors": errors,
            "claim": ("Reviewed ledger and local execution receipt consistency; not authenticated proof of correctness"
                      if require_recorded else "Reviewed ledger completeness only; not independent proof of whole-project correctness")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--require-recorded", action="store_true")
    args = parser.parse_args()
    try:
        result = check(json.loads(args.report.read_text()), json.loads(args.ledger.read_text()), args.root, args.require_recorded)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(2, f"integration-check: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["ledger_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
