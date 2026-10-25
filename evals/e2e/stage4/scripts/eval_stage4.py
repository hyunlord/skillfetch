#!/usr/bin/env python3
"""Stage 4 metrics from runs/E{1,2}/<task>-r{1,2,3}.* -> sessions.jsonl, summary.json.

Per session (main thread only; subagent messages carry parent_tool_use_id and are skipped):
- fired: any mcp__skillfetch__* call. Path (a): Skill(skillfetch-router) or a Read of the router SKILL.md before the
  first skillfetch call; (b) a skillfetch call without either. router_no_mcp: the router was invoked, no skillfetch call.
- first search turn: 1-based index of the main-thread assistant message holding the first search_skills call; its
  time and the first skillfetch call's time are ms after spawn (runs/*.ts gives each stdout line's epoch ms); MCP ready
  = the debug log's 'MCP server "skillfetch": Successfully connected' time after the init event.
- capped: result subtype error_max_turns.
- top50: ids in the first search_skills result; loaded: ids in load_skills results (all calls).
- searched_no_load cause (searched, no load_skills call):
    resolve_stop  resolve_set was called and the session did not end at the cap within 2 tool calls of it;
    none          resolve_set was never called and the session did not end at the cap within 2 tool calls of the
                  search;
    cap           otherwise (the session ended at the 16-turn cap within 2 tool calls of its last skillfetch call).
- first-tool attribution (first main-thread tool call, rules in DESIGN.md order):
    omc_hook      a UserPromptSubmit hook added context containing "<E2 hook text>" before it and it is
                  Skill(<E2 plugin>:*)
    other_skill   Skill(...) other than the router
    rules_git     Bash whose command contains `git status` or `git branch`
    explore       Read / Glob / Grep, a non-git Bash, or a ToolSearch that is not for skillfetch
    router_first  Skill(skillfetch-router), a Read of the router SKILL.md, a skillfetch call, or a ToolSearch for it
- vs oracle (relevant = grade >= 2): precision, recall, hit, wrong loads; class with the offline rules, using the
  session's own top50 for select_fail and the offline Q1/Q2/Q3 top-50 for restate_fail; no_search when it never
  searched (loaded nothing).
"""
from __future__ import annotations

import itertools
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

S4 = Path(__file__).resolve().parents[1]
ENVS = ("E1", "E2")
SF = "mcp__skillfetch__"


def jl(path):
    return [json.loads(l) for l in path.open() if l.strip()]


def tool_text(content):
    if isinstance(content, list):
        return "".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content or "")


