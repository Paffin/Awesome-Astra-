#!/usr/bin/env python3
"""Run paired behavioral tasks with an explicit external model executor.

This is process/worktree isolation, NOT a hostile-code security sandbox. Run in
an externally isolated environment with no secrets. Graders are trusted code.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(Path(root).rglob('*')) if p.is_file() and not p.is_symlink()}


def execute(argv, cwd, env, timeout, prefix):
    started = time.monotonic()
    with Path(str(prefix) + '.stdout').open('wb') as out, Path(str(prefix) + '.stderr').open('wb') as err:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=out, stderr=err,
                                    start_new_session=os.name == 'posix')
        except OSError as exc:
            err.write(str(exc).encode())
            return {'exit_code': None, 'timed_out': False, 'error': str(exc), 'elapsed_seconds': time.monotonic() - started}
        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Also remove descendants after a successful parent exit.
            if os.name == 'posix':
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif proc.poll() is None:
                proc.kill()
            proc.wait()
    return {'exit_code': proc.returncode, 'timed_out': timed_out,
            'elapsed_seconds': time.monotonic() - started}


def run(manifest, executor, model, output, skill, repeats=1, timeout=300, check_timeout=60, synthetic=False):
    manifest = Path(manifest).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('output must be a new directory; never overwrite earlier evidence')
    if not model.strip() or not executor or not all(isinstance(x, str) for x in executor):
        raise ValueError('model and nonempty executor argv are required')
    if repeats < 1 or not math.isfinite(timeout) or not math.isfinite(check_timeout) or timeout <= 0 or check_timeout <= 0:
        raise ValueError('repeats and timeouts must be positive')
    # Literal replacement, no shell or format-string interpretation.
    if not all(any('{' + key + '}' in arg for arg in executor) for key in ('workspace', 'prompt', 'model', 'variant')):
        raise ValueError('executor must contain {workspace}, {prompt}, {model}, {variant}')
    data = json.loads(manifest.read_text())
    tasks = data['tasks']
    ids = [t['id'] for t in tasks]
    if not tasks or len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x.replace('-', '').replace('_', '').isalnum() for x in ids):
        raise ValueError('task ids must be unique simple names')
    sources = []
    for task in tasks:
        project_source = manifest.parent / task['project']
        check_source = manifest.parent / task['check']
        if project_source.is_symlink() or check_source.is_symlink():
            raise ValueError('fixture symlinks are not supported')
        project = project_source.resolve()
        check = check_source.resolve()
        if not project.is_dir() or not check.is_file() or not task['prompt'].strip():
            raise ValueError('invalid fixture')
        if any(p.is_symlink() for p in project.rglob('*')) or check.is_symlink():
            raise ValueError('fixture symlinks are not supported')
        sources.append((task, project, check))
    if not (Path(skill) / 'SKILL.md').is_file():
        raise ValueError('candidate skill is missing SKILL.md')
    if Path(skill).is_symlink() or any(p.is_symlink() for p in Path(skill).rglob('*')):
        raise ValueError('skill symlinks are not supported')
    protected = [Path(skill).resolve(), manifest.parent]
    protected.extend(project for _, project, _ in sources)
    protected.extend(check.parent for _, _, check in sources)
    if any(output.is_relative_to(path) or path.is_relative_to(output) for path in protected):
        raise ValueError('output must not overlap skill, fixture, or evaluator source directories')
    output.mkdir(parents=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix='astra-evals-') as scratch:
        scratch = Path(scratch)
        frozen = scratch / 'trusted'
        frozen.mkdir()
        for task, project, check in sources:
            shutil.copyfile(check, frozen / (task['id'] + '.py'))
        checks = {p.name: digest(p) for p in frozen.iterdir()}
        projects = scratch / 'frozen-projects'
        projects.mkdir()
        frozen_skill = scratch / 'frozen-skill'
        shutil.copytree(skill, frozen_skill)
        for task, project, _ in sources:
            shutil.copytree(project, projects / task['id'])
        provenance = {'model': model, 'executor_argv_template': executor, 'manifest': data,
                      'manifest_sha256': digest(manifest), 'grader_hashes': checks,
                      'skill_hashes': tree_hashes(frozen_skill),
                      'fixture_hashes': {t['id']: tree_hashes(projects / t['id']) for t, _, _ in sources},
                      'environment': {'platform': platform.platform(), 'python': sys.version,
                                      'git': subprocess.check_output(['git', '--version'], text=True).strip()},
                      'repeats': repeats, 'timeout': timeout, 'check_timeout': check_timeout,
                      'adapter_contract': 'Each invocation must start a fresh model session, isolate global skills/config, load candidate .agents/skills only, and perform no automatic network/dependency installation.'}
        (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        for repeat in range(repeats):
            for task, project, _ in sources:
                order = ('baseline', 'candidate') if repeat % 2 == 0 else ('candidate', 'baseline')
                for variant in order:
                    run_id = f"{task['id']}-{repeat}-{variant}"
                    evidence = output / run_id
                    evidence.mkdir()
                    workspace = scratch / run_id
                    shutil.copytree(projects / task['id'], workspace)
                    env = os.environ.copy()
                    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
                        env.pop(key, None)
                    subprocess.run(['git', 'init', '-q', str(workspace)], check=True, env=env)
                    subprocess.run(['git', '-C', str(workspace), 'add', '.'], check=True, env=env)
                    subprocess.run(['git', '-C', str(workspace), '-c', 'user.name=Evaluation', '-c', 'user.email=eval@localhost', 'commit', '-qm', 'fixture'], check=True, env=env)
                    if variant == 'candidate':
                        shutil.copytree(frozen_skill, workspace / '.agents' / 'skills' / 'astra-code')
                    prompt = evidence / 'prompt.txt'
                    prompt.write_text(task['prompt'], encoding='utf-8')
                    values = {'workspace': str(workspace), 'prompt': str(prompt), 'model': model, 'variant': variant}
                    argv = list(executor)
                    for key, value in values.items():
                        argv = [arg.replace('{' + key + '}', value) for arg in argv]
                    result = execute(argv, workspace, env, timeout, evidence / 'executor')
                    integrity = all(p.is_file() and digest(p) == h for name, h in checks.items() for p in [frozen / name])
                    check_result = None
                    if integrity and result['exit_code'] == 0 and not result['timed_out']:
                        check_result = execute([sys.executable, '-I', str(frozen / (task['id'] + '.py')), str(workspace)], frozen, env, check_timeout, evidence / 'check')
                    integrity = integrity and all(p.is_file() and digest(p) == h for name, h in checks.items() for p in [frozen / name])
                    execute(['git', 'diff', 'HEAD', '--'], workspace, env, check_timeout, evidence / 'diff')
                    execute(['git', 'status', '--porcelain'], workspace, env, check_timeout, evidence / 'status')
                    # Include untracked outputs too, not only git diff.
                    shutil.copytree(workspace, evidence / 'workspace', ignore=shutil.ignore_patterns('.git'), symlinks=True)
                    row = {'run_id': run_id, 'task_id': task['id'], 'repeat': repeat, 'variant': variant,
                           'model': model, 'synthetic_executor': synthetic, 'executor': result,
                           'check': check_result, 'grader_integrity': integrity,
                           'accepted': bool(integrity and check_result and check_result['exit_code'] == 0 and not check_result['timed_out']),
                           'tokens': None, 'evidence': str(evidence), 'provenance': str(output / 'provenance.json'), 'grader_sha256': checks[task['id'] + '.py']}
                    rows.append(row)
                    with (output / 'runs.jsonl').open('a') as f:
                        f.write(json.dumps(row) + '\n')
        summary = {'runs': len(rows), 'synthetic_executor': synthetic,
                   'accepted': {v: sum(r['accepted'] for r in rows if r['variant'] == v) for v in ('baseline', 'candidate')},
                   'limitations': ['No token telemetry collected.', 'No security sandbox; executor adapter must isolate host/global skills, start fresh sessions, and avoid network/tool installs.', 'Acceptance covers fixture assertions only; not a general safety or quality claim.']}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'evals/executable.json')
    parser.add_argument('--executor', required=True, help='JSON argv, with {workspace}, {prompt} (file), {model}, {variant}')
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill', type=Path, default=Path(__file__).resolve().parents[1] / 'skills/astra-code')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--check-timeout', type=float, default=60)
    parser.add_argument('--synthetic', action='store_true', help='Explicitly label a test/fake executor; never a model benchmark')
    args = parser.parse_args()
    try:
        rows = run(args.manifest, json.loads(args.executor), args.model, args.output, args.skill,
                   args.repeats, args.timeout, args.check_timeout, args.synthetic)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        parser.exit(2, f'eval-runner: {exc}\n')
    print(json.dumps({'runs': len(rows), 'output': str(args.output), 'synthetic': args.synthetic}))
    return 0 if all(r['accepted'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
