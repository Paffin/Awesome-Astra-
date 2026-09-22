"""Synthetic protocol fixture, not a real language analyzer."""
import json
import sys
import subprocess
import time


def receive():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            raise EOFError
        if line == b"\r\n":
            break
        key, value = line.decode().split(":", 1)
        headers[key.lower()] = value.strip()
    return json.loads(sys.stdin.buffer.read(int(headers["content-length"])))


def send(data):
    raw = json.dumps({"jsonrpc": "2.0", **data}).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
    sys.stdout.buffer.flush()


mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
while True:
    try:
        msg = receive()
    except EOFError:
        break
    method = msg.get("method")
    if method == "initialize":
        if mode == "timeout":
            time.sleep(10)
        send({"id": msg["id"], "result": {"capabilities": {"referencesProvider": mode != "unsupported"}}})
        if mode == "blocked-write":
            time.sleep(10)
        if mode == "inherited-pipe":
            subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    elif method == "textDocument/references":
        send({"id": "config", "method": "workspace/configuration", "params": {"items": [{}]}})
        assert receive()["result"] == [None]
        if mode == "error":
            send({"id": msg["id"], "error": {"code": -32603, "message": "fixture error"}})
            continue
        if mode == "utf16":
            assert msg["params"]["position"]["character"] == 3
        pos = msg["params"]["position"]
        send({"id": msg["id"], "result": [
            {"uri": msg["params"]["textDocument"]["uri"], "range": {"start": pos, "end": pos}},
            {"uri": "file:///outside/private.txt", "range": {"start": pos, "end": pos}}]})
