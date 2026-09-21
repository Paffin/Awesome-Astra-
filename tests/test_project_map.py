from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/astra-code/scripts"
sys.path.insert(0, str(SCRIPTS))
import project_map as mapping
import repo_index as index


class MapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        _, cache = index.locations(self.root)
        self.db = index.connect(cache, self.root)
        self.addCleanup(self.db.close)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def build(self, roots=None):
        return mapping.build(self.db, self.root, [], roots or ["."])

    def test_alias_and_transitive_consumers(self):
        self.write("core.py", "def send():\n    return 1\n")
        self.write("worker.py", "from core import send as publish\npublish()\n")
        self.write("cli.py", "import worker as job\n")
        result = mapping.impact(self.build(), ["core.py"])
        self.assertEqual(result["affected_candidates"], ["cli.py", "core.py", "worker.py"])
        self.assertFalse(result["whole_project_verified"])

    def test_relative_import_and_explicit_src_root(self):
        self.write("src/pkg/__init__.py", "from .core import send\n")
        self.write("src/pkg/core.py", "def send():\n    pass\n")
        self.write("src/pkg/worker.py", "from . import core\n")
        result = mapping.impact(self.build(["src"]), ["src/pkg/core.py"])
        self.assertEqual(len(result["affected_candidates"]), 3)

    def test_normalized_changed_path_keeps_consumers(self):
        self.write("core.py", "value=1\n")
        self.write("cli.py", "import core\n")
        result = mapping.impact(self.build(), ["./core.py"])
        self.assertEqual(result["affected_candidates"], ["cli.py", "core.py"])

    def test_parent_package_does_not_hide_missing_module(self):
        self.write("pkg/__init__.py", "value=1\n")
        self.write("cli.py", "import pkg.missing\n")
        report = self.build()
        self.assertEqual(report["unresolved_imports"][0]["module"], "pkg.missing")
        self.assertTrue(report["edges"])

    def test_reuse_and_invalidation(self):
        self.write("core.py", "value=1\n")
        first = self.build()
        second = self.build()
        self.assertEqual(second["stats"]["parsed"], 0)
        self.assertEqual(second["stats"]["reused"], 1)
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.write("core.py", "value=2\n")
        self.assertNotEqual(first["snapshot_sha256"], self.build()["snapshot_sha256"])
        (self.root / "core.py").unlink()
        self.assertEqual(self.build()["facts"], {})
        self.assertEqual(self.db.execute("SELECT count(*) FROM map_facts").fetchone()[0], 0)

    def test_unknowns_are_explicit(self):
        self.write("main.py", "from missing import *\ngetattr(object(), 'run')\n")
        self.write("broken.py", "def invalid(\n")
        self.write("client.ts", "export const call = 1;\n")
        result = mapping.impact(self.build(), ["main.py"])
        self.assertTrue(result["unresolved_imports"])
        self.assertEqual(result["parse_errors"], ["broken.py"])
        self.assertEqual(result["dynamic_files"], ["main.py"])
        self.assertEqual(result["unsupported_files"], ["client.ts"])

    def test_ignores_sensitive_files_and_never_executes_source(self):
        self.write("main.py", "raise RuntimeError('must not execute')\n")
        self.write(".env", "SECRET=value\n")
        self.assertEqual(list(self.build()["files"]), ["main.py"])

    def test_cli_and_budget_fail_closed(self):
        self.write("core.py", "value=1\n")
        command = [sys.executable, str(SCRIPTS / "project_map.py"), "--root", str(self.root)]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        run = subprocess.run(command + ["--max-bytes", "512"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")


if __name__ == "__main__":
    unittest.main()