def parse(jsonl: Path):
    lines = jsonl.read_text().splitlines()
    ts_path = Path(str(jsonl)[: -len(".jsonl")] + ".ts")
    ts = [int(x) for x in ts_path.read_text().split()] if ts_path.is_file() else []
    meta = json.loads(Path(str(jsonl)[: -len(".jsonl")] + ".meta.json").read_text())
    spawn = meta["spawn_epoch_ms"]
    ev = []
    for i, l in enumerate(lines):
        try:
            e = json.loads(l)
        except ValueError:
            continue
        e["_ms"] = (ts[i] - spawn) if i < len(ts) else None
        ev.append(e)
    init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(ev) if e.get("type") == "result"), {})
    calls, results = [], {}
    turn = 0
    hook_ctx_before_first = []
    for e in ev:
        if e.get("type") == "system" and e.get("subtype") == "hook_response" and not calls:
            if e.get("hook_event") == "UserPromptSubmit":
                hook_ctx_before_first.append(json.dumps(e.get("output") or e.get("stdout") or ""))
        if e.get("parent_tool_use_id"):
            continue
        if e.get("type") == "assistant":
            turn += 1
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    calls.append({"id": c["id"], "name": c["name"], "input": c.get("input") or {}, "turn": turn,
                                  "ms": e["_ms"]})
        elif e.get("type") == "user":
            content = e.get("message", {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        results[c.get("tool_use_id")] = tool_text(c.get("content"))
    return meta, init, result, calls, results, hook_ctx_before_first


def is_router(c):
    if c["name"] == "Skill":
        return "skillfetch-router" in str(c["input"].get("skill") or c["input"].get("command") or "")
    if c["name"] == "Read":
        return "skillfetch-router" in str(c["input"].get("file_path", ""))
    return False


def first_tool_class(calls, hook_ctx):
    if not calls:
        return "none"
    c = calls[0]
    name, inp = c["name"], c["input"]
    skill = str(inp.get("skill") or inp.get("command") or "")
    if name == "Skill" and skill.startswith("<E2 plugin>:") and any("<E2 hook text>" in h for h in hook_ctx):
        return "omc_hook"
    if is_router(c) or name.startswith(SF) or (name == "ToolSearch" and "skillfetch" in json.dumps(inp)):
        return "router_first"
    if name == "Skill":
        return "other_skill"
    if name == "Bash" and re.search(r"git\s+(status|branch)", str(inp.get("command", ""))):
        return "rules_git"
    return "explore"


def json_payload(text):
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None


def mcp_ready_ms(debug: Path, init_ms):
    if not debug.is_file():
        return None
    first = None
    for line in debug.open(errors="replace"):
        if first is None:
            m0 = re.match(r"(\d{4}-\d\d-\d\dT[\d:.]+Z)", line)
            if m0:
                first = m0.group(1)
        if 'MCP server "skillfetch": Successfully connected' in line:
            m = re.match(r"(\d{4}-\d\d-\d\dT[\d:.]+Z)", line)
            if m and first:
                fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
                return int((datetime.strptime(m.group(1), fmt) - datetime.strptime(first, fmt)).total_seconds() * 1000)
    return None


def session(env, jsonl, tasks, oracle, rank):
    meta, init, result, calls, results, hook_ctx = parse(jsonl)
    task = meta["task"]
    sf = [c for c in calls if c["name"].startswith(SF)]
    first_sf = sf[0] if sf else None
    router_idx = next((i for i, c in enumerate(calls) if is_router(c)), None)
    first_sf_idx = calls.index(first_sf) if first_sf else None
    router_called = router_idx is not None
    path = None
    if first_sf:
        path = "a" if router_called and router_idx < first_sf_idx else "b"
    searches = [c for c in sf if c["name"] == SF + "search_skills"]
    resolves = [c for c in sf if c["name"] == SF + "resolve_set"]
    loads = [c for c in sf if c["name"] == SF + "load_skills"]
    top50 = []
    if searches:
        p = json_payload(results.get(searches[0]["id"], "")) or {}
        top50 = [r["id"] for r in p.get("results", []) if isinstance(r, dict) and "id" in r]
    loaded = []
    for c in loads:
        p = json_payload(results.get(c["id"], "")) or {}
        loaded += [s["id"] for s in p.get("skills", []) if isinstance(s, dict) and "id" in s]
    loaded = list(dict.fromkeys(loaded))
    capped = result.get("subtype") == "error_max_turns"
    cause = None
    if searches and not loads:
        last = resolves[-1] if resolves else searches[-1]
        near_end = capped and len(calls) - 1 - calls.index(last) <= 2
        cause = "cap" if near_end else ("resolve_stop" if resolves else "none")
    R = set(oracle[task]["relevant"])
    local = [s for s in loaded if s.startswith("path:")]  # pinned project skills: not in the index, not graded
    S = set(loaded) - set(local)
    rk = rank[task]
    if not searches:
        cls = "no_search"
    elif not R:
        cls = "over_load" if S else "ok"
    elif S & R:
        cls = "ok"
    elif R & set(top50):
        cls = "select_fail"
    elif R & (set(rk["q1"][:50]) | set(rk["q2"][:50]) | set(rk["q3"][:50])):
        cls = "restate_fail"
    else:
        cls = "search_fail"
    debug = Path(str(jsonl)[: -len(".jsonl")] + ".debug.log")
    return {
        "env": env, "task": task, "rep": meta["tag"], "offline_class": tasks[task]["offline_class"],
        "subtype": result.get("subtype"), "capped": capped, "num_turns": result.get("num_turns"),
        "main_turns": max([c["turn"] for c in calls], default=0),
        "cost_usd": result.get("total_cost_usd"), "duration_ms": result.get("duration_ms"), "wall_s": meta.get("wall_s"),
        "input_tokens": sum((result.get("usage") or {}).get(k, 0) or 0 for k in
                            ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        "fired": bool(sf), "path": path, "router_called": router_called, "router_no_mcp": router_called and not sf,
        "searched": bool(searches), "resolved": bool(resolves), "loaded_any": bool(loaded),
        "first_search_turn": searches[0]["turn"] if searches else None,
        "first_search_ms": searches[0]["ms"] if searches else None,
        "first_sf_ms": first_sf["ms"] if first_sf else None,
        "mcp_ready_ms": mcp_ready_ms(debug, None),
        "queries": (searches[0]["input"].get("queries") or [searches[0]["input"].get("query")]) if searches else None,
        "top50": top50, "loaded": loaded, "local_pins": local, "searched_no_load": cause,
        "first_tool": calls[0]["name"] + (f"({calls[0]['input'].get('skill')})" if calls and calls[0]["name"] == "Skill" else "") if calls else None,
        "first_tool_class": first_tool_class(calls, hook_ctx), "class": cls,
        "precision": (len(S & R) / len(S)) if S else None, "recall": (len(S & R) / len(R)) if R else None,
        "hit": bool(S & R) if R else None, "wrong_loads": len(S - R),
        "offline_skills": tasks[task]["offline_skills"],
        "init": {"mcp_servers": [s.get("name") for s in init.get("mcp_servers", [])],
                 "plugins": [p.get("name") if isinstance(p, dict) else p for p in init.get("plugins", [])],
                 "skills_n": len(init.get("skills", []) or []), "agents_n": len(init.get("agents", []) or []),
                 "tools_n": len(init.get("tools", []) or [])},
        "hook_events": sorted({e for e in hook_event_names(jsonl)}),
    }


def hook_event_names(jsonl):
    for e in jl(jsonl):
        if e.get("type") == "system" and e.get("subtype") == "hook_started":
            yield e.get("hook_event")


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def main():
    tasks = {t["id"]: t for t in jl(S4 / "tasks.jsonl")}
    oracle, rank = {}, {}
    # round 1 and 2 candidates, then the 29 tasks after the 4-0 grading of loaded / picked skills (wins)
    for path in (S4 / "oracle.jsonl", S4 / "oracle-r2.jsonl", S4 / "oracle-v3.jsonl"):
        oracle.update({o["id"]: o for o in jl(path)})
    for path in sorted(S4.glob("rankings*.json")):
        rank.update(json.loads(path.read_text()))
    rows = []
    for env in ENVS:
        for f in sorted((S4 / "runs" / env).glob("s4-*-r[123].jsonl")):
            if Path(str(f)[: -len(".jsonl")] + ".meta.json").exists():
                rows.append(session(env, f, tasks, oracle, rank))
    (S4 / "sessions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(len(rows), "sessions")


if __name__ == "__main__":
    main()
