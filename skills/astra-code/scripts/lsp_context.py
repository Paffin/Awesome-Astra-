#!/usr/bin/env python3
"""Query an explicitly selected stdio LSP server for symbol references.

Any language ID/server may be supplied. Servers are external trusted programs;
their indexing completeness is not guaranteed by this client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import repo_index


def read_message(stream):
    headers = {}
    while True:
        line = stream.readline(8193)
        if not line:
            raise EOFError("LSP server closed stdout")
        if len(line) > 8192:
            raise ValueError("Oversized LSP header")
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode("ascii").split(":", 1)
        headers[key.lower()] = value.strip()
    size = int(headers["content-length"])
    if not 0 <= size <= 16_000_000:
        raise ValueError("Oversized LSP response")
    body = bytearray()
    while len(body) < size:
        part = stream.read(size - len(body))
        if not part:
            raise EOFError("Truncated LSP response")
        body.extend(part)
    return json.loads(body)


class Client:
    def __init__(self, command, root, timeout):
        self.timeout = timeout
        self.root = root
        self.sequence = 0
        self.messages = queue.Queue(maxsize=1024)
        self.stopped = threading.Event()
        self.process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
            start_new_session=(os.name == "posix"))
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            while not self.stopped.is_set():
                message = read_message(self.process.stdout)
                while not self.stopped.is_set():
                    try:
                        self.messages.put(message, timeout=.1)
                        break
                    except queue.Full:
                        pass
        except Exception as exc:
            try:
                self.messages.put_nowait(exc)
            except queue.Full:
                pass

    def send(self, message):
        body = json.dumps({"jsonrpc": "2.0", **message}).encode()
        frame = f"Content-Length: {len(body)}\r\n\r\n".encode() + body
        finished = queue.Queue(maxsize=1)
        def write():
            try:
                view = memoryview(frame)
                while view:
                    written = self.process.stdin.write(view)
                    if not written:
                        raise EOFError("LSP server stdin closed")
                    view = view[written:]
                finished.put(None)
            except Exception as exc:
                finished.put(exc)
        threading.Thread(target=write, daemon=True).start()
        try:
            result = finished.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise TimeoutError("LSP write timeout") from exc
        if result is not None:
            raise result

    def notify(self, method, params):
        self.send({"method": method, "params": params})

    def request(self, method, params):
        self.sequence += 1
        identity = self.sequence
        self.send({"id": identity, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"LSP timeout: {method}")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError(f"LSP timeout: {method}") from exc
            if isinstance(message, Exception):
                raise message
            if "method" in message and "id" in message:
                requested = message["method"]
                if requested == "workspace/configuration":
                    result = [None for _ in message.get("params", {}).get("items", [])]
                elif requested == "workspace/workspaceFolders":
                    result = [{"uri": self.root.as_uri(), "name": self.root.name}]
                elif requested == "window/workDoneProgress/create":
                    result = None
                else:
                    self.send({"id": message["id"], "error": {"code": -32601,
                              "message": "Unsupported client request; workspace edits prohibited"}})
                    continue
                self.send({"id": message["id"], "result": result})
            elif message.get("id") == identity:
                if "error" in message:
                    raise ValueError(f"LSP request failed: {message['error']}")
                return message.get("result")

    def close(self):
        self.stopped.set()
        if os.name == "posix":
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()


def snapshot(root):
    files = {}
    for path in repo_index.inventory(root):
        source = None if repo_index.excluded(path, []) else repo_index.read_source(root, path)
        if source:
            files[path] = source[1]
    return files


def query(root, file, line, column, language, command, timeout=30, open_files=()):
    root, _ = repo_index.locations(root)
    file = Path(file)
    if file.is_absolute() or ".." in file.parts:
        raise ValueError("file must be repository-relative")
    source = repo_index.read_source(root, file.as_posix())
    before = snapshot(root)
    documents = {file.as_posix(): source}
    for extra in open_files:
        path = Path(extra)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("open-file must be repository-relative")
        value = repo_index.read_source(root, path.as_posix())
        if value is None or before.get(path.as_posix()) != value[1]:
            raise ValueError("Additional document missing, excluded or changed")
        documents[path.as_posix()] = value
    if source is None or before.get(file.as_posix()) != source[1]:
        raise ValueError("Target missing, excluded or changed")
    lines = source[0].split("\n")
    if not 1 <= line <= len(lines) or not 1 <= column <= len(lines[line-1].rstrip("\r")) + 1:
        raise ValueError("line/column outside source (1-based Unicode characters)")
    # LSP defaults to UTF-16; explicitly negotiate only this encoding.
    character = len(lines[line-1][:column-1].encode("utf-16-le")) // 2
    uri = (root / file).as_uri()
    client = Client(command, root, timeout)
    try:
        initialized = client.request("initialize", {"processId": None, "rootUri": root.as_uri(),
            "workspaceFolders": [{"uri": root.as_uri(), "name": root.name}],
            "capabilities": {"general": {"positionEncodings": ["utf-16"]},
                "workspace": {"configuration": True, "workspaceFolders": True}}})
        caps = initialized.get("capabilities", {})
        if caps.get("positionEncoding", "utf-16") != "utf-16":
            raise ValueError("Server selected unsupported position encoding")
        if caps.get("referencesProvider") is not True and not isinstance(caps.get("referencesProvider"), dict):
            raise ValueError("Server does not advertise references support")
        client.notify("initialized", {})
        for path, document in documents.items():
            client.notify("textDocument/didOpen", {"textDocument": {"uri": (root / path).as_uri(),
                "languageId": language, "version": 1, "text": document[0]}})
        references = client.request("textDocument/references", {"textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": character},
            "context": {"includeDeclaration": True}})
        if references is None:
            references = []
        if not isinstance(references, list):
            raise ValueError("Invalid LSP reference response")
        accepted, unresolved = [], 0
        for item in references:
            parsed = urlparse(item["uri"])
            if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
                unresolved += 1
                continue
            try:
                relative = Path(unquote(parsed.path)).relative_to(root).as_posix()
            except ValueError:
                unresolved += 1
                continue
            if relative not in before:
                unresolved += 1
                continue
            accepted.append({"path": relative, "range": item["range"],
                             "sha256": before[relative], "evidence": "language-server reference"})
        if snapshot(root) != before:
            raise ValueError("Working tree changed during LSP query; retry")
        return {"provider": "lsp", "language": language, "opened_files": list(documents),
            "snapshot_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
            "position_encoding": "utf-16", "references": accepted,
            "unresolved_locations": unresolved, "whole_project_verified": False,
            "limitations": ["Server startup response does not guarantee completed workspace indexing",
                "References cover this symbol and server workspace, not all wire contracts or external consumers"]}
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--file", required=True)
    parser.add_argument("--line", type=int, required=True)
    parser.add_argument("--column", type=int, required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--open-file", action="append", default=[], help="additional same-language document; repeatable")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-bytes", type=int, default=100000)
    parser.add_argument("--server", required=True, help='JSON argv array, e.g. ["gopls"]')
    args = parser.parse_args()
    try:
        command = json.loads(args.server)
        if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
            raise ValueError("server must be nonempty JSON string array")
        if not 0 < args.timeout <= 300 or args.max_bytes < 512:
            raise ValueError("Require timeout 0..300 seconds and max-bytes >=512")
        report = query(args.root, args.file, args.line, args.column, args.language, command, args.timeout, args.open_file)
        output = repo_index.encoded(report)
        if len(output.encode()) > args.max_bytes:
            raise ValueError("References exceed budget; increase max-bytes. No partial result emitted")
        print(output, end="")
    except (OSError, ValueError, KeyError, TypeError, EOFError, TimeoutError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"lsp-context: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
