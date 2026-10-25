#!/usr/bin/env python3
"""Minimal MCP stdio client for skillselion-mcp@0.9.11 (npx), one server process, sequential tool calls with >= 1 s
between calls. Env: DO_NOT_TRACK=1, SK_NO_DEMAND=1, GITHUB_TOKEN only with gh_token=True
(main run; read from <credentials file> into the child env, never written anywhere); cwd = stage8/iso (empty). Every call's raw result
and wall time are appended to raw/<run>.jsonl."""
import json
import os
import subprocess
import time
from pathlib import Path

S8 = Path(__file__).resolve().parents[1]
PKG = "skillselion-mcp@0.9.11"


CREDS = Path.home() / "<credentials file>"


def _gh_token():
    """GITHUB_PAT_TOKEN from <credentials file> (read-only fine-grained, given by the user); returned, never printed."""
    for line in CREDS.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if line.startswith("GITHUB_PAT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("GITHUB_PAT_TOKEN not in <credentials file>")


class SS:
    def __init__(self, run, gh_token=False):
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
        env.update({"DO_NOT_TRACK": "1", "SK_NO_DEMAND": "1"})
        if gh_token:  # only into the server child's env (stage8 DESIGN §2-추가 1)
            env["GITHUB_TOKEN"] = _gh_token()
        (S8 / "iso").mkdir(exist_ok=True)
        self.p = subprocess.Popen(["npx", "-y", PKG], cwd=S8 / "iso", env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=open(S8 / "raw" / f"{run}.stderr", "a"), text=True, bufsize=1)
        self.n, self.last, self.log = 0, 0.0, open(S8 / "raw" / f"{run}.jsonl", "a")
        r = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "skillfetch-e2e-stage8", "version": "0"}})
        self.server_info = r.get("result", {}).get("serverInfo")
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.p.stdin.flush()

    def _rpc(self, method, params):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("server closed")
            msg = json.loads(line)
            if msg.get("id") == self.n:
                return msg

    def tool(self, task_id, kind, name, args):
        wait = 1.0 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        t0 = time.time()
        r = self._rpc("tools/call", {"name": name, "arguments": args})
        dt = round(time.time() - t0, 3)
        self.last = time.time()
        text = "\n".join(c.get("text", "") for c in (r.get("result") or {}).get("content", []) if c.get("type") == "text")
        rec = {"task": task_id, "kind": kind, "tool": name, "args": args, "wall_s": dt, "error": r.get("error"),
               "is_error": (r.get("result") or {}).get("isError"), "text": text, "ts": int(t0)}
        self.log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.log.flush()
        return rec

    def close(self):
        self.p.terminate()
