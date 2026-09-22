import importlib.util
import json
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('run_evals', ROOT / 'tools/run_evals.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class EvalRunnerTests(unittest.TestCase):
    def setup_fixture(self, base, body):
        base = base / 'source'
        base.mkdir()
        project = base / 'project'
        project.mkdir()
        (project / 'value.py').write_text('VALUE = 0\n')
        # An agent-controlled test must not be used as the external grader.
        (project / 'check.py').write_text('raise SystemExit(1)\n')
        (base / 'check.py').write_text("import sys\nfrom pathlib import Path\nassert (Path(sys.argv[1]) / 'value.py').read_text() == 'VALUE = 1\\n'\n")
        manifest = base / 'manifest.json'
        manifest.write_text(json.dumps({'tasks': [{'id': 'test', 'project': 'project', 'check': 'check.py', 'prompt': 'set value to one'}]}))
        skill = base / 'skill'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('test skill')
        executor = base / 'fake.py'
        executor.write_text('import sys, time\nfrom pathlib import Path\nw=Path(sys.argv[1])\n' + body)
        argv = [sys.executable, str(executor), '{workspace}', '{prompt}', '{model}', '{variant}']
        return manifest, skill, argv

    def test_paired_isolation_alternating_order_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, "assert (w/'value.py').read_text() == 'VALUE = 0\\n'\nassert (w/'.agents/skills/astra-code/SKILL.md').exists() == (sys.argv[4] == 'candidate')\n(w/'value.py').write_text('VALUE = 1\\n')\nprint('synthetic executor only')\n")
            rows = runner.run(manifest, argv, 'synthetic-test', base/'output', skill, repeats=2, synthetic=True)
            self.assertEqual([r['variant'] for r in rows], ['baseline', 'candidate', 'candidate', 'baseline'])
            self.assertTrue(all(r['accepted'] for r in rows))
            self.assertTrue(all(r['tokens'] is None and r['synthetic_executor'] for r in rows))
            self.assertEqual((base/'source/project/value.py').read_text(), 'VALUE = 0\n')
            self.assertTrue((base/'output/test-0-candidate/workspace/value.py').exists())
            self.assertIn('synthetic executor', (base/'output/test-0-baseline/executor.stdout').read_text())

    def test_workspace_test_tampering_does_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, "(w/'check.py').write_text('raise SystemExit(0)\\n')\n")
            rows = runner.run(manifest, argv, 'fake', base/'out', skill, synthetic=True)
            self.assertTrue(all(not r['accepted'] and r['grader_integrity'] for r in rows))

    def test_executor_failure_is_not_graded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'raise SystemExit(7)\n')
            rows = runner.run(manifest, argv, 'fake', base/'out', skill, synthetic=True)
            self.assertTrue(all(r['executor']['exit_code'] == 7 and r['check'] is None and not r['accepted'] for r in rows))

    def test_timeout_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'time.sleep(20)\n')
            rows = runner.run(manifest, argv, 'fake', base/'out', skill, timeout=.1, synthetic=True)
            self.assertTrue(all(r['executor']['timed_out'] and not r['accepted'] for r in rows))

    def test_external_grader_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, "(w.parent/'trusted/test.py').write_text('raise SystemExit(0)\\n')\n")
            rows = runner.run(manifest, argv, 'fake', base/'out', skill, synthetic=True)
            self.assertTrue(all(not r['grader_integrity'] and not r['accepted'] for r in rows))

    def test_nonfinite_timeout_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'pass\n')
            for timeout in (float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    runner.run(manifest, argv, 'fake', base/'out', skill, timeout=timeout)

    def test_real_fixtures_reject_original_accept_known_repairs(self):
        data = json.loads((ROOT/'evals/executable.json').read_text())
        for task in data['tasks']:
            if task['id'] == 'wire-contract' and not shutil.which('node'):
                continue  # The external grader records 77; Python-only CI tests other fixtures.
            with self.subTest(task=task['id']), tempfile.TemporaryDirectory() as directory:
                work = Path(directory)/'project'
                shutil.copytree(ROOT/'evals'/task['project'], work)
                command = [sys.executable, '-I', str(ROOT/'evals'/task['check']), str(work)]
                self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                if task['id'] == 'shared-price':
                    (work/'pricing.py').write_text('def total(subtotal_cents, member=False):\n    return (subtotal_cents * 9 + 5) // 10 if member else subtotal_cents\n')
                    (work/'invoice.py').write_text('from pricing import total\ndef invoice_total(subtotal_cents, member=False):\n    return total(subtotal_cents, member)\n')
                elif task['id'] == 'route-registration':
                    with (work/'handlers.py').open('a') as f:
                        f.write("\ndef ready():\n    return {'ready': True}\n")
                    with (work/'app.py').open('a') as f:
                        f.write("\nfrom handlers import ready\nROUTES['/ready'] = ready\n")
                    with (work/'client.py').open('a') as f:
                        f.write("\ndef is_ready():\n    return request('/ready')[1]['ready']\n")
                else:
                    for name in ('backend.py', 'client.mjs', 'schema.json'):
                        file = work/name
                        file.write_text(file.read_text().replace('amount', 'total_cents'))
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                if task['id'] == 'shared-price':
                    (work/'invoice.py').write_text('def invoice_total(subtotal_cents, member=False):\n    return (subtotal_cents * 9 + 5) // 10 if member else subtotal_cents\n')
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                elif task['id'] == 'route-registration':
                    with (work/'client.py').open('a') as f:
                        f.write('\ndef is_ready():\n    return True\n')
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_cli_rejects_nan_and_source_output_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'raise RuntimeError("must not run")\n')
            common = [sys.executable, str(ROOT/'tools/run_evals.py'), '--manifest', str(manifest),
                      '--skill', str(skill), '--executor', json.dumps(argv), '--model', 'fake', '--synthetic']
            for extra in (["--output", str(base/'out'), '--timeout', 'nan'],
                          ['--output', str(skill/'out')],
                          ['--output', str(manifest.parent/'project/out')],
                          ['--output', str(manifest.parent/'out')]):
                result = subprocess.run(common + extra, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse((base/'out').exists())
            self.assertFalse((skill/'out').exists())

    def test_root_fixture_and_skill_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'pass\n')
            linked_skill = base/'linked-skill'
            linked_skill.symlink_to(skill, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                runner.run(manifest, argv, 'fake', base/'out', linked_skill)
            project_link = manifest.parent/'linked-project'
            project_link.symlink_to(manifest.parent/'project', target_is_directory=True)
            data = json.loads(manifest.read_text())
            data['tasks'][0]['project'] = 'linked-project'
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'symlink'):
                runner.run(manifest, argv, 'fake', base/'out', skill)

    def test_requires_explicit_execution_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            manifest, skill, argv = self.setup_fixture(base, 'pass\n')
            with self.assertRaises(ValueError):
                runner.run(manifest, ['echo'], 'fake', base/'out', skill)
            self.assertFalse((base/'out').exists())


if __name__ == '__main__':
    unittest.main()
