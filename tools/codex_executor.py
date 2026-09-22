#!/usr/bin/env python3
"""Fresh Codex CLI execution adapter for run_evals.py; retains host safety policy.

Use a dedicated evaluation account/container with no globally installed target
skill. This adapter does not alter HOME, credentials, approvals or global config.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--prompt', required=True, type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--variant', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--explicit-skill', action='store_true',
                        help='Candidate explicitly invokes astra-code; default measures implicit discovery')
    args = parser.parse_args()
    executable = shutil.which(args.codex)
    if not executable:
        parser.exit(2, 'codex executor: Codex CLI not installed; no model run performed\n')
    workspace = args.workspace.resolve()
    target = workspace / '.agents/skills/astra-code/SKILL.md'
    if target.is_file() != (args.variant == 'candidate'):
        parser.exit(2, 'codex executor: workspace skill does not match variant\n')
    try:
        prompt = args.prompt.read_text(encoding='utf-8')
        if args.explicit_skill and args.variant == 'candidate':
            prompt = '$astra-code\n' + prompt
        argv = [executable, 'exec', '--ephemeral', '--json', '--sandbox',
                'workspace-write', '--model', args.model, '-']
        # Inherit the runner's process group so its deadline also kills Codex.
        return subprocess.run(argv, cwd=workspace, input=prompt, text=True).returncode
    except (OSError, ValueError) as exc:
        parser.exit(2, f'codex executor: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
