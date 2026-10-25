#!/usr/bin/env python3
"""Stage 0.5: extract runs-0.5/<cond>/<id>.* into runs-0.5/_extract.json (reuses extract.py + MCP timing)."""
import json
import re
from datetime import datetime
from pathlib import Path

import yaml

import extract as ex

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs-0.5"
CONDS = ("R1", "R1R2")
CONNECT_RE = re.compile(r'^(\S+) \[DEBUG\] MCP server "skillfetch": Successfully connected .* in (\d+)ms')
START_RE = re.compile(r'^(\S+) \[DEBUG\] MCP server "skillfetch": Starting connection')
FAIL_RE = re.compile(r'^(\S+) \[\w+\] MCP server "skillfetch": (Connection failed|.*timed out|.*Failed to connect)', re.I)
# the skillfetch reminder line only (the user's global UserPromptSubmit hooks also log "success")
HOOK_RE = re.compile(r"^(\S+) \[DEBUG\] .*Hook UserPromptSubmit.*you have not yet called skillfetch")


def iso_ms(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def timing(runs, tid, spawn):
    out = {"spawn_epoch_ms": spawn}
    dbg = runs / f"{tid}.debug.log"
    if dbg.exists():
        for line in dbg.read_text(errors="replace").splitlines():
            for key, rx in (("mcp_start_ms", START_RE), ("mcp_ready_ms", CONNECT_RE), ("hook_ms", HOOK_RE)):
                m = rx.match(line)
                if m and key not in out:
                    out[key] = iso_ms(m.group(1)) - spawn
                    if key == "mcp_ready_ms":
                        out["mcp_connect_reported_ms"] = int(m.group(2))
            m = FAIL_RE.match(line)
            if m and "mcp_fail" not in out:
                out["mcp_fail"] = line[:300]
    # receive time of each stdout line -> init event, first tool call, first skillfetch call
    ts = [int(x) for x in (runs / f"{tid}.ts").read_text().split()] if (runs / f"{tid}.ts").exists() else []
    lines = (runs / f"{tid}.jsonl").read_text().splitlines()
    for i, line in enumerate(lines[: len(ts)]):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "system" and e.get("subtype") == "init" and "init_ms" not in out:
            out["init_ms"] = ts[i] - spawn
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            for c in e["message"].get("content", []):
                if c["type"] == "tool_use":
                    out.setdefault("first_tool_ms", ts[i] - spawn)
                    if c["name"].startswith(ex.SF):
                        out.setdefault("first_sf_call_ms", ts[i] - spawn)
                    if c["name"] == "ToolSearch":
                        out.setdefault("first_toolsearch_ms", ts[i] - spawn)
    return out


def main():
    cfg = yaml.safe_load((ROOT / "tasks.yaml").read_text())
    rows = []
    for cond in CONDS:
        runs = OUT / cond
        ex.RUNS = runs
        for t in cfg["tasks"]:
            if not (runs / f"{t['id']}.meta.json").exists():
                continue
            r = ex.extract(t)
            r["cond"] = cond
            if t["repo"] == "fastapi":
                r["junit"] = ex.junit_summary(r["meta"].get("tests", {}).get("junit"),
                                              set((ROOT / "runs" / "baseline_fastapi_tests.txt").read_text().split()))
            r["timing"] = timing(runs, t["id"], r["meta"]["session"]["spawn_epoch_ms"])
            r["skillfetch_hook_injected"] = "hook_ms" in r["timing"]
            rows.append(r)
    (OUT / "_extract.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in rows:
        tm = r["timing"]
        print(r["cond"], r["id"], r["chain"], r["num_turns"], r["result_subtype"], "init=", r["init_skillfetch_status"],
              "ready=", tm.get("mcp_ready_ms"), "init_ms=", tm.get("init_ms"), "sf1=", tm.get("first_sf_call_ms"),
              "loaded=", r["loaded_ids"])


if __name__ == "__main__":
    main()
