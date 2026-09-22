"""Validate grader discrimination, not model performance."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'evals/fixtures/behavioral'

MIGRATION = '''def migrate(path):
    with sqlite3.connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version == 2:
            return
        db.execute("ALTER TABLE accounts ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")
        if db.execute('SELECT 1 FROM accounts WHERE balance_cents < 0').fetchone():
            raise ValueError('negative legacy balance')
        db.execute('PRAGMA user_version = 2')
'''

TRANSFER = '''import sqlite3

def transfer(path, event_id, source, destination, cents, fail_after_debit=False):
    with sqlite3.connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT source, destination, cents FROM deliveries WHERE event_id = ?', (event_id,)).fetchone()
        if previous is not None:
            if previous != (source, destination, cents):
                raise ValueError('event payload conflict')
            return False
        db.execute('UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?', (cents, source))
        if fail_after_debit:
            raise RuntimeError('simulated failure after debit')
        db.execute('UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?', (cents, destination))
        db.execute('INSERT INTO deliveries VALUES (?, ?, ?, ?)', (event_id, source, destination, cents))
    return True
'''


class FailureFixtureTests(unittest.TestCase):
    def run_fixture(self, task, repair=None):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / 'project'
            shutil.copytree(FIXTURES / task / 'project', work)
            if repair:
                repair(work)
            return subprocess.run(
                [sys.executable, '-I', str(FIXTURES / task / 'check.py'), str(work)],
                capture_output=True, text=True, timeout=20,
            )

    def migration(self, body):
        def repair(work):
            path = work / 'store.py'
            path.write_text(path.read_text() + '\n' + body)
        return repair

    def transfer(self, body):
        return lambda work: (work / 'payments.py').write_text(body)

    def test_migration_rejects_baseline_accepts_transactional_upgrade(self):
        self.assertNotEqual(self.run_fixture('schema-migration').returncode, 0)
        result = self.run_fixture('schema-migration', self.migration(MIGRATION))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_migration_rejects_schema_left_after_failed_upgrade(self):
        broken = MIGRATION.replace("        db.execute('BEGIN IMMEDIATE')\n", '')
        result = self.run_fixture('schema-migration', self.migration(broken))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed migration changed schema', result.stderr)

    def test_migration_rejects_missing_old_writer_default(self):
        broken = MIGRATION.replace("currency TEXT NOT NULL DEFAULT 'USD'", 'currency TEXT')
        broken = broken.replace("        if db.execute('SELECT 1", "        db.execute(\"UPDATE accounts SET currency = 'USD'\")\n        if db.execute('SELECT 1")
        self.assertNotEqual(self.run_fixture('schema-migration', self.migration(broken)).returncode, 0)

    def test_retry_rejects_baseline_accepts_atomic_idempotency(self):
        self.assertNotEqual(self.run_fixture('retry-idempotency').returncode, 0)
        result = self.run_fixture('retry-idempotency', self.transfer(TRANSFER))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_retry_rejects_commit_before_failure(self):
        broken = TRANSFER.replace('        if fail_after_debit:', '        db.commit()\n        if fail_after_debit:')
        result = self.run_fixture('retry-idempotency', self.transfer(broken))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Debit and delivery must roll back', result.stderr)

    def test_retry_rejects_ignored_payload_conflict(self):
        broken = TRANSFER.replace("                raise ValueError('event payload conflict')", '                return False')
        result = self.run_fixture('retry-idempotency', self.transfer(broken))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('different payload must fail', result.stderr)

    def test_retry_rejects_constant_success(self):
        broken = 'def transfer(*args, **kwargs):\n    return True\n'
        self.assertNotEqual(self.run_fixture('retry-idempotency', self.transfer(broken)).returncode, 0)


if __name__ == '__main__':
    unittest.main()
