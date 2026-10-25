#!/usr/bin/env python3
"""Stage 8 pilot: 10 tasks (seed "s8-pilot": 8 with relevant skills in oracle v5-direction, 2 expect_none), per task
SS-q1 search_skillselion(query=task text, type=skill, limit=25), SS-q3 search_skillselion(query=R-c first query, type=skill,
limit=25), SS-load load_skill(query=task text, context=task text). Writes raw/pilot.jsonl and pilot-summary.json."""
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ss_client import SS  # noqa: E402

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage7" / "oracle-v5-direction.jsonl").open()}
rc = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
rng = random.Random("s8-pilot")
rel = sorted(t for t in tasks if orc[t]["relevant"] and not tasks[t]["expect_none"])
en = sorted(t for t in tasks if tasks[t]["expect_none"])
ids = sorted(rng.sample(rel, 8) + rng.sample(en, 2))
ss = SS("pilot")
recs = []
for t in ids:
    recs.append(ss.tool(t, "SS-q1", "search_skillselion", {"query": tasks[t]["text"], "type": "skill", "limit": 25}))
    recs.append(ss.tool(t, "SS-q3", "search_skillselion", {"query": rc[t][0], "type": "skill", "limit": 25}))
    recs.append(ss.tool(t, "SS-load", "load_skill", {"query": tasks[t]["text"], "context": tasks[t]["text"]}))
ss.close()
count = lambda txt: len(re.findall(r"^### ", txt, re.M))  # noqa: E731
out = {"server_info": ss.server_info, "tasks": ids, "per_kind": {}}
for k in ("SS-q1", "SS-q3", "SS-load"):
    rs = [r for r in recs if r["kind"] == k]
    out["per_kind"][k] = {"n_results": [count(r["text"]) for r in rs], "wall_s_median": st.median(r["wall_s"] for r in rs),
                          "wall_s_max": max(r["wall_s"] for r in rs), "errors": sum(bool(r["error"] or r["is_error"]) for r in rs),
                          "empty": sum("No Skillselion result" in r["text"] for r in rs)}
(S8 / "pilot-summary.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
