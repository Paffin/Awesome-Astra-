#!/usr/bin/env python3
"""Install one or more bundled skills into a local Codex skill directory."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills"


def available_skills() -> list[str]:
    return sorted(path.name for path in SOURCE.iterdir() if (path / "SKILL.md").is_file())


def install(name: str, destination: Path, force: bool) -> Path:
    source = SOURCE / name
    target = destination / name
    if not (source / "SKILL.md").is_file():
        raise ValueError(f"unknown skill: {name}")

    destination.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(f"target exists: {target}; use --force to back it up and replace it")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = destination / f"{name}.backup-{stamp}"
        if backup.exists():
            raise FileExistsError(f"backup already exists: {backup}")
        target.rename(backup)

    try:
        shutil.copytree(source, target)
    except Exception:
        backups = sorted(destination.glob(f"{name}.backup-*"), reverse=True)
        if backups and not target.exists():
            backups[0].rename(target)
        raise
    return target


def main() -> int:
    skills = available_skills()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", action="append", choices=skills, help="install only this skill; repeatable")
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="destination directory (default: $HOME/.agents/skills)",
    )
    parser.add_argument("--force", action="store_true", help="back up and replace an existing skill")
    args = parser.parse_args()

    selected = args.skill or skills
    for name in selected:
        target = install(name, args.dest.expanduser().resolve(), args.force)
        print(f"installed {name}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
