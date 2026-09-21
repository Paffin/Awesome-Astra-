#!/usr/bin/env python3
"""Validate plugin structure, skills, links, budgets, and eval fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
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
    data: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def validate_skill(skill: Path) -> list[str]:
    errors: list[str] = []
    manifest = skill / "SKILL.md"
    if not manifest.is_file():
        return [f"{skill}: missing SKILL.md"]
    try:
        meta = frontmatter(manifest)
    except ValueError as exc:
        return [f"{manifest}: {exc}"]

    if set(meta) != {"name", "description"}:
        errors.append(f"{manifest}: frontmatter must contain only name and description")
    name = meta.get("name", "")
    description = meta.get("description", "")
    if name != skill.name or not NAME_RE.fullmatch(name):
        errors.append(f"{manifest}: invalid or mismatched name {name!r}")
    if not description or len(description) > 220:
        errors.append(f"{manifest}: description must be 1..220 characters")
    if len(manifest.read_text(encoding="utf-8").splitlines()) > 120:
        errors.append(f"{manifest}: root skill exceeds 120 lines")

    for markdown in [manifest, *sorted((skill / "references").glob("*.md"))] if (skill / "references").exists() else [manifest]:
        if markdown != manifest and len(markdown.read_text(encoding="utf-8").splitlines()) > 100:
            errors.append(f"{markdown}: reference exceeds 100 lines")
        for target in LINK_RE.findall(markdown.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#")):
                continue
            resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                errors.append(f"{markdown}: broken link {target}")

    ui = skill / "agents" / "openai.yaml"
    if not ui.is_file():
        errors.append(f"{skill}: missing agents/openai.yaml")
    else:
        ui_text = ui.read_text(encoding="utf-8")
        if f"${name}" not in ui_text:
            errors.append(f"{ui}: default prompt must mention ${name}")
    if any((skill / filename).exists() for filename in ("README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md")):
        errors.append(f"{skill}: user documentation belongs at repository root")
    return errors


def validate_evals() -> list[str]:
    errors: list[str] = []
    path = ROOT / "evals" / "cases.jsonl"
    seen: set[str] = set()
    routes = {"implement", "debug", "review", "design", "audit", None}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{number}: {exc}")
            continue
        case_id = case.get("id")
        if not case_id or case_id in seen:
            errors.append(f"{path}:{number}: missing or duplicate id")
        seen.add(case_id)
        if case.get("expect", {}).get("route") not in routes:
            errors.append(f"{path}:{number}: unknown route")
    if len(seen) < 10:
        errors.append(f"{path}: expected at least 10 cases")
    return errors


def main() -> int:
    errors: list[str] = []
    plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    if plugin.get("name") != "astra-codex-skills" or not plugin.get("version"):
        errors.append("plugin.json: missing stable name or version")

    skill_dirs = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    if [path.name for path in skill_dirs] != ["astra-code", "astra-repo-audit"]:
        errors.append("skills/: expected astra-code and astra-repo-audit only")
    for skill in skill_dirs:
        errors.extend(validate_skill(skill))
    errors.extend(validate_evals())

    if errors:
        print("validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"validated plugin and {len(skill_dirs)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
