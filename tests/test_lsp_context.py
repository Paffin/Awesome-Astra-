import io
import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/astra-code/scripts"))
import lsp_context as lsp


class LSPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "code.txt").write_text("a😀symbol\n", encoding="utf-8")

    def query(self, mode="normal", **kwargs):
        return lsp.query(self.root, "code.txt", 1, 3, "arbitrary-language",
            [sys.executable, str(ROOT / "tests/fixtures/lsp_server.py"), mode], **kwargs)

    def test_references_and_external_gap(self):
        report = self.query()
        self.assertEqual(report["references"][0]["path"], "code.txt")
        self.assertEqual(report["unresolved_locations"], 1)
        self.assertFalse(report["whole_project_verified"])

    def test_utf16_position(self):
        self.assertEqual(self.query("utf16")["references"][0]["range"]["start"]["character"], 3)

    def test_missing_capability(self):
        with self.assertRaisesRegex(ValueError, "advertise"):
            self.query("unsupported")

    def test_server_error(self):
        with self.assertRaisesRegex(ValueError, "fixture error"):
            self.query("error")

    def test_timeout(self):
        with self.assertRaises(TimeoutError):
            self.query("timeout", timeout=.2)

    def test_blocked_write_is_bounded(self):
        (self.root / "code.txt").write_text("abc\n" * 50000)
        with self.assertRaisesRegex(TimeoutError, "write timeout"):
            self.query("blocked-write", timeout=.2)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_inherited_pipe_cleanup(self):
        command = [sys.executable, str(ROOT / "skills/astra-code/scripts/lsp_context.py"),
                   "--root", str(self.root), "--file", "code.txt", "--line", "1", "--column", "1",
                   "--language", "text", "--server", json.dumps([sys.executable,
                   str(ROOT / "tests/fixtures/lsp_server.py"), "inherited-pipe"])]
        run = subprocess.run(command, capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_truncated_frame(self):
        with self.assertRaises(EOFError):
            lsp.read_message(io.BytesIO(b"Content-Length: 20\r\n\r\n{}"))

    def test_oversized_frame(self):
        with self.assertRaises(ValueError):
            lsp.read_message(io.BytesIO(b"Content-Length: 99999999\r\n\r\n"))

    def test_installed_skill_tools_are_self_contained(self):
        destination = self.root / "installed"
        run = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--skill", "astra-code",
                              "--dest", str(destination)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        for tool in ("lsp_context.py", "check_integration.py", "project_map.py", "repo_index.py"):
            run = subprocess.run([sys.executable, str(destination / "astra-code/scripts" / tool), "--help"],
                                 cwd=self.root, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, f"{tool}: {run.stderr}")
