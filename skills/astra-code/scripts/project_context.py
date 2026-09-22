#!/usr/bin/env python3
"""Persist per-worktree import context and explicit, hash-bound contract facts.

Update before editing; impact refreshes against that baseline without advancing it.
Only an explicit update accepts a new baseline. No target code is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
import sys

import project_map
import repo_index


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Expected repository-relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Paths must be repository-relative without traversal')
    return str(path)


def contracts(root, config, report):
    """Declarations need exact hashes: stale facts remain gaps, never fresh edges."""
    report['contract_gaps'] = []
    report['contracts'] = []
    if config is None:
        return
    config = relative(config)
    source = repo_index.read_source(root, config)
    if source is None or config not in report['files']:
        raise ValueError('Contract config must be an eligible repository file')
    if source[1] != report['files'][config]:
        raise ValueError('Contract config changed during refresh; retry')
    data = json.loads(source[0])
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('contracts'), list):
        raise ValueError('Contract config requires version: 1 and contracts: []')
    for item in data['contracts']:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not item['name'].strip():
            raise ValueError('Each contract requires a name')
        if 'rationale' in item and (not isinstance(item['rationale'], str) or not item['rationale'].strip()):
            raise ValueError('Contract rationale must be a nonempty string when supplied')
        owner = relative(item.get('owner'))
        consumers = item.get('consumers')
        hashes = item.get('hashes')
        if not isinstance(consumers, list) or not consumers or not isinstance(hashes, dict):
            raise ValueError('Contract requires consumers and hashes')
        consumers = [relative(p) for p in consumers]
        paths = {owner, *consumers}
        for path in paths:
            digest = hashes.get(path)
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('Contract hashes must contain SHA-256 for owner and every consumer')
        stale = sorted(p for p in paths if report['files'].get(p) != hashes[p])
        if stale:
            report['contract_gaps'].append({'name': item['name'], 'stale_or_missing_paths': stale})
            continue
        report['contracts'].append(item)
        report['edges'].extend({'provider': owner, 'consumer': p, 'line': None,
            'evidence': 'Explicit hash-bound contract declaration: ' + item['name']} for p in consumers)
    report['snapshot_sha256'] = hashlib.sha256((report['snapshot_sha256'] + source[1]).encode()).hexdigest()


def table(db):
    db.execute('CREATE TABLE IF NOT EXISTS project_context (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT)')


def read_baseline(db):
    table(db)
    row = db.execute('SELECT data FROM project_context WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None


def run(db, root, action, patterns=None, source_roots=None, config=None, changed=None, max_bytes=100000):
    if max_bytes < 512:
        raise ValueError("max-bytes must be at least 512")
    patterns, source_roots = patterns or [], source_roots or ['.']
    source_roots = [relative(p) for p in source_roots]
    changed = [relative(p) for p in (changed or [])]
    previous = read_baseline(db)
    current = project_map.build(db, root, patterns, source_roots)
    contracts(root, config, current)
    current['context_policy'] = {'exclude': patterns, 'source_roots': source_roots, 'contracts': config}
    oldfiles = previous['files'] if previous else {}
    delta = sorted(p for p in oldfiles.keys() | current['files'].keys() if oldfiles.get(p) != current['files'].get(p))
    policy_changed = previous is not None and previous.get('context_policy') != current['context_policy']
    result = {'baseline_exists': previous is not None, 'baseline_sha256': previous['snapshot_sha256'] if previous else None,
        'snapshot_sha256': current['snapshot_sha256'], 'files': current['files'],
        'exclude': current['exclude'], 'changed_paths': delta,
        'policy_changed': policy_changed, 'fresh': previous is not None and not delta and not policy_changed,
        'contract_gaps': current['contract_gaps'], 'whole_project_verified': False,
        'limitations': current['limitations'] + [
            'Baseline covers only the last explicit update; run update before editing',
            'Contract declarations are reviewed assertions, not compiler-verified bindings',
            'Refresh reads eligible files to check hashes; there is no background watcher']}
    if action == 'impact':
        combined = dict(current)
        combined['limitations'] = result['limitations']
        # Retain old consumers even when providers or their import statements disappear.
        # Old edges are historical candidates only; never presented as current facts.
        combined['edges'] = list(current['edges'])
        if previous:
            for edge in previous['edges']:
                if edge not in combined['edges']:
                    combined['edges'].append({**edge, 'historical': True})
        impact = project_map.impact(combined, sorted(set(delta + changed)))
        result.update(impact)
        result['historical_edges_are_candidates'] = True
        result['baseline_advanced'] = False
    elif action == 'update':
        result['baseline_advanced'] = True
    elif action != 'status':
        raise ValueError('Unknown context action')
    # Validate the complete response before publishing a new baseline. Cache
    # refreshes are harmless; accepting a baseline discards pending impact.
    if len(repo_index.encoded(result).encode()) > max_bytes:
        raise ValueError('Context exceeds byte budget; increase --max-bytes. No partial output emitted')
    if action == 'update':
        with db:
            db.execute('INSERT OR REPLACE INTO project_context VALUES (1, ?)', (json.dumps(current),))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['update', 'status', 'impact'])
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--source-root', action='append')
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--contracts', help='Repo-relative JSON declarations with recorded SHA-256 hashes')
    parser.add_argument('--changed', action='append', default=[])
    parser.add_argument('--max-bytes', type=int, default=100000)
    args = parser.parse_args()
    try:
        if args.max_bytes < 512:
            raise ValueError('max-bytes must be at least 512')
        root, cache = repo_index.locations(args.root)
        db = repo_index.connect(cache, root)
        try:
            result = run(db, root, args.action, args.exclude, args.source_root, args.contracts, args.changed, args.max_bytes)
            output = repo_index.encoded(result)
            sys.stdout.write(output)
        finally:
            db.close()
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(f'project-context: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
