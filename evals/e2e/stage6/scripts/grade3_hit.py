#!/usr/bin/env python3
"""6b-A1: hit with relevance = grade 3 only (oracle v4), S-0 vs S-b (first generation); and for the tasks S-0 hit and
S-b missed (grade >= 2 basis, the 28 of report-6a), the best grade S-0 picked there and the task's top relevant grade.
Writes grade3-hit.json."""
import json
from collections import Counter
from pathlib import Path

S6 = Path(__file__).resolve().parents[1]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()}
O = {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4.jsonl").open()}
S = {c: {json.loads(l)["id"]: set(json.loads(l)["skills"]) for l in (S6 / f"select-{c}.jsonl").open()} for c in ("S-0", "S-b")}
g = {t: {x["skill"]: x["grade"] for x in O[t]["pool"]} for t in O}
out = {}
for lab, thr in (("grade>=2", 2), ("grade==3", 3)):
    cov = [t for t in O if not tasks[t]["expect_none"] and any(v >= thr for v in g[t].values())]
    out[lab] = {"tasks": len(cov)}
    for c in S:
        out[lab][c] = round(sum(any(g[t].get(s, 0) >= thr for s in S[c][t]) for t in cov) / len(cov), 3)
    out[lab]["S-0_hit_S-b_miss"] = sum(any(g[t].get(s, 0) >= thr for s in S["S-0"][t]) and not any(g[t].get(s, 0) >= thr for s in S["S-b"][t]) for t in cov)
    out[lab]["S-b_hit_S-0_miss"] = sum(any(g[t].get(s, 0) >= thr for s in S["S-b"][t]) and not any(g[t].get(s, 0) >= thr for s in S["S-0"][t]) for t in cov)
cov2 = [t for t in O if not tasks[t]["expect_none"] and O[t]["relevant"]]
miss = [t for t in cov2 if S["S-0"][t] & set(O[t]["relevant"]) and not S["S-b"][t] & set(O[t]["relevant"])]
out["missed_28"] = {"n": len(miss),
                    "best_grade_S-0_picked": dict(Counter(max(g[t].get(s, 0) for s in S["S-0"][t]) for t in miss)),
                    "task_top_relevant_grade": dict(Counter(max(O[t]["relevant_grades"].values()) for t in miss)),
                    "S-b_picked_none": sum(not S["S-b"][t] for t in miss)}
(S6 / "grade3-hit.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
