import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/astra-code/scripts'))
import acceptance
import verify_command


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('def answer(value):\n    return 42 if value else None\n')
        self.plan = {'schema': 1, 'risks': [], 'criteria': [
            {'id': 'answer', 'expected': 'Truthy input returns 42; false input returns None',
             'kinds': ['entrypoint', 'negative']}]}
        self.path = self.root / 'acceptance.json'
        self.ledger = {'checks': []}

    def prepare(self, kinds=('entrypoint', 'negative'), external=False):
        if external:
            self.path = self.base / 'acceptance.json'
        self.path.write_text(json.dumps(self.plan))
        self.ledger['acceptance_plan_sha256'] = verify_command.digest(self.plan)
        environment = None
        if external:
            environment = self.base / 'environment.json'
            environment.write_text(json.dumps({'files': [str(self.path)]}))
        for number, kind in enumerate(kinds):
            receipt = self.base / f'{number}.receipt.json'
            code = ('from app import answer; assert answer(False) is None'
                    if kind == 'negative' else 'from app import answer; assert answer(True) == 42')
            verify_command.run(self.root, [sys.executable, '-c', code], receipt, environment=environment)
            self.ledger['checks'].append({'id': f'check-{number}', 'criteria': ['answer'],
                                         'kind': kind, 'passed': True, 'evidence': 'executed assertion',
                                         'receipt': str(receipt)})

    def result(self):
        return acceptance.check(self.plan, self.ledger, self.root, self.path)

    def test_entrypoint_and_negative_with_receipts_pass(self):
        self.prepare()
        self.assertTrue(self.result()['acceptance_gate_passed'])

    def test_public_integration_cli_enforces_acceptance(self):
        self.prepare()
        repository = Path(__file__).resolve().parents[1]
        mapped = subprocess.run([sys.executable,
            str(repository / 'skills/astra-code/scripts/project_map.py'),
            '--root', str(self.root), '--changed', 'app.py'],
            capture_output=True, text=True, check=True, timeout=10)
        report = json.loads(mapped.stdout)
        report_path = self.base / 'impact.json'
        report_path.write_text(mapped.stdout)
        self.ledger.update({'snapshot_sha256': report['snapshot_sha256'],
            'consumers': {p: {'disposition': 'compatible', 'evidence': 'public answer assertions'}
                          for p in report['affected_candidates']},
            'coverage_review': {'unsupported_files': {'resolved': True,
                               'evidence': 'acceptance.json is reviewed metadata, not source code'}}})
        ledger_path = self.base / 'ledger.json'
        ledger_path.write_text(json.dumps(self.ledger))
        argv = [sys.executable, str(repository / 'tools/check_integration.py'),
                str(report_path), str(ledger_path), '--root', str(self.root),
                '--acceptance', str(self.path)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.ledger['checks'] = self.ledger['checks'][:1]
        ledger_path.write_text(json.dumps(self.ledger))
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('missing recorded negative', result.stdout)

    def test_external_plan_bound_in_environment(self):
        self.prepare(external=True)
        self.assertTrue(self.result()['acceptance_gate_passed'])

    def test_successful_command_cannot_replace_missing_negative(self):
        self.prepare(('entrypoint',))
        self.assertIn('missing recorded negative check for criterion: answer', self.result()['errors'])

    def test_stale_source_and_tampered_log_fail(self):
        self.prepare()
        (self.root / 'app.py').write_text('def answer(value): return 0\n')
        self.assertFalse(self.result()['acceptance_gate_passed'])
        (self.root / 'app.py').write_text('def answer(value):\n    return 42 if value else None\n')
        (self.base / '0.receipt.json.log').write_text('tampered')
        self.assertTrue(any('checksum mismatch' in error for error in self.result()['errors']))

    def test_plan_changed_after_recording_fails_even_with_new_ledger_hash(self):
        self.prepare()
        self.plan['criteria'][0]['expected'] = 'Changed after verification'
        self.path.write_text(json.dumps(self.plan))
        self.ledger['acceptance_plan_sha256'] = verify_command.digest(self.plan)
        self.assertFalse(self.result()['acceptance_gate_passed'])

    def test_external_plan_unrecorded_fails(self):
        self.path = self.base / 'acceptance.json'
        self.prepare()
        self.assertTrue(any('not recorded' in error for error in self.result()['errors']))

    def test_unresolved_boundary_remains_incomplete(self):
        self.plan['boundaries'] = [{'id': 'other-service', 'status': 'unavailable', 'criteria': ['answer']}]
        self.prepare()
        result = self.result()
        self.assertFalse(result['acceptance_gate_passed'])
        self.assertEqual(result['unresolved'], ['other-service'])

    def test_exception_cannot_waive_missing_check(self):
        self.plan['exceptions'] = [{'reason': 'consumer not accessible', 'reviewer': 'owner'}]
        self.prepare(('entrypoint',))
        self.assertFalse(self.result()['acceptance_gate_passed'])
        self.assertTrue(self.result()['exceptions'])

    def test_risks_require_specific_scenarios(self):
        self.plan['criteria'][0]['risks'] = ['migration', 'concurrency', 'security']
        self.prepare()
        errors = self.result()['errors']
        for kind in ['compatibility', 'recovery', 'concurrency', 'replay', 'failure', 'denied-path']:
            self.assertIn(f'missing recorded {kind} check for criterion: answer', errors)

    def test_performance_uses_recorded_whole_command_duration(self):
        self.plan['criteria'][0].update(kinds=['entrypoint', 'performance'],
                                        risks=['performance'], max_duration_seconds=1e-12)
        self.prepare(('entrypoint', 'performance'))
        self.assertTrue(any('exceeds budget' in error for error in self.result()['errors']))

    def test_duplicate_ids_and_unknown_references_rejected(self):
        self.prepare()
        saved = copy.deepcopy(self.ledger)
        self.ledger['checks'].append(copy.deepcopy(self.ledger['checks'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate check'):
            self.result()
        self.ledger = saved
        self.ledger['checks'][0]['criteria'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'check criteria'):
            self.result()

    def test_empty_criteria_and_unknown_risk_rejected(self):
        self.plan['criteria'] = []
        self.prepare(())
        with self.assertRaisesRegex(ValueError, 'nonempty acceptance criteria'):
            self.result()
        self.plan['criteria'] = [{'id': 'a', 'expected': 'result', 'kinds': ['entrypoint'], 'risks': ['typo']}]
        self.path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError, 'criterion risks'):
            self.result()


if __name__ == '__main__':
    unittest.main()
