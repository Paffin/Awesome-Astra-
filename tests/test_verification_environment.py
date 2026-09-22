import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/astra-code/scripts'))
import verify_command as recorder


class EnvironmentReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('answer = 42\n')
        self.receipt = self.base / 'receipt.json'
        self.config = self.base / 'environment.json'
        self.lock = self.base / 'external.lock'
        self.lock.write_text('dependency-version-1')
        self.config.write_text(json.dumps({'files': ['external.lock'],
                                          'facts': {'schema': 'reviewed-v3'}}))

    def record(self, code='pass', **kwargs):
        return recorder.run(self.root, [sys.executable, '-c', code], self.receipt,
                            environment=self.config, **kwargs)

    def valid(self):
        return recorder.verify(self.root, self.receipt)['recorded_check_passed']

    def test_external_file_change_invalidates(self):
        payload = self.record()
        self.assertTrue(self.valid())
        self.assertFalse(payload['environment_before']['declaration']['facts_verified'])
        self.assertNotIn('dependency-version-1', self.receipt.read_text())
        self.assertNotIn('reviewed-v3', self.receipt.read_text())
        self.lock.write_text('dependency-version-2')
        self.assertFalse(self.valid())

    def test_declaration_bytes_and_facts_are_bound(self):
        self.record()
        self.config.write_text(self.config.read_text() + '\n')
        self.assertFalse(self.valid())

    def test_deleted_external_input_invalidates(self):
        self.record()
        self.lock.unlink()
        self.assertFalse(self.valid())

    def test_command_modifying_external_input_invalidates(self):
        self.record(f'from pathlib import Path; Path({str(self.lock)!r}).write_text("new")')
        self.assertFalse(self.valid())

    def test_command_deleting_declaration_still_records_failure(self):
        payload = self.record(f'from pathlib import Path; Path({str(self.config)!r}).unlink()')
        self.assertEqual(payload['environment_error'], 'FileNotFoundError')
        self.assertFalse(self.valid())

    def test_source_change_still_invalidates(self):
        self.record()
        (self.root / 'app.py').write_text('answer = 43\n')
        self.assertFalse(self.valid())

    @unittest.skipUnless(os.name == 'posix', 'executable script fixture')
    def test_executable_identity_change_invalidates_without_declaration(self):
        executable = self.base / 'check'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o700)
        recorder.run(self.root, [str(executable)], self.receipt)
        self.assertTrue(self.valid())
        executable.write_text('#!/bin/sh\nexit 1\n')
        self.assertFalse(self.valid())

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permission semantics')
    def test_executable_mode_change_invalidates(self):
        executable = self.base / 'check'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o700)
        recorder.run(self.root, [str(executable)], self.receipt)
        self.assertTrue(self.valid())
        executable.chmod(0o600)
        self.assertFalse(self.valid())

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permission semantics')
    def test_declared_file_mode_change_invalidates(self):
        self.lock.chmod(0o600)
        self.record()
        self.assertTrue(self.valid())
        self.lock.chmod(0o400)
        self.assertFalse(self.valid())

    def test_invalid_declarations_do_not_run_command(self):
        for config in [[], {'files': 'external.lock'}, {'files': [0]},
                       {'files': ['']}, {'facts': []}, {'commands': ['echo hi']},
                       {'facts': {'value': float('nan')}}]:
            with self.subTest(config=config):
                self.config.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    self.record('raise SystemExit("must not run")')
                self.assertFalse(self.receipt.exists())

    def test_legacy_receipt_remains_valid(self):
        self.record()
        data = json.loads(self.receipt.read_text())
        data['payload']['schema'] = 1
        for key in ('environment_before', 'environment_after', 'environment_error'):
            del data['payload'][key]
        data['payload_sha256'] = recorder.digest(data['payload'])
        self.receipt.write_text(json.dumps(data))
        self.assertTrue(self.valid())

    @unittest.skipUnless(os.name == 'posix', 'FIFO fixture')
    def test_special_file_rejected_before_read(self):
        fifo = self.base / 'fifo'
        os.mkfifo(fifo)
        self.config.write_text(json.dumps({'files': ['fifo']}))
        with self.assertRaises(ValueError):
            self.record()


if __name__ == '__main__':
    unittest.main()
