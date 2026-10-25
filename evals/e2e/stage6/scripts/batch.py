"""Isolated `claude -p` batch calls for stage 6 (kind labels, selection, grading).

Each call: no tools, no MCP servers, project-only settings (no user hooks / plugins / CLAUDE.md), the fixed part of
the prompt as the system prompt file (identical across a batch, so it is served from the prompt cache), the
variable part as the user prompt. Results are cached on disk by name, so a rerun only makes the missing calls.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S6 = Path(__file__).resolve().parents[1]
RAW = S6 / "gen" / "raw"
ISO = Path(tempfile.gettempdir()) / "stage6-iso"  # neutral cwd: no project CLAUDE.md, no .mcp.json


def _env():
    e = dict(os.environ)
    for k in list(e):
        if k in ("CLAUDECODE", "VIRTUAL_ENV", "UV") or k.startswith("CLAUDE_CODE_"):
            e.pop(k)
    return e


def call(name: str, system_file: Path, prompt: str, timeout: int = 1800) -> dict:
    """One call; returns {"name", "text", "usage", "duration_ms", "is_error"} and caches it under gen/raw/<name>.json."""
    out = RAW / f"{name}.json"
    if out.exists():
        return json.loads(out.read_text())
    RAW.mkdir(parents=True, exist_ok=True)
    ISO.mkdir(parents=True, exist_ok=True)
    (ISO / "mcp.json").write_text('{"mcpServers":{}}')
    cmd = ["claude", "-p", prompt, "--system-prompt-file", str(system_file), "--tools", "", "--strict-mcp-config",
           "--mcp-config", str(ISO / "mcp.json"), "--setting-sources", "project", "--output-format", "json",
           "--no-session-persistence"]
    t0 = time.time()
    for attempt in range(3):
        p = subprocess.run(cmd, cwd=ISO, env=_env(), capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        try:
            j = json.loads(p.stdout)
        except json.JSONDecodeError:
            j = {"is_error": True, "result": p.stdout[-500:] + p.stderr[-500:]}
        if not j.get("is_error"):
            break
        time.sleep(10 * (attempt + 1))
    rec = {"name": name, "text": j.get("result") or "", "usage": j.get("usage"), "duration_ms": j.get("duration_ms"),
           "cost_usd": j.get("total_cost_usd"), "is_error": bool(j.get("is_error")), "secs": round(time.time() - t0, 1)}
    if not rec["is_error"]:
        out.write_text(json.dumps(rec, ensure_ascii=False))
    return rec


def run_all(jobs: list[tuple[str, Path, str]], workers: int = 6) -> list[dict]:
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda j: call(*j), jobs))


def parse_json(text: str):
    """The JSON value in a model reply (bare, or inside a ```json fence)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    start = min([i for i in (body.find("["), body.find("{")) if i >= 0], default=0)
    return json.JSONDecoder().raw_decode(body[start:])[0]  # ignores any text after the JSON value


def parse_json_last(text: str):
    """The last top-level JSON array/object in a reply (a reply that corrects itself ends with its final answer)."""
    dec, i, last = json.JSONDecoder(), 0, None
    while True:
        cand = [j for j in (text.find("[", i), text.find("{", i)) if j >= 0]
        if not cand:
            break
        j = min(cand)
        try:
            val, end = dec.raw_decode(text[j:])
            last, i = val, j + end
        except json.JSONDecodeError:
            i = j + 1
    if last is None:
        raise ValueError("no JSON in reply")
    return last


def resolve_ids(ids, valid):
    """Model ids -> catalog ids: exact, or `source/name` without the @hash when that name is unique."""
    by_name = {v.split("@")[0]: v for v in valid}
    by_hash = {v.split("@")[1]: v for v in valid if "@" in v}
    bare = {}
    for v in valid:
        bare.setdefault(v.split("/", 1)[-1].split("@")[0], []).append(v)
    out, dropped = [], []
    for s in ids:
        s = str(s).strip()
        v = s if s in valid else by_name.get(s.split("@")[0]) or (by_hash.get(s.split("@")[1]) if "@" in s else None)
        if v is None:  # wrong source prefix: the bare name, when unique
            hit = bare.get(s.split("/", 1)[-1].split("@")[0], [])
            v = hit[0] if len(hit) == 1 else None
        (out if v else dropped).append(v or s)
    return list(dict.fromkeys(out)), dropped
