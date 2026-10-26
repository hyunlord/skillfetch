#!/usr/bin/env python3
"""Stage 11 per-session rows from stage11-private/runs/<cond>/<task>-<tag>.* (E1 only) -> stage11-private/sessions-<tags>.jsonl.
Same fields and parser as stage10/scripts/extract_s10.py; E2-only fields are dropped.
Parser: stage4/scripts/eval_stage4.py parse() (main thread). Fields: model, MCP servers / plugins / skills from init,
turns, input tokens (input + cache read + cache creation), output tokens, cost, wall, subtype, fired (any skillfetch
call), first search turn, loaded ids (load_skills results; resolve_and_load content headers), check pass and failed items, harness failure, E2 user-state
check. usage: extract_s10.py <tag> [<tag> ...]"""
import json
import re
import sys
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
E2E = S11.parent
PRIV = E2E / "stage11-private"
sys.path.insert(0, str(S11 / "scripts"))
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from eval_stage4 import SF, json_payload, parse  # noqa: E402

tags = set(sys.argv[1:])
from run_s11 import load_tasks  # noqa: E402

tasks = load_tasks()
rows = []
for f in sorted((PRIV / "runs").glob("*/*.jsonl")):
    m_path = Path(str(f)[:-6] + ".meta.json")
    if not m_path.exists():
        continue
    m = json.loads(m_path.read_text())
    if m["tag"] not in tags:
        continue
    meta, init, result, calls, results, _ = parse(f)
    sf = [c for c in calls if c["name"].startswith(SF)]
    loaded = []
    for c in sf:
        if c["name"] == SF + "load_skills":
            p = json_payload(results.get(c["id"], "")) or {}
            loaded += [s["id"] for s in p.get("skills", []) if isinstance(s, dict) and "id" in s]
        elif c["name"] == SF + "resolve_and_load":  # R1s: no skills list; loaded = section headers "## n. title (id)"
            p = json_payload(results.get(c["id"], "")) or {}  # among the ids the call asked for
            asked = set(c["input"].get("auto_ids") or []) | set(c["input"].get("pinned_ids") or [])
            heads = re.findall(r"^## \d+\. .*\(([^()\s]+)\)$", p.get("content") or "", re.M)
            loaded += [i for i in heads if i in asked]
    first_search = next((c["turn"] for c in sf if c["name"] == SF + "search_skills"), None)
    u = result.get("usage") or {}
    rows.append({"task": m["task"], "bundle": m["bundle"], "env": m["env"], "cond": m["cond"], "tag": m["tag"],
                 "model": init.get("model"), "mcp_servers": [s.get("name") for s in init.get("mcp_servers", [])],
                 "plugins": [p.get("name") for p in init.get("plugins", [])] if isinstance(init.get("plugins"), list) else init.get("plugins"),
                 "skills_available": init.get("skills"), "subtype": result.get("subtype"), "turns": result.get("num_turns"),
                 "input_tokens": sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                 "output_tokens": u.get("output_tokens"), "cost_usd": result.get("total_cost_usd"), "wall_s": m["wall_s"], "prep_s": m["prep_s"],
                 "fired": bool(sf), "first_search_turn": first_search, "sf_calls": [c["name"].removeprefix(SF) for c in sf],
                 "loaded": list(dict.fromkeys(loaded)), "check_pass": m["check"].get("pass"),
                 "check_failed": [i["name"] for i in m["check"].get("items", []) if i.get("pass") is False],
                 "diff_added": m["diff"]["added"], "diff_deleted": m["diff"]["deleted"], "harness_fail": m.get("harness_fail"),
                 "timed_out": m.get("timed_out"), "no_result": m.get("no_result"), "check_undecidable": m["check"].get("undecidable") or [],
                 "graft_removed": [g["path"] for g in m.get("graft_removed", [])], "index_ok_after": m.get("index_ok_after"),
                 "leftover_procs": len(m.get("leftover_procs") or [])})
out = PRIV / f"sessions-{'-'.join(sorted(tags))}.jsonl"
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(len(rows), "rows ->", out.name)
