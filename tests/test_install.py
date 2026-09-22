from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_skills", ROOT / "scripts/install.py")
install_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_skills)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destination = Path(self.tmp.name) / "skills"

    def test_installs_and_refuses_overwrite(self):
        target = install_skills.install("astra-code", self.destination, False)
        self.assertTrue((target / "SKILL.md").is_file())
        with self.assertRaises(FileExistsError):
            install_skills.install("astra-code", self.destination, False)

    def test_installed_runtime_is_self_contained(self):
        target = install_skills.install("astra-code", self.destination, False)
        unrelated = Path(self.tmp.name) / "unrelated"
        unrelated.mkdir()
        report = subprocess.run([sys.executable, str(target / "scripts/doctor.py"),
                                 "--server-command", "astra-test-missing-server"],
                                cwd=unrelated, capture_output=True, text=True, timeout=10)
        self.assertEqual(report.returncode, 0, report.stderr)
        data = json.loads(report.stdout)
        self.assertTrue(data["ready"])
        self.assertIsNone(data["servers"][0]["executable"])
        self.assertFalse(data["servers"][0]["references_verified"])
        for name in ("verify_command.py", "project_context.py", "check_integration.py", "acceptance.py"):
            result = subprocess.run([sys.executable, str(target / "scripts" / name), "--help"],
                                    cwd=unrelated, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_force_creates_backup_outside_discovery(self):
        target = install_skills.install("astra-code", self.destination, False)
        (target / "marker.txt").write_text("old")
        install_skills.install("astra-code", self.destination, True)
        backups = list(install_skills.backup_directory(self.destination).glob("astra-code.backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "marker.txt").read_text(), "old")
        self.assertEqual(len(list(self.destination.rglob("SKILL.md"))), 1)

    def test_failed_partial_copy_leaves_original_untouched(self):
        target = install_skills.install("astra-code", self.destination, False)
        (target / "marker.txt").write_text("old")
        def fail(source, target, **kwargs):
            target.mkdir()
            (target / "partial").write_text("partial")
            raise OSError("disk full")
        with patch.object(install_skills.shutil, "copytree", side_effect=fail):
            with self.assertRaises(OSError):
                install_skills.install("astra-code", self.destination, True)
        self.assertEqual((target / "marker.txt").read_text(), "old")
        self.assertEqual(list(self.destination.parent.glob(".astra-stage-*")), [])
        self.assertEqual(list(self.destination.parent.glob("*.lock")), [])

    def test_failed_publication_restores_exact_backup(self):
        target = install_skills.install("astra-code", self.destination, False)
        (target / "marker.txt").write_text("old")
        original_rename = Path.rename
        def fail_staging(path, target):
            if path.parent.name.startswith(".astra-stage-"):
                raise OSError("rename failed")
            return original_rename(path, target)
        with patch.object(Path, "rename", fail_staging):
            with self.assertRaises(OSError):
                install_skills.install("astra-code", self.destination, True)
        self.assertEqual((target / "marker.txt").read_text(), "old")

    def test_repeated_force_has_unique_backups(self):
        install_skills.install("astra-code", self.destination, False)
        install_skills.install("astra-code", self.destination, True)
        install_skills.install("astra-code", self.destination, True)
        self.assertEqual(len(list(install_skills.backup_directory(self.destination).iterdir())), 2)

    def test_traversal_and_source_overwrite_rejected(self):
        with self.assertRaises(ValueError):
            install_skills.install("../astra-code", self.destination, False)
        with self.assertRaises(ValueError):
            install_skills.install("astra-code", install_skills.SOURCE, True)

    def test_symlink_target_is_backed_up_without_following(self):
        external = self.destination.parent / "external"
        external.mkdir()
        (external / "marker").write_text("keep")
        self.destination.mkdir()
        (self.destination / "astra-code").symlink_to(external, target_is_directory=True)
        install_skills.install("astra-code", self.destination, True)
        self.assertEqual((external / "marker").read_text(), "keep")
        self.assertFalse((self.destination / "astra-code").is_symlink())


if __name__ == "__main__":
    unittest.main()
