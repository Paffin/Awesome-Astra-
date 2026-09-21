#!/usr/bin/env python3
"""Install reviewed local skills; stage first and keep backups outside discovery."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills"


def available_skills() -> list[str]:
    return sorted(p.name for p in SOURCE.iterdir()
                  if not p.is_symlink() and (p / "SKILL.md").is_file())


def backup_directory(destination: Path) -> Path:
    identity = hashlib.sha256(str(destination.resolve()).encode()).hexdigest()[:12]
    return destination.resolve().parent / ".astra-skill-backups" / identity


def install(name: str, destination: Path, force: bool) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name not in available_skills():
        raise ValueError(f"unknown skill: {name}")
    source = SOURCE / name
    destination = destination.expanduser().resolve()
    if destination == SOURCE.resolve() or SOURCE.resolve() in destination.parents:
        raise ValueError("Refusing to install over bundled sources")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Bundled skill contains symlinks; review it before installation")
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = destination / name
    backup_root = backup_directory(destination)
    lock = destination.parent / f".astra-install-{backup_root.name}-{name}.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    backup: Path | None = None
    try:
        if (target.exists() or target.is_symlink()) and not force:
            raise FileExistsError(f"target exists: {target}; use --force for a backed-up replacement")
        with tempfile.TemporaryDirectory(prefix=".astra-stage-", dir=destination.parent) as staging:
            staged = Path(staging) / name
            # Complete the copy before touching the installed skill.
            shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            destination.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                if backup_root.is_symlink() or backup_root.parent.is_symlink():
                    raise ValueError("Refusing a symlink backup directory")
                backup_root.mkdir(parents=True, exist_ok=True)
                backup = backup_root / f"{name}.backup-{uuid.uuid4().hex}"
                target.rename(backup)
            try:
                staged.rename(target)
            except Exception:
                if backup is not None and not (target.exists() or target.is_symlink()):
                    backup.rename(target)
                raise
    finally:
        lock.unlink(missing_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", action="append", choices=available_skills())
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--force", action="store_true", help="back up and replace existing skills")
    args = parser.parse_args()
    try:
        for name in dict.fromkeys(args.skill or available_skills()):
            print(f"installed {name}: {install(name, args.dest, args.force)}")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"install: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
