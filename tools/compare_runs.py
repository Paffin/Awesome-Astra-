#!/usr/bin/env python3
"""Compare paired, externally measured runs. Does not execute or grade a model."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

SETUP = {"model", "harness", "repo_revision", "environment", "reasoning_effort", "cache_state"}
COUNTS = ("input_tokens", "cached_input_tokens", "output_tokens")


def compare(records: list[dict]) -> dict:
    pairs: dict[tuple[str, int], dict[str, dict]] = {}
    runs = set()
    for row in records:
        for key in ("run_id", "task_id", "evidence"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"missing nonempty {key}")
        if row["run_id"] in runs:
            raise ValueError("duplicate run_id")
        runs.add(row["run_id"])
        if type(row.get("repeat")) is not int or row["repeat"] < 0:
            raise ValueError("repeat must be a nonnegative integer")
        if row.get("variant") not in {"baseline", "candidate"}:
            raise ValueError("variant must be baseline or candidate")
        setup = row.get("setup")
        if not isinstance(setup, dict) or set(setup) != SETUP or any(not isinstance(v, str) or not v.strip() for v in setup.values()):
            raise ValueError(f"setup must specify {sorted(SETUP)}")
        for key in COUNTS:
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError(f"{key} must be a nonnegative integer, not an estimate or null")
        if row["cached_input_tokens"] > row["input_tokens"]:
            raise ValueError("cached input is a subset of input, not an additional count")
        elapsed = row.get("elapsed_seconds")
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError("elapsed_seconds must be finite and positive")
        if any(type(row.get(k)) is not bool for k in ("accepted", "safety_passed")):
            raise ValueError("accepted and safety_passed must be explicit booleans")
        pair = pairs.setdefault((row["task_id"], row["repeat"]), {})
        if row["variant"] in pair:
            raise ValueError("duplicate task/repeat/variant")
        pair[row["variant"]] = row
    if not pairs:
        raise ValueError("no measured runs supplied")
    for pair in pairs.values():
        if set(pair) != {"baseline", "candidate"}:
            raise ValueError("unpaired runs; do not silently drop failed or missing runs")
        if pair["baseline"]["setup"] != pair["candidate"]["setup"]:
            raise ValueError("mismatched setup within a pair")
    def totals(variant):
        rows = [p[variant] for p in pairs.values()]
        counts = {k: sum(r[k] for r in rows) for k in COUNTS}
        accepted = sum(r["accepted"] and r["safety_passed"] for r in rows)
        total = counts["input_tokens"] + counts["output_tokens"]
        return {**counts, "total_tokens": total, "accepted_safe": accepted,
                "safety_failures": sum(not r["safety_passed"] for r in rows),
                "tokens_per_accepted_safe_task": total / accepted if accepted else None,
                "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rows)}
    regressions = [f"{task}:{repeat}" for (task, repeat), p in pairs.items()
                   if p["baseline"]["accepted"] and p["baseline"]["safety_passed"]
                   and not (p["candidate"]["accepted"] and p["candidate"]["safety_passed"])]
    result = {"pairs": len(pairs), "baseline": totals("baseline"), "candidate": totals("candidate"),
              "observed_quality_regressions": regressions,
              "claim": "Descriptive paired results; not proof of population-level improvement."}
    result["observed_gate_passed"] = not regressions and result["candidate"]["safety_failures"] == 0 and result["candidate"]["accepted_safe"] > 0
    result["median_paired_elapsed_delta_seconds"] = statistics.median(
        p["candidate"]["elapsed_seconds"] - p["baseline"]["elapsed_seconds"] for p in pairs.values())
    result["heterogeneous_setups"] = len({json.dumps(p["baseline"]["setup"], sort_keys=True) for p in pairs.values()}) > 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, help="JSONL; every task/repetition needs both variants")
    args = parser.parse_args()
    try:
        records = [json.loads(line) for line in args.runs.read_text(encoding="utf-8").splitlines() if line.strip()]
        result = compare(records)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(2, f"compare-runs: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["observed_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
