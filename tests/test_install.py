from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("install_skills", MODULE_PATH)
assert SPEC and SPEC.loader
install_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_skills)


class InstallTests(unittest.TestCase):
    def test_installs_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw)
            target = install_skills.install("astra-code", destination, force=False)
            self.assertTrue((target / "SKILL.md").is_file())
            with self.assertRaises(FileExistsError):
                install_skills.install("astra-code", destination, force=False)

    def test_force_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw)
            target = destination / "astra-code"
            target.mkdir()
            (target / "marker.txt").write_text("old", encoding="utf-8")

            install_skills.install("astra-code", destination, force=True)

            backups = list(destination.glob("astra-code.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "marker.txt").read_text(encoding="utf-8"), "old")
            self.assertTrue((target / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
