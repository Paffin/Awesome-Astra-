#!/usr/bin/env python3
"""Validate this pack's intentionally restricted skill format and eval cases."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAMES = {"astra-code", "astra-repo-audit"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    data = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line or line.startswith(" "):
            raise ValueError("use plain single-line name/description metadata in this pack")
        key, value = line.split(":", 1)
        if key in data:
            raise ValueError(f"duplicate metadata key: {key}")
        data[key] = value.strip().strip("\"'")
    return data


def validate_skill(skill: Path) -> list[str]:
    errors = []
    manifest = skill / "SKILL.md"
    try:
        meta = frontmatter(manifest)
    except (OSError, ValueError) as exc:
        return [f"{manifest}: {exc}"]
    if set(meta) != {"name", "description"}:
        errors.append(f"{manifest}: expected only name and description")
    if meta.get("name") != skill.name or not NAME_RE.fullmatch(meta.get("name", "")):
        errors.append(f"{manifest}: mismatched/invalid name")
    if not 1 <= len(meta.get("description", "")) <= 220:
        errors.append(f"{manifest}: description outside 1..220 characters")
    for markdown in [manifest, *sorted((skill / "references").glob("*.md"))]:
        text = markdown.read_text(encoding="utf-8")
        max_lines, max_bytes = (120, 4000) if markdown == manifest else (100, 6500)
        if len(text.splitlines()) > max_lines or len(text.encode("utf-8")) > max_bytes:
            errors.append(f"{markdown}: exceeds line/UTF-8 byte budget")
        for target in LINK_RE.findall(text):
            if target.startswith(("https://", "http://", "#")):
                continue
            resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
            if not resolved.is_relative_to(skill.resolve()) or not resolved.exists():
                errors.append(f"{markdown}: missing or escaping link: {target}")
    ui = skill / "agents/openai.yaml"
    if not ui.is_file() or f"${skill.name}" not in ui.read_text(encoding="utf-8"):
        errors.append(f"{skill}: missing UI metadata or explicit skill invocation")
    if any((skill / filename).exists() for filename in ("README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md")):
        errors.append(f"{skill}: user documentation belongs at repository root")
    return errors


def validate_evals() -> list[str]:
    errors = []
    seen = set()
    for path in sorted((ROOT / "evals").glob("*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                case = json.loads(line)
                identity = case.get("id")
                expect = case.get("expect", {})
                if not isinstance(identity, str) or not identity or identity in seen:
                    raise ValueError("missing/duplicate id")
                seen.add(identity)
                if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
                    raise ValueError("missing prompt")
                if expect.get("skill") not in NAMES | {None}:
                    raise ValueError("unknown skill")
                if expect.get("route") not in {"implement", "debug", "design", "review", "audit", None}:
                    raise ValueError("unknown route")
                for key in ("must", "must_not"):
                    if not isinstance(expect.get(key), list) or any(not isinstance(x, str) for x in expect[key]):
                        raise ValueError(f"{key} must be an array of assertions")
            except (ValueError, AttributeError, TypeError) as exc:
                errors.append(f"{path}:{number}: {exc}")
    if len(seen) < 10:
        errors.append("expected at least 10 behavior cases; these are specifications, not measured passes")
    return errors


def main() -> int:
    errors = []
    plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    if plugin.get("name") != "astra-codex-skills" or not re.fullmatch(r"\d+\.\d+\.\d+", plugin.get("version", "")):
        errors.append("invalid plugin identity/version")
    if plugin.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        errors.append("unexpected plugin schema")
    compatibility = ROOT / ".codex-plugin/plugin.json"
    try:
        codex_plugin = json.loads(compatibility.read_text(encoding="utf-8"))
        if codex_plugin != plugin:
            errors.append(".codex-plugin/plugin.json must match portable plugin.json")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid Codex compatibility manifest: {exc}")
    skills = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    if {p.name for p in skills} != NAMES:
        errors.append("expected exactly two non-overlapping skill entry points")
    for skill in skills:
        errors.extend(validate_skill(skill))
    errors.extend(validate_evals())
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated portable/Codex manifests and {len(skills)} skills; behavior outcomes are not evaluated here")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
