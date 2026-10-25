#!/usr/bin/env python3
"""Post-run pool check (stage 4 step 4-0): skills that a stage-5 session loaded, or that were in a session's first
search top-10, and are not in the task's oracle pool, graded with the unchanged 2b prompt (stage4/gen/sys-grade.txt),
one isolated call per task. Writes oracle-4-0.jsonl (stage5/oracle.jsonl + the new grades, relevant sets recomputed)
and grade-4-0.json (counts)."""
import json
import random
import sys
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S5.parent / "stage4" / "scripts"))
from batch import S4, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

jl = lambda p: [json.loads(l) for l in p.open() if l.strip()]  # noqa: E731
tasks = {t["id"]: t for t in jl(S5 / "tasks.jsonl")}
orc = {o["id"]: o for o in jl(S5 / "oracle.jsonl")}
sess = jl(S5 / "sessions.jsonl")
new = {}
for r in sess:
    have = {x["skill"] for x in orc[r["task"]]["pool"]}
    for sid in [s for s in r["loaded"] if not s.startswith("path:")] + r["top50"][:10]:
        if sid not in have:
            new.setdefault(r["task"], {}).setdefault(sid, set()).add("loaded" if sid in r["loaded"] else "top10")
jobs, orders = [], {}
for tid, d in new.items():
    order = sorted(d)
    random.Random(f"s5-40-{tid}").shuffle(order)
    orders[tid] = order
    jobs.append((f"s5-grade40-{tid}", S4 / "gen" / "sys-grade.txt",
                 f"TASK\n{tasks[tid]['prompt']}\n\nCANDIDATES ({len(order)})\n" + "\n".join(card(s) for s in order)))
res = run_all(jobs, workers=8)
graded, problems = {}, []
for (tid, order), r in zip(orders.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(order))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(order):
        problems.append((tid, len(set(order) - set(g))))
    graded[tid] = g
rows, added, added_rel = [], 0, 0
for tid, o in orc.items():
    o = dict(o, pool=list(o["pool"]))
    for sid in orders.get(tid, []):
        if sid in graded[tid]:
            o["pool"].append({"skill": sid, "sources": sorted(new[tid][sid]), **graded[tid][sid], "added_in": "s5-4-0"})
            added += 1
            added_rel += graded[tid][sid]["grade"] >= 2
    rel = sorted((x for x in o["pool"] if x["grade"] >= 2), key=lambda x: -x["grade"])
    o["relevant_before_4_0"] = orc[tid]["relevant"]
    o["relevant"] = [x["skill"] for x in rel]
    o["relevant_grades"] = {x["skill"]: x["grade"] for x in rel}
    o["relevant_process"] = [x["skill"] for x in rel if x["process"]]
    o["relevant_2a"] = [x["skill"] for x in rel if "2a" in x["sources"]]
    rows.append(o)
(S5 / "oracle-4-0.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summary = {"tasks_graded": len(jobs), "added": added, "added_relevant": added_rel, "problems": problems,
           "relevant_before": sum(len(orc[t]["relevant"]) for t in orc), "relevant_after": sum(len(r["relevant"]) for r in rows),
           "no_relevant_after": sum(not r["relevant"] for r in rows),
           "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2)}
(S5 / "grade-4-0.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary))
