#!/usr/bin/env python3
"""Validate a reviewed integration ledger against a fresh impact report.

This validates evidence bookkeeping, not truth of reviewer claims or model quality.
Never executes commands from the ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def check(report: dict, ledger: dict) -> dict:
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
    for key in ("missing_paths", "parse_errors", "dynamic_files", "unsupported_files", "unresolved_imports"):
        if report.get(key):
            review = ledger.get("coverage_review", {}).get(key)
            if not isinstance(review, dict) or review.get("resolved") is not True or not review.get("evidence"):
                errors.append(f"unreviewed coverage gap: {key}")
    return {"ledger_gate_passed": not errors, "errors": errors,
            "claim": "Reviewed ledger completeness only; not independent proof of whole-project correctness"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        result = check(json.loads(args.report.read_text()), json.loads(args.ledger.read_text()))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(2, f"integration-check: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["ledger_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
