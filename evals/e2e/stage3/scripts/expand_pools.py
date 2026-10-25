#!/usr/bin/env python3
"""Step 3-0: add each new method's top-10 (bm25_q2, bm25_q3, emb_q1, emb_q2, rrf_q1, rrf_q2) to every task's pool,
grade only candidates without a grade, with the unchanged 2b prompt (gen/sys-grade.txt), one call per task that has
new candidates; merge into oracle.jsonl (v1 grades untouched; v1 kept in frozen/oracle-v1.jsonl).
Writes pool-expansion.json with the counts."""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402  (same candidate card as 2b)

METHODS = ["bm25_q2", "bm25_q3", "emb_q1", "emb_q2", "rrf_q1", "rrf_q2"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
v1 = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "frozen" / "oracle-v1.jsonl").open()}
rk = json.loads((S3 / "rankings.json").read_text())
new = {}
for tid, o in v1.items():
    have = {x["skill"] for x in o["pool"]}
    add = {}
    for m in METHODS:
        for sid in rk[tid][m][:10]:
            if sid not in have:
                add.setdefault(sid, []).append(m)
    if add:
        order = list(add)
        random.Random(f"expand-{tid}").shuffle(order)
        new[tid] = {"order": order, "sources": add}
jobs = [(f"grade3x-{tid}", S3 / "gen" / "sys-grade.txt",
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
rows, stats = [], Counter()
by_method = {m: Counter() for m in METHODS}
for tid, o in v1.items():
    o = dict(o, pool=list(o["pool"]))
    for sid in new.get(tid, {}).get("order", []):
        if sid in graded[tid]:
            x = {"skill": sid, "sources": new[tid]["sources"][sid], **graded[tid][sid], "added_in": "3-0"}
            o["pool"].append(x)
            stats["added"] += 1
            stats[f"grade{x['grade']}"] += 1
            for m in x["sources"]:
                by_method[m]["added"] += 1
                by_method[m]["relevant"] += x["grade"] >= 2
    rel = sorted((x for x in o["pool"] if x["grade"] >= 2), key=lambda x: -x["grade"])
    o["relevant"] = [x["skill"] for x in rel]
    o["relevant_grades"] = {x["skill"]: x["grade"] for x in rel}
    o["relevant_process"] = [x["skill"] for x in rel if x["process"]]
    o["relevant_2a"] = [x["skill"] for x in rel if "2a" in x["sources"]]
    o["relevant_v1"] = v1[tid]["relevant"]
    rows.append(o)
(S3 / "oracle.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summary = {"tasks_with_new_candidates": len(new), "added": stats["added"], "grade_dist_added": {g: stats[f"grade{g}"] for g in range(4)},
           "added_relevant": stats["grade2"] + stats["grade3"], "relevant_v1": sum(len(r["relevant_v1"]) for r in rows),
           "relevant_v2": sum(len(r["relevant"]) for r in rows), "by_method": {m: dict(c) for m, c in by_method.items()},
           "tasks_gaining_first_relevant": sum(1 for r in rows if r["relevant"] and not r["relevant_v1"]),
           "grading_problems": problems}
(S3 / "pool-expansion.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
