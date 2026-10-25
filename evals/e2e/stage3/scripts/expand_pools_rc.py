#!/usr/bin/env python3
"""Pool check for the router candidates (same as step 3-0): add each candidate's top-10 on the 380 tasks
(followup/rc-rankings.json, runs R-a|380, R-b|380, R-c|380) to the oracle v2 pool, grade only candidates without a
grade with the unchanged 2b prompt (gen/sys-grade.txt), one call per task. oracle.jsonl (v2) stays frozen; the merged
labels go to followup/oracle-v3.jsonl, counts to followup/pool-expansion-rc.json."""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

FU = S3 / "followup"
RUNS = ["R-a|380", "R-b|380", "R-c|380"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
v2 = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
rk = json.loads((FU / "rc-rankings.json").read_text())
new = {}
for tid, o in v2.items():
    have = {x["skill"] for x in o["pool"]}
    add = {}
    for m in RUNS:
        for sid in rk[m][tid][:10]:
            if sid not in have:
                add.setdefault(sid, []).append(m.split("|")[0])
    if add:
        order = list(add)
        random.Random(f"expand-rc-{tid}").shuffle(order)
        new[tid] = {"order": order, "sources": add}
jobs = [(f"grade-rc-{tid}", S3 / "gen" / "sys-grade.txt",
         f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(n['order'])})\n" + "\n".join(card(s) for s in n["order"])) for tid, n in new.items()]
res = run_all(jobs, workers=8)
graded, problems = {}, []
for (tid, n), r in zip(new.items(), res):
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(n["order"]))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(n["order"]):
        problems.append((tid, len(set(n["order"]) - set(g))))
    graded[tid] = g
rows, stats, by = [], Counter(), {m.split("|")[0]: Counter() for m in RUNS}
for tid, o in v2.items():
    o = dict(o, pool=list(o["pool"]))
    for sid in new.get(tid, {}).get("order", []):
        if sid in graded[tid]:
            x = {"skill": sid, "sources": new[tid]["sources"][sid], **graded[tid][sid], "added_in": "rc"}
            o["pool"].append(x)
            stats["added"] += 1
            stats[f"grade{x['grade']}"] += 1
            for m in x["sources"]:
                by[m]["added"] += 1
                by[m]["relevant"] += x["grade"] >= 2
    rel = sorted((x for x in o["pool"] if x["grade"] >= 2), key=lambda x: -x["grade"])
    o["relevant"] = [x["skill"] for x in rel]
    o["relevant_grades"] = {x["skill"]: x["grade"] for x in rel}
    o["relevant_process"] = [x["skill"] for x in rel if x["process"]]
    o["relevant_2a"] = [x["skill"] for x in rel if "2a" in x["sources"]]
    o["relevant_v2"] = v2[tid]["relevant"]
    rows.append(o)
(FU / "oracle-v3.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summary = {"tasks_with_new_candidates": len(new), "calls": len(jobs), "added": stats["added"],
           "grade_dist_added": {g: stats[f"grade{g}"] for g in range(4)}, "added_relevant": stats["grade2"] + stats["grade3"],
           "relevant_v2": sum(len(r["relevant_v2"]) for r in rows), "relevant_v3": sum(len(r["relevant"]) for r in rows),
           "by_candidate": {m: dict(c) for m, c in by.items()}, "grading_problems": problems,
           "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2)}
(FU / "pool-expansion-rc.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
