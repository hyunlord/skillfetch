#!/usr/bin/env python3
"""Answer the skillfetch claude-code queue (~/.skillfetch/claude-code-queue) with isolated `claude -p` calls.

For each pending/<sha>.json without answers/<sha>.json: system prompt = systems/<system_sha256>.txt; user prompt = the
request's user message(s) plus the JSON schema and an output-format line; no tools, no MCP servers, project-only
settings, a neutral cwd (stage 6 batch.py). The reply's JSON object is written to answers/<sha>.json as {"text": ...};
skillfetch validates it on the next ingest run. Usage records (tokens, cost, seconds) go to answer-log.jsonl here.
Usage: answer_queue.py [--workers N] [--limit N]"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

Q = Path("~/.skillfetch/claude-code-queue").expanduser()
HERE = Path(__file__).resolve().parent
LOG = HERE / "answer-log.jsonl"
ISO = Path(tempfile.gettempdir()) / "staging30-iso"
_lock = threading.Lock()


def _env():
    e = dict(os.environ)
    for k in list(e):
        if k in ("CLAUDECODE", "VIRTUAL_ENV", "UV") or k.startswith("CLAUDE_CODE_"):
            e.pop(k)
    return e


def first_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    start = body.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    return json.JSONDecoder().raw_decode(body[start:])[0]


def answer(pending: Path) -> dict:
    sha = pending.stem
    out = Q / "answers" / f"{sha}.json"
    if out.exists():
        return {"sha": sha, "skipped": True}
    req = json.loads(pending.read_text())
    system_file = Q / "systems" / f"{req['system_sha256']}.txt"
    msgs = req["messages"]
    if len(msgs) == 1:
        convo = msgs[0]["content"]
    else:  # a correction round: the request, the earlier answer, the validation feedback
        parts = []
        for m in msgs:
            label = "Your earlier answer" if m["role"] == "assistant" else "Request" if not parts else "Feedback"
            parts.append(f"[{label}]\n{m['content']}")  # no leading "-": the CLI would read an option
        convo = "\n\n".join(parts)
    prompt = (f"{convo}\n\nReply with one JSON object that matches this JSON schema, and nothing else:\n"
              f"{json.dumps(req['schema'], ensure_ascii=False)}")
    ISO.mkdir(parents=True, exist_ok=True)
    (ISO / "mcp.json").write_text('{"mcpServers":{}}')
    cmd = ["claude", "-p", prompt, "--system-prompt-file", str(system_file), "--tools", "", "--strict-mcp-config",
           "--mcp-config", str(ISO / "mcp.json"), "--setting-sources", "project", "--output-format", "json",
           "--no-session-persistence"]
    t0, rec = time.time(), {"sha": sha}
    for attempt in range(3):
        p = subprocess.run(cmd, cwd=ISO, env=_env(), capture_output=True, text=True, timeout=1800,
                           stdin=subprocess.DEVNULL)
        try:
            j = json.loads(p.stdout)
            if j.get("is_error"):
                raise ValueError(str(j.get("result"))[:200])
            obj = first_json(j.get("result") or "")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"text": json.dumps(obj, ensure_ascii=False)}, ensure_ascii=False))
            rec.update(ok=True, usage=j.get("usage"), cost_usd=j.get("total_cost_usd"), attempts=attempt + 1)
            break
        except (ValueError, json.JSONDecodeError) as exc:
            rec.update(ok=False, error=str(exc)[:300], attempts=attempt + 1)
            time.sleep(5 * (attempt + 1))
    rec["secs"] = round(time.time() - t0, 1)
    with _lock, LOG.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    todo = sorted(p for p in (Q / "pending").glob("*.json") if not (Q / "answers" / p.name).exists())
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(todo)} pending without an answer", flush=True)
    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for rec in ex.map(answer, todo):
            done += 1
            if done % 25 == 0 or not rec.get("ok", True):
                print(f"{done}/{len(todo)} {rec.get('sha', '')[:12]} ok={rec.get('ok')} {rec.get('error', '')[:80]}",
                      flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
