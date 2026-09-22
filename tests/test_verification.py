import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/astra-code/scripts'
sys.path.insert(0, str(SCRIPTS))
import verify_command as recorder
spec = importlib.util.spec_from_file_location('recorded_gate', SCRIPTS / 'check_integration.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('answer = 42\n')
        self.receipt = self.base / 'receipt.json'

    def record(self, code='print("ok")', **kwargs):
        return recorder.run(self.root, [sys.executable, '-c', code], self.receipt, **kwargs)

    def test_success_and_gate(self):
        self.record()
        self.assertTrue(recorder.verify(self.root, self.receipt)['recorded_check_passed'])
        report = {'snapshot_sha256': 'test', 'affected_candidates': ['app.py'],
                  'files': recorder.snapshot(self.root)['files'], 'exclude': []}
        ledger = {'snapshot_sha256': 'test', 'consumers': {'app.py': {
            'disposition': 'compatible', 'evidence': 'reviewed'}}, 'checks': [{
            'kind': 'entrypoint', 'passed': True, 'evidence': 'local run', 'receipt': str(self.receipt)}]}
        self.assertTrue(gate.check(report, ledger, self.root, True)['ledger_gate_passed'])
        report['contract_gaps'] = [{'name': 'api'}]
        self.assertFalse(gate.check(report, ledger, self.root, True)['ledger_gate_passed'])
        del report['contract_gaps']
        del report['files']
        self.assertFalse(gate.check(report, ledger, self.root, True)['ledger_gate_passed'])
        report['files'] = recorder.snapshot(self.root)['files']
        del ledger['checks'][0]['receipt']
        self.assertFalse(gate.check(report, ledger, self.root, True)['ledger_gate_passed'])
        self.assertTrue(gate.check(report, ledger)['ledger_gate_passed'])

    def test_old_report_with_fresh_receipt_rejected(self):
        files = recorder.snapshot(self.root)['files']
        (self.root / 'app.py').write_text('answer = 43\n')
        self.record()
        report = {'snapshot_sha256': 'old', 'affected_candidates': ['app.py'],
                  'files': files, 'exclude': []}
        ledger = {'snapshot_sha256': 'old', 'consumers': {'app.py': {
            'disposition': 'compatible', 'evidence': 'reviewed'}}, 'checks': [{
            'kind': 'entrypoint', 'passed': True, 'evidence': 'local run', 'receipt': str(self.receipt)}]}
        result = gate.check(report, ledger, self.root, True)
        self.assertIn('impact report source inventory is stale', result['errors'])

    def test_stale(self):
        self.record()
        (self.root / 'app.py').write_text('answer = 43\n')
        self.assertFalse(recorder.verify(self.root, self.receipt)['recorded_check_passed'])

    def test_payload_tamper(self):
        self.record()
        data = json.loads(self.receipt.read_text())
        data['payload']['argv'] = ['invented']
        self.receipt.write_text(json.dumps(data))
        self.assertIn('receipt checksum mismatch', recorder.verify(self.root, self.receipt)['errors'])

    def test_log_tamper(self):
        self.record()
        self.receipt.with_suffix('.json.log').write_text('fake')
        self.assertIn('log checksum mismatch', recorder.verify(self.root, self.receipt)['errors'])

    def test_failure(self):
        self.record('raise SystemExit(7)')
        self.assertFalse(recorder.verify(self.root, self.receipt)['recorded_check_passed'])

    def test_timeout(self):
        started = time.monotonic()
        result = self.record('import time; time.sleep(30)', timeout=0.1)
        self.assertTrue(result['timed_out'])
        self.assertLess(time.monotonic() - started, 5)
        self.assertFalse(recorder.verify(self.root, self.receipt)['recorded_check_passed'])

    @unittest.skipUnless(sys.platform != 'win32', 'POSIX process group cleanup')
    def test_surviving_descendant_timeout(self):
        result = self.record('import subprocess,sys; subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])', timeout=0.2)
        self.assertTrue(result['timed_out'])
        self.assertIsNone(result['output_error'])

    def test_bounded_log(self):
        result = self.record('print("x" * 1000000)', max_log_bytes=64)
        self.assertTrue(result['log_truncated'])
        self.assertEqual(self.receipt.with_suffix('.json.log').stat().st_size, 64)
        self.assertTrue(recorder.verify(self.root, self.receipt)['recorded_check_passed'])

    def test_source_modified_by_command(self):
        self.record('from pathlib import Path; Path("app.py").write_text("changed")')
        self.assertFalse(recorder.verify(self.root, self.receipt)['recorded_check_passed'])

    def test_reject_inside_repo_and_reuse(self):
        with self.assertRaises(ValueError):
            recorder.run(self.root, [sys.executable, '-c', 'pass'], self.root / 'receipt.json')
        self.record()
        with self.assertRaises(FileExistsError):
            self.record()

    def test_arguments_are_literal(self):
        recorder.run(self.root, [sys.executable, '-c', 'import sys; print(sys.argv[1])', '$(touch injected); hello'], self.receipt)
        self.assertFalse((self.root / 'injected').exists())
        self.assertIn('$(touch injected)', self.receipt.with_suffix('.json.log').read_text())


if __name__ == '__main__':
    unittest.main()
