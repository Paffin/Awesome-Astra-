#!/usr/bin/env python3
"""Record explicit command execution; receipts detect accidental changes, not forgery.

Commands run with user privileges, without a shell. Output may contain secrets;
receipts and bounded logs must be stored outside the target working tree.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import shutil
import stat
import platform
import sys
import subprocess
import threading
import time

import repo_index


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def snapshot(root, exclude=None):
    files = {}
    for path in repo_index.inventory(root):
        source = None if repo_index.excluded(path, exclude or []) else repo_index.read_source(root, path)
        if source:
            files[path] = source[1]
    return {"sha256": digest(files), "files": files}


def external_path(root, receipt):
    receipt = Path(receipt).resolve()
    if receipt == root or root in receipt.parents:
        raise ValueError("receipt must be outside the target working tree")
    return receipt


def stop(proc):
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        elif proc.poll() is None:
            proc.kill()
    except ProcessLookupError:
        pass


def file_identity(path):
    """Read only regular files, recording hashes rather than file contents."""
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError("environment inputs must be regular files")
    with resolved.open("rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("environment inputs must be regular files")
        hasher = hashlib.sha256()
        for chunk in iter(lambda: source.read(1048576), b""):
            hasher.update(chunk)
    identity = {"path": str(path), "resolved": str(resolved), "sha256": hasher.hexdigest(),
                "mode": stat.S_IMODE(metadata.st_mode)}
    if os.name == "posix":
        identity.update(uid=metadata.st_uid, gid=metadata.st_gid)
    return identity


def observed_environment(root, argv, declaration=None):
    """Bind selected inputs; facts are declarations, never external observations.

    JSON: {"files": ["relative/to/declaration/lockfile", "/external/config"],
           "facts": {"database_schema": "reviewed version"}}.
    Facts must be non-secret JSON values; only their digest is stored. No probes
    or shell commands are inferred or run. This does not inventory dependencies,
    environment variables, shebang interpreters or remote services.
    """
    executable = argv[0]
    if os.path.dirname(executable):
        executable = str(root / executable) if not os.path.isabs(executable) else executable
    else:
        # Relative PATH entries are interpreted against the command's cwd.
        search_path = os.pathsep.join(str(root / p) if not os.path.isabs(p) else p
                                     for p in os.get_exec_path())
        executable = shutil.which(executable, path=search_path)
        if executable is None:
            raise ValueError("command executable cannot be resolved")
    result = {"executable": file_identity(executable),
              "recorder_python": file_identity(sys.executable),
              "python_version": platform.python_version(),
              "platform": {"system": platform.system(), "release": platform.release(),
                           "machine": platform.machine()},
              "declaration": None}
    if declaration is not None:
        declaration = Path(declaration).absolute()
        if not stat.S_ISREG(declaration.stat().st_mode):
            raise ValueError("environment declaration must be a regular file")
        if declaration.stat().st_size > 1048576:
            raise ValueError("environment declaration exceeds 1 MiB")
        raw = declaration.read_bytes()
        config = json.loads(raw)
        if not isinstance(config, dict) or set(config) - {"files", "facts"}:
            raise ValueError("environment declaration requires only files and facts")
        files, facts = config.get("files", []), config.get("facts", {})
        if (not isinstance(files, list) or len(files) > 256 or
                any(not isinstance(p, str) or not p or "\0" in p for p in files)):
            raise ValueError("environment files must be at most 256 nonempty path strings")
        if not isinstance(facts, dict):
            raise ValueError("environment facts must be a JSON object")
        # Reject non-standard JSON numeric values too.
        json.dumps(facts, allow_nan=False)
        identities = [file_identity(declaration.parent / p) for p in files]
        result["declaration"] = {"path": str(declaration),
            "resolved": str(declaration.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            "files": identities, "declared_facts_sha256": digest(facts),
            "facts_verified": False}
    return result


def run(root, argv, receipt, timeout=60, max_log_bytes=1048576, environment=None):
    root, _ = repo_index.locations(Path(root))
    receipt = external_path(root, receipt)
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or "\0" in a for a in argv):
        raise ValueError("argv must be a nonempty JSON array of strings")
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    if not isinstance(max_log_bytes, int) or not 1 <= max_log_bytes <= 16 * 1024 * 1024:
        raise ValueError("max_log_bytes must be between 1 and 16777216")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    log_path = receipt.with_suffix(receipt.suffix + ".log")
    before = snapshot(root)
    environment_before = observed_environment(root, argv, environment)
    # Exclusive creation prevents overwriting evidence from a previous run.
    with receipt.open("x", encoding="utf-8") as output:
        with log_path.open("xb") as log:
            started = time.monotonic()
            proc = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    start_new_session=os.name == "posix", bufsize=0)
            state = {"bytes_seen": 0, "bytes_saved": 0, "error": None}
            def drain():
                try:
                    while True:
                        chunk = proc.stdout.read(65536)
                        if not chunk:
                            break
                        state["bytes_seen"] += len(chunk)
                        keep = chunk[:max(0, max_log_bytes - state["bytes_saved"])]
                        log.write(keep)
                        state["bytes_saved"] += len(keep)
                except (OSError, ValueError) as exc:
                    state["error"] = str(exc)
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            timed_out = False
            try:
                proc.wait(timeout=timeout)
                reader.join(max(0, timeout - (time.monotonic() - started)))
                timed_out = reader.is_alive()
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                stop(proc)  # Kill surviving descendants even after parent exited.
                proc.wait(timeout=5)
                reader.join(2)
                proc.stdout.close()
            if reader.is_alive():
                state["error"] = "output reader did not terminate; descendant cleanup incomplete"
            log.flush()
            duration = time.monotonic() - started
        after = snapshot(root)
        try:
            environment_after = observed_environment(root, argv, environment)
            environment_error = None
        except (OSError, ValueError, TypeError) as exc:
            environment_after, environment_error = None, type(exc).__name__
        payload = {"schema": 2, "root": str(root), "cwd": str(root), "argv": argv,
                   "exit_code": proc.returncode, "timed_out": timed_out,
                   "duration_seconds": duration, "before": before, "after": after,
                   "environment_before": environment_before, "environment_after": environment_after,
                   "environment_error": environment_error,
                   "log": log_path.name, "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
                   "log_truncated": state["bytes_seen"] > state["bytes_saved"],
                   "output_error": state["error"],
                   "limitations": ["Local checksums are not signatures; a writer can forge this receipt",
                     "Snapshot excludes ignored, sensitive, oversized, binary and unreadable files",
                     "Snapshot is not a filesystem lock and does not identify external dependencies",
                     "Windows descendant cleanup is not guaranteed",
                     "Only explicit environment files and executable identities are observed; dependencies and inherited variables are not inventoried",
                     "Declared external facts are not automatically verified; hashes do not redact low-entropy secrets"]}
        json.dump({"payload": payload, "payload_sha256": digest(payload)}, output, indent=2)
        output.write("\n")
    return payload


def verify(root, receipt):
    root, _ = repo_index.locations(Path(root))
    receipt = external_path(root, receipt)
    if receipt.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("receipt exceeds size limit")
    data = json.loads(receipt.read_text())
    payload = data["payload"]
    errors = []
    if data.get("payload_sha256") != digest(payload):
        errors.append("receipt checksum mismatch")
    if payload.get("schema") not in (1, 2) or payload.get("root") != str(root) or payload.get("cwd") != str(root):
        errors.append("wrong receipt schema or repository")
    log_path = receipt.with_suffix(receipt.suffix + ".log")
    if payload.get("log") != log_path.name or log_path.is_symlink() or log_path.stat().st_size > 16 * 1024 * 1024:
        errors.append("invalid log path or size")
    elif hashlib.sha256(log_path.read_bytes()).hexdigest() != payload.get("log_sha256"):
        errors.append("log checksum mismatch")
    if payload.get("schema") == 2:
        try:
            previous = payload["environment_before"]
            declaration = previous.get("declaration")
            current_environment = observed_environment(root, payload["argv"],
                declaration["path"] if declaration is not None else None)
            if (previous != current_environment or payload.get("environment_after") != current_environment
                    or payload.get("environment_error") is not None):
                errors.append("stale environment or command modified declared inputs")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
            errors.append("environment inputs unavailable or invalid")
    current = snapshot(root)
    if payload.get("before") != current or payload.get("after") != current:
        errors.append("stale receipt or command modified eligible sources")
    if type(payload.get("exit_code")) is not int or payload["exit_code"] != 0 or payload.get("timed_out") is not False or payload.get("output_error") is not None:
        errors.append("command did not complete successfully")
    return {"recorded_check_passed": not errors, "errors": errors,
            "claim": "Local execution receipt consistency only; not authenticated proof of correctness"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "verify"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--argv", help="Explicit JSON argv; never interpreted by a shell")
    parser.add_argument("--environment", type=Path, help="run only: explicit JSON files/facts declaration; relative files resolve beside it")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-log-bytes", type=int, default=1048576)
    args = parser.parse_args()
    try:
        if args.action == "verify" and args.environment is not None:
            raise ValueError("verify uses the environment declaration recorded in the receipt")
        if args.action == "run":
            run(args.root, json.loads(args.argv or "null"), args.receipt, args.timeout, args.max_log_bytes, args.environment)
        result = verify(args.root, args.receipt)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"verification: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["recorded_check_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
