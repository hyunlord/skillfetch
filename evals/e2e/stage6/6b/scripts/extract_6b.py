#!/usr/bin/env python3
"""6b per-session rows from runs/{A,C0,Cb}/<task>-r{1,2,3}.* -> sessions.jsonl (pilot p0 excluded).
Parser: stage4/scripts/eval_stage4.py parse() (main thread only). Fields: turns (result.num_turns), input tokens
(input + cache_read + cache_creation), output tokens, cost, wall, subtype, fired (any skillfetch call), searched,
loaded ids (load_skills results), number loaded, check pass + failed items."""
import json
import sys
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
E2E = S6B.parents[1]
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from eval_stage4 import SF, json_payload, parse  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6B / "tasks.jsonl").open()}
rows = []
for cond in ("A", "C0", "Cb"):
    for f in sorted((S6B / "runs" / cond).glob("*-r[123].jsonl")):
        if not Path(str(f)[:-6] + ".meta.json").exists():
            continue
        meta, init, result, calls, results, _ = parse(f)
        m = json.loads(Path(str(f)[:-6] + ".meta.json").read_text())
        sf = [c for c in calls if c["name"].startswith(SF)]
        loaded = []
        for c in sf:
            if c["name"] == SF + "load_skills":
                p = json_payload(results.get(c["id"], "")) or {}
                loaded += [s["id"] for s in p.get("skills", []) if isinstance(s, dict) and "id" in s]
        u = result.get("usage") or {}
        t = tasks[m["task"]]
        rows.append({"task": m["task"], "bundle": t["bundle"], "cond": cond, "rep": m["tag"], "relevant_found": bool(t.get("relevant_found")),
                     "subtype": result.get("subtype"), "turns": result.get("num_turns"),
                     "input_tokens": sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                     "output_tokens": u.get("output_tokens"), "cost_usd": result.get("total_cost_usd"), "wall_s": m["wall_s"],
                     "fired": bool(sf), "searched": any(c["name"] == SF + "search_skills" for c in sf),
                     "resolve_called": any(c["name"] == SF + "resolve_set" for c in sf),
                     "loaded": list(dict.fromkeys(loaded)), "n_loaded": len(set(loaded)),
                     "mcp_servers": [s.get("name") for s in init.get("mcp_servers", [])],
                     "check_pass": m["check"].get("pass"), "check_failed": [i["name"] for i in m["check"].get("items", []) if i["pass"] is False],
                     "diff_added": m["diff"]["added"], "diff_deleted": m["diff"]["deleted"]})
(S6B / "sessions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(len(rows), "sessions")
