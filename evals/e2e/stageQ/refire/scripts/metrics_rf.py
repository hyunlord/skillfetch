#!/usr/bin/env python3
"""Re-fire check numbers and verdict (stageRF/DESIGN.md §3, fixed before the run) from
stageRF-private/requests-<tags>.jsonl (stageQ/scripts/extract_q.py with SQ_PRIV=stageRF-private).
Per arm (cur, a, b) × task position 1–4: router fired (the Skill tool invoked `skillfetch-router` or any skillfetch MCP
call in that request), skillfetch calls by name, loaded skills, an earlier task's loaded skill named in this request's
reply or diff without being loaded in it, turns, API-price equivalent.
Criteria: fire rate on tasks 2 and 4 (10 requests per arm); non-fire rate on task 3 (5 requests per arm).
Winner: among a and b, the higher fire(2,4), counted only if non-fire(3) >= 4/5 and fire(2,4) > cur's; tie -> higher
non-fire(3) -> lower mean API-price equivalent per session; no qualifying arm -> no winner (no canary rerun).
usage: metrics_rf.py <requests.jsonl>   -> stageRF-private/metrics-rf.json"""
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

PRIV = Path(__file__).resolve().parents[2] / "stageRF-private"
rows = [r for r in map(json.loads, open(sys.argv[1])) if r["tag"].startswith("m") and r["job"].startswith("rf:")]


def short(i):
    return i.split("/")[-1].split("@")[0]


out = {"arms": {}}
for arm in ("cur", "a", "b"):
    by = {(r["tag"], r["k"]): r for r in rows if r["job"] == f"rf:{arm}"}
    tags = sorted({t for t, _ in by})
    pos = {}
    for k in (1, 2, 3, 4):
        rs = [by[(t, k)] for t in tags if (t, k) in by]
        mention = 0
        for t in tags:
            if (t, k) not in by:
                continue
            r = by[(t, k)]
            earlier = {short(i) for j in range(1, k) for i in by.get((t, j), {}).get("loaded", [])} - {short(i) for i in r["loaded"]}
            stem = PRIV / "runs" / f"rf-{arm}-{t}.p{k}"
            txt = (Path(str(stem) + ".reply.txt").read_text() if Path(str(stem) + ".reply.txt").exists() else "") + \
                (Path(str(stem) + ".diff").read_text(errors="replace") if Path(str(stem) + ".diff").exists() else "")
            mention += any(n in txt for n in earlier)
        pos[k] = {"n": len(rs), "fired": sum(bool(r["router_skill"] or r["fired"]) for r in rs),
                  "router_skill": sum(r["router_skill"] for r in rs), "sf_any": sum(r["fired"] for r in rs),
                  "calls": dict(Counter(c for r in rs for c in r["sf_calls"])), "loaded_any": sum(bool(r["loaded"]) for r in rs),
                  "loaded": dict(Counter(short(i) for r in rs for i in r["loaded"])), "mention_earlier_without_load": mention,
                  "turns_med": st.median(r["turns"] for r in rs) if rs else None,
                  "cost_mean": round(st.mean(r["cost_usd"] for r in rs), 3) if rs else None}
    sess_cost = [sum(by[(t, k)]["cost_usd"] for k in (1, 2, 3, 4) if (t, k) in by) for t in tags]
    out["arms"][arm] = {"sessions": len(tags), "positions": pos,
                        "fire_2_4": pos[2]["fired"] + pos[4]["fired"], "n_2_4": pos[2]["n"] + pos[4]["n"],
                        "nonfire_3": pos[3]["n"] - pos[3]["fired"], "n_3": pos[3]["n"],
                        "session_cost_mean": round(st.mean(sess_cost), 3) if sess_cost else None}
A = out["arms"]
q = [x for x in ("a", "b") if A[x]["nonfire_3"] >= 4 and A[x]["fire_2_4"] > A["cur"]["fire_2_4"]]
q.sort(key=lambda x: (-A[x]["fire_2_4"], -A[x]["nonfire_3"], A[x]["session_cost_mean"]))
out["qualifying"] = q
out["winner"] = q[0] if q else None
(PRIV / "metrics-rf.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({x: {k: A[x][k] for k in ("sessions", "fire_2_4", "n_2_4", "nonfire_3", "n_3", "session_cost_mean")} for x in A}))
print(json.dumps({"qualifying": q, "winner": out["winner"]}))
