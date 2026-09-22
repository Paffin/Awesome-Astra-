#!/usr/bin/env python3
"""Check scoped acceptance coverage and existing execution receipts; never run commands.

Kinds and boundaries are reviewer declarations, not proof that a test asserts the
intended behavior. Checksums detect accidental drift, not malicious forgery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import verify_command

KINDS = {"entrypoint", "negative", "compatibility", "recovery", "concurrency",
         "replay", "failure", "denied-path", "security", "performance", "user-journey"}
RISKS = {"migration": {"compatibility", "recovery"},
         "concurrency": {"concurrency", "replay", "failure"},
         "security": {"denied-path"}, "external-contract": {"compatibility"},
         "performance": {"performance"}, "user-journey": {"user-journey"},
         "recovery": {"recovery", "failure"}}


def strings(value, field, allowed=None, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not isinstance(x, str) or not x.strip() for x in value)
            or len(set(value)) != len(value)
            or (allowed is not None and not set(value) <= set(allowed))):
        raise ValueError(f"invalid {field}")
    return set(value)


def plan_recorded(payload, root, plan_path, plan_hash):
    """Require exact plan bytes observed before and after each command."""
    for source_key, env_key in (("before", "environment_before"), ("after", "environment_after")):
        found = False
        try:
            relative = plan_path.relative_to(Path(root).resolve()).as_posix()
            found = payload.get(source_key, {}).get("files", {}).get(relative) == plan_hash
        except ValueError:
            pass
        declaration = payload.get(env_key, {}).get("declaration") or {}
        found |= any(item.get("resolved") == str(plan_path) and item.get("sha256") == plan_hash
                     for item in declaration.get("files", []))
        if not found:
            return False
    return True


def check(plan: dict, ledger: dict, root: Path, plan_path: Path | None = None) -> dict:
    errors, unresolved = [], []
    if plan_path is None:
        raise ValueError("acceptance plan path required to verify receipt provenance")
    plan_path = Path(plan_path).resolve(strict=True)
    raw_plan = plan_path.read_bytes()
    if json.loads(raw_plan) != plan:
        raise ValueError("plan file differs from supplied acceptance plan")
    plan_hash = hashlib.sha256(raw_plan).hexdigest()
    if plan.get("schema") != 1:
        raise ValueError("acceptance plan schema must be 1")
    if ledger.get("acceptance_plan_sha256") != verify_command.digest(plan):
        errors.append("missing or stale acceptance plan hash")
    criteria = plan.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("nonempty acceptance criteria required")
    definitions = {}
    for item in criteria:
        if not isinstance(item, dict):
            raise ValueError("criterion must be an object")
        cid, expected = item.get("id"), item.get("expected")
        if not isinstance(cid, str) or not cid.strip() or cid in definitions:
            raise ValueError("missing or duplicate criterion id")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"missing expected behavior: {cid}")
        required = strings(item.get("kinds"), f"criterion kinds: {cid}", KINDS, True)
        for risk in strings(item.get("risks", []), f"criterion risks: {cid}", RISKS):
            required |= RISKS[risk]
        if "performance" in required:
            maximum = item.get("max_duration_seconds")
            if type(maximum) not in (int, float) or not math.isfinite(maximum) or maximum <= 0:
                raise ValueError(f"positive finite command duration budget required: {cid}")
        definitions[cid] = (item, required)
    required_global = {"entrypoint"}
    for risk in strings(plan.get("risks", []), "plan risks", RISKS):
        required_global |= RISKS[risk]
    boundaries = plan.get("boundaries", [])
    if not isinstance(boundaries, list):
        raise ValueError("boundaries must be an array")
    boundary_ids = set()
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            raise ValueError("boundary must be an object")
        bid = boundary.get("id")
        if not isinstance(bid, str) or not bid.strip() or bid in boundary_ids:
            raise ValueError("missing or duplicate boundary id")
        boundary_ids.add(bid)
        strings(boundary.get("criteria"), f"boundary criteria: {bid}", definitions, True)
        if boundary.get("status") != "verified":
            unresolved.append(bid)
        elif not isinstance(boundary.get("evidence"), str) or not boundary["evidence"].strip():
            errors.append(f"missing boundary review evidence: {bid}")
    exceptions = plan.get("exceptions", [])
    if not isinstance(exceptions, list):
        raise ValueError("exceptions must be an array")
    # An exception is visible for a human review; it never turns missing checks green.
    if exceptions:
        errors.append("acceptance exceptions require separate review; gate remains incomplete")
    checks = ledger.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("nonempty checks required")
    covered = {cid: set() for cid in definitions}
    check_ids, all_kinds = set(), set()
    for item in checks:
        if not isinstance(item, dict):
            raise ValueError("check must be an object")
        check_id = item.get("id")
        if not isinstance(check_id, str) or not check_id.strip() or check_id in check_ids:
            raise ValueError("missing or duplicate check id")
        check_ids.add(check_id)
        refs = strings(item.get("criteria"), f"check criteria: {check_id}", definitions, True)
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError(f"unknown check kind: {check_id}")
        if item.get("passed") is not True or not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
            errors.append(f"failed or unevidenced check: {check_id}")
            continue
        try:
            receipt = item.get("receipt")
            if not isinstance(receipt, str) or not Path(receipt).is_absolute():
                raise ValueError("absolute receipt path required")
            result = verify_command.verify(root, Path(receipt))
            if not result["recorded_check_passed"]:
                errors.extend(f"{check_id}: {error}" for error in result["errors"])
                continue
            payload = json.loads(Path(receipt).read_text())["payload"]
            if not plan_recorded(payload, root, plan_path, plan_hash):
                raise ValueError("acceptance plan was not recorded before and after command")
            if kind == "performance":
                duration = payload["duration_seconds"]
                if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
                    raise ValueError("invalid recorded command duration")
                for cid in refs:
                    maximum = definitions[cid][0].get("max_duration_seconds")
                    if type(maximum) not in (int, float) or not math.isfinite(maximum) or maximum <= 0:
                        raise ValueError(f"missing criterion command duration budget: {cid}")
                    if duration > maximum:
                        raise ValueError(f"command duration exceeds budget: {cid}")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"{check_id}: {exc}")
            continue
        all_kinds.add(kind)
        for cid in refs:
            covered[cid].add(kind)
    for cid, (_, required) in definitions.items():
        for kind in sorted(required - covered[cid]):
            errors.append(f"missing recorded {kind} check for criterion: {cid}")
    for kind in sorted(required_global - all_kinds):
        errors.append(f"missing recorded {kind} check for plan")
    errors.extend(f"unresolved external boundary: {bid}" for bid in unresolved)
    return {"acceptance_gate_passed": not errors, "errors": errors,
            "unresolved": unresolved, "exceptions": exceptions,
            "claim": "Declared acceptance coverage and local receipt consistency only; "
                     "test semantics and boundary evidence require review; duration budgets measure "
                     "the whole command, not application latency; checksums are not signatures"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(json.loads(args.plan.read_text()), json.loads(args.ledger.read_text()), args.root, args.plan)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(2, f"acceptance: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["acceptance_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
