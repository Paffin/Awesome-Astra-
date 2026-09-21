from __future__ import annotations

import hashlib
import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/astra-code/scripts/repo_index.py"
SPEC = importlib.util.spec_from_file_location("repo_index", SCRIPT)
index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(index)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        root, cache = index.locations(self.root)
        self.root = root
        self.db = index.connect(cache, root)
        self.addCleanup(self.db.close)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def search(self, query, **kwargs):
        stats = index.refresh(self.db, self.root, [])
        return index.search(self.db, self.root, query, stats, **kwargs)

    def test_python_symbols_and_exact_source_ranges(self):
        text = '"""Module."""\n\ndef processInvoice(value):\n    return value + 1\n'
        self.write("billing/payments.py", text)
        result = self.search("process invoice")["results"][0]
        self.assertEqual(result["path"], "billing/payments.py")
        self.assertIn("processInvoice", result["symbols"])
        self.assertEqual(result["text"], "".join(text.splitlines(keepends=True)[result["start"]-1:result["end"]]))
        self.assertEqual(result["sha256"], hashlib.sha256(text.encode()).hexdigest())

    def test_common_language_declarations_create_symbol_chunks(self):
        fixtures = {
            "web/checkout.ts": "export async function processInvoice(id: string) {\n  return id;\n}\n",
            "worker/main.go": "package worker\n\nfunc ProcessInvoice(id string) string {\n return id\n}\n",
            "core/lib.rs": "pub fn process_invoice(id: &str) -> &str {\n    id\n}\n",
            "api/Invoice.java": "public class InvoiceProcessor {\n}\n",
        }
        for path, text in fixtures.items():
            self.write(path, text)
        report = self.search("process invoice", limit=8)
        by_path = {item["path"]: item for item in report["results"]}
        self.assertIn("processInvoice", by_path["web/checkout.ts"]["symbols"])
        self.assertIn("ProcessInvoice", by_path["worker/main.go"]["symbols"])
        self.assertIn("process_invoice", by_path["core/lib.rs"]["symbols"])
        self.assertIn("InvoiceProcessor", by_path["api/Invoice.java"]["symbols"])

    def test_all_terms_rank_before_relaxed_fallback(self):
        self.write("exact.py", "def retry_invoice():\n    pass\n")
        self.write("partial.py", "def retry_job():\n    pass\n")
        report = self.search("retry invoice", limit=4)
        self.assertEqual(report["results"][0]["path"], "exact.py")
        self.assertEqual(report["results"][0]["match"], "all-terms")
        self.assertTrue(any(item["path"] == "partial.py" and item["match"] == "any-term"
                            for item in report["results"]))

    def test_unchanged_files_are_not_reindexed(self):
        self.write("a.py", "value = 1\n")
        self.assertEqual(self.search("value")["stats"]["updated"], 1)
        report = self.search("value")
        self.assertEqual(report["stats"]["updated"], 0)
        self.assertEqual(report["stats"]["unchanged"], 1)

    def test_same_mtime_and_size_change_is_detected(self):
        path = self.write("a.py", "value = 1\n")
        self.search("value")
        old = path.stat()
        self.write("a.py", "value = 2\n")
        os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
        report = self.search("value")
        self.assertEqual(report["stats"]["updated"], 1)
        self.assertIn("value = 2", report["results"][0]["text"])

    def test_deleted_file_is_evicted(self):
        path = self.write("a.py", "obsolete = 1\n")
        self.search("obsolete")
        path.unlink()
        report = self.search("obsolete")
        self.assertEqual(report["results"], [])
        self.assertEqual(report["stats"]["removed"], 1)

    def test_new_ignore_evicts_previously_tracked_file(self):
        self.write("tracked.txt", "sensitive_marker\n")
        subprocess.run(["git", "-C", str(self.root), "add", "tracked.txt"], check=True)
        self.search("sensitive_marker")
        self.write(".gitignore", "tracked.txt\nignored/\n")
        self.write("ignored/a.txt", "sensitive_marker\n")
        self.assertEqual(self.search("sensitive_marker")["results"], [])

    def test_secrets_binary_large_minified_and_vendor_are_skipped(self):
        for path in (".env", ".env.example", "private.key", "node_modules/x.js", ".npmrc"):
            self.write(path, "uniquecredentialmarker\n")
        self.write("binary.dat", "\0uniquecredentialmarker")
        self.write("huge.txt", "x" * (index.MAX_FILE_BYTES + 1))
        self.write("minified.js", "uniquecredentialmarker" + "x" * 8001)
        self.write("accidental.txt", "-----BEGIN RSA PRIVATE KEY-----\nuniquecredentialmarker\n")
        self.write("secrets.yaml", "token: uniquecredentialmarker\n")
        self.write("state/terraform.tfstate", "uniquecredentialmarker\n")
        self.write("slack.txt", "xoxb-12345678901234567890\nuniquecredentialmarker\n")
        self.write("openai.txt", "sk-proj-12345678901234567890\nuniquecredentialmarker\n")
        self.assertEqual(self.search("uniquecredentialmarker")["results"], [])

    def test_symlink_file_and_parent_are_not_read(self):
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside)
            (other / "x.txt").write_text("outsideuniquemarker")
            (self.root / "escape.txt").symlink_to(other / "x.txt")
            (self.root / "escape-dir").symlink_to(other, target_is_directory=True)
            self.assertIsNone(index.read_source(self.root, "escape-dir/x.txt"))
            self.assertEqual(self.search("outsideuniquemarker")["results"], [])

    def test_source_changed_after_scan_is_not_returned(self):
        self.write("a.txt", "olduniquemarker\n")
        stats = index.refresh(self.db, self.root, [])
        self.write("a.txt", "newuniquemarker\n")
        report = index.search(self.db, self.root, "olduniquemarker", stats)
        self.assertEqual(report["results"], [])
        self.assertEqual(report["stale_hits"], 1)

    def test_unicode_and_spaces_roundtrip(self):
        self.write("папка/my module.py", "оплата = 'счёт'\n")
        self.assertEqual(self.search("оплата")["results"][0]["path"], "папка/my module.py")

    def test_malformed_python_falls_back_to_lines(self):
        self.write("unfinished.py", "def brokeninvoice(\n")
        self.assertIn("brokeninvoice", self.search("brokeninvoice")["results"][0]["text"])

    def test_query_operators_are_data_not_fts_or_sql_syntax(self):
        self.write("a.txt", "invoice\n")
        self.assertTrue(self.search('invoice "; DROP TABLE files; -- : NOT ***')["results"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM files").fetchone()[0], 1)

    def test_budget_includes_json_and_unicode(self):
        self.write("a.txt", "оплата " * 10 + "\n" + ("оплата = 1\n" * 80))
        report = self.search("оплата", max_bytes=600)
        self.assertLessEqual(len(index.encoded(report).encode("utf-8")), 600)
        self.assertTrue(report["budget_exhausted"])
        for item in report["results"]:
            self.assertEqual(item["end"]-item["start"]+1, len(item["text"].splitlines()))

    def test_bad_query_and_limits_fail_clearly(self):
        for query, kwargs in [("***", {}), ("a", {"max_bytes": 1}), ("a", {"limit": 0})]:
            with self.assertRaises(ValueError):
                self.search(query, **kwargs)

    def test_additional_exclusions_remove_existing_content(self):
        self.write("internal/private.txt", "internaluniquemarker\n")
        self.search("internaluniquemarker")
        stats = index.refresh(self.db, self.root, ["internal/*"])
        self.assertEqual(index.search(self.db, self.root, "internaluniquemarker", stats)["results"], [])

    def test_changed_file_chunks_do_not_accumulate(self):
        self.write("a.txt", "appleunique\n")
        self.search("appleunique")
        self.write("a.txt", "bananaunique\n")
        self.assertEqual(self.search("appleunique")["results"], [])
        self.assertTrue(self.search("bananaunique")["results"])

    def test_transaction_rolls_back_on_indexing_failure(self):
        from unittest.mock import patch
        self.write("a.txt", "originaluniquemarker\n")
        self.search("originaluniquemarker")
        self.write("a.txt", "replacementuniquemarker\n")
        with patch.object(index, "chunks", side_effect=RuntimeError("parse failure")):
            with self.assertRaises(RuntimeError):
                index.refresh(self.db, self.root, [])
        self.assertEqual(self.db.execute("SELECT body FROM excerpts").fetchone()[0], "originaluniquemarker\n")

    def test_cache_permissions_and_root_binding(self):
        _, cache = index.locations(self.root)
        if os.name == "posix":
            self.assertEqual((cache / "index.sqlite3").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            index.connect(cache, self.root / "different-root")

    def test_independent_repositories_do_not_share_cache(self):
        self.write("a.txt", "privateuniquemarker\n")
        self.search("privateuniquemarker")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            resolved, cache = index.locations(root)
            other = index.connect(cache, resolved)
            try:
                stats = index.refresh(other, resolved, [])
                self.assertEqual(index.search(other, resolved, "privateuniquemarker", stats)["results"], [])
            finally:
                other.close()

    def test_read_source_rejects_traversal(self):
        self.assertIsNone(index.read_source(self.root, "../outside.txt"))
        self.assertIsNone(index.read_source(self.root, "/etc/passwd"))

    def test_cache_symlink_is_rejected(self):
        cache = self.root / "cache-link"
        cache.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            index.connect(cache, self.root)

    def test_git_linked_worktrees_have_distinct_cache(self):
        self.write("a.txt", "mainuniquemarker\n")
        subprocess.run(["git", "-C", str(self.root), "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "linked"
            subprocess.run(["git", "-C", str(self.root), "worktree", "add", "-q", "-b", "test-linked", str(worktree)], check=True)
            other_root, other_cache = index.locations(worktree)
            _, main_cache = index.locations(self.root)
            self.assertNotEqual(main_cache, other_cache)
            (other_root / "a.txt").write_text("linkeduniquemarker\n")
            other = index.connect(other_cache, other_root)
            try:
                stats = index.refresh(other, other_root, [])
                self.assertEqual(index.search(other, other_root, "mainuniquemarker", stats)["results"], [])
                self.assertTrue(self.search("mainuniquemarker")["results"])
            finally:
                other.close()

    def test_cli_search_and_purge(self):
        self.write("a.txt", "climarker\n")
        run = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "search", "climarker"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("climarker", run.stdout)
        self.db.close()
        run = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "purge"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse((self.root / ".git/awesome-astra-index/index.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
