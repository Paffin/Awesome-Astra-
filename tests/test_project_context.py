from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/astra-code/scripts'
sys.path.insert(0, str(SCRIPTS))
import project_context as context
import repo_index


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.git('init', '-q')
        _, cache = repo_index.locations(self.root)
        self.db = repo_index.connect(cache, self.root)
        self.addCleanup(self.db.close)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, text=True)

    def write(self, path, body):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        return hashlib.sha256(body.encode()).hexdigest()

    def run_context(self, action, **kwargs):
        return context.run(self.db, self.root, action, **kwargs)

    def test_deleted_provider_and_modified_consumer_keep_old_transitive_edges(self):
        self.write('core.py', 'value = 1\n')
        self.write('worker.py', 'import core\n')
        self.write('cli.py', 'import worker\n')
        self.run_context('update')
        (self.root / 'core.py').unlink()
        self.write('worker.py', 'value = 2\n')
        first = self.run_context('impact')
        self.assertEqual(first['affected_candidates'], ['cli.py', 'core.py', 'worker.py'])
        self.assertTrue(any(e.get('historical') for e in first['edges']))
        self.assertEqual(first, self.run_context('impact'))
        self.assertFalse(self.run_context('status')['fresh'])
        self.run_context('update')
        self.assertTrue(self.run_context('status')['fresh'])

    def test_renamed_provider_keeps_old_consumers_and_finds_new(self):
        self.write('old.py', 'value = 1\n')
        self.write('client.py', 'import old\n')
        self.run_context('update')
        (self.root / 'old.py').rename(self.root / 'new.py')
        self.write('new_client.py', 'import new\n')
        result = self.run_context('impact')
        self.assertEqual(result['affected_candidates'], ['client.py', 'new.py', 'new_client.py', 'old.py'])

    def test_persistent_baseline_survives_connection_restart(self):
        self.write('a.py', 'value = 1\n')
        self.run_context('update')
        _, cache = repo_index.locations(self.root)
        with repo_index.connect(cache, self.root) as other:
            result = context.run(other, self.root, 'status')
            self.assertTrue(result['fresh'])

    def test_worktree_isolation(self):
        self.write('a.py', 'value = 1\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'initial')
        self.run_context('update')
        other_root = Path(self.temp.name) / 'other'
        self.git('worktree', 'add', '-q', '-b', 'other', str(other_root))
        _, cache = repo_index.locations(other_root)
        other = repo_index.connect(cache, other_root)
        self.addCleanup(other.close)
        self.assertFalse(context.run(other, other_root, 'status')['baseline_exists'])
        self.assertTrue(self.run_context('status')['baseline_exists'])

    def contract(self):
        owner = self.write('api.proto', 'syntax = "proto3";\n')
        consumer = self.write('client.ts', 'export const version = 1;\n')
        data = {'version': 1, 'contracts': [{'name': 'wire API', 'owner': 'api.proto',
            'consumers': ['client.ts'], 'hashes': {'api.proto': owner, 'client.ts': consumer},
            'rationale': 'Client implements the protocol.'}]}
        self.write('contracts.json', json.dumps(data))
        return data

    def test_language_neutral_contract_hashes_and_stale_invalidation(self):
        self.contract()
        self.run_context('update', config='contracts.json')
        fresh = self.run_context('impact', config='contracts.json', changed=['api.proto'])
        self.assertIn('client.ts', fresh['affected_candidates'])
        self.assertEqual(fresh['contract_gaps'], [])
        self.write('api.proto', 'syntax = "proto2";\n')
        stale = self.run_context('impact', config='contracts.json')
        self.assertEqual(stale['contract_gaps'][0]['stale_or_missing_paths'], ['api.proto'])
        self.assertTrue(any(e.get('historical') for e in stale['edges']))
        self.run_context('update', config='contracts.json')
        report = context.read_baseline(self.db)
        self.assertEqual(report['contracts'], [])
        self.assertEqual(report['edges'], [])

    def test_invalid_contract_does_not_replace_baseline(self):
        self.run_context('update')
        before = context.read_baseline(self.db)
        data = self.contract()
        data['contracts'][0]['owner'] = '../outside'
        self.write('contracts.json', json.dumps(data))
        with self.assertRaises(ValueError):
            self.run_context('update', config='contracts.json')
        self.assertEqual(before, context.read_baseline(self.db))

    def test_policy_change_is_not_fresh(self):
        self.write('a.py', 'value = 1\n')
        self.run_context('update')
        result = self.run_context('status', source_roots=['src'])
        self.assertTrue(result['policy_changed'])
        self.assertFalse(result['fresh'])

    def test_failed_cli_update_preserves_baseline_and_pending_impact(self):
        self.write('core.py', 'value = 1\n')
        self.write('worker.py', 'import core\n')
        self.write('cli.py', 'import worker\n')
        self.run_context('update')
        before = context.read_baseline(self.db)
        (self.root / 'core.py').unlink()
        self.write('worker.py', 'value = 2\n')
        command = [sys.executable, str(SCRIPTS / 'project_context.py'),
                   'update', '--root', str(self.root), '--max-bytes', '512']
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2, failed.stderr)
        self.assertEqual(failed.stdout, '')
        self.assertIn('byte budget', failed.stderr)
        self.assertEqual(context.read_baseline(self.db), before)
        result = self.run_context('impact')
        self.assertEqual(result['affected_candidates'], ['cli.py', 'core.py', 'worker.py'])
        self.assertTrue(any(e.get('historical') for e in result['edges']))

    def test_cli_flow(self):
        self.write('a.py', 'value = 1\n')
        command = [sys.executable, str(SCRIPTS / 'project_context.py')]
        for action in ['update', 'status', 'impact']:
            run = subprocess.run(command + [action, '--root', str(self.root)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('snapshot_sha256', json.loads(run.stdout))
        run = subprocess.run(command + ['impact', '--root', str(self.root), '--changed', '../outside'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(run.stdout)


if __name__ == '__main__':
    unittest.main()
