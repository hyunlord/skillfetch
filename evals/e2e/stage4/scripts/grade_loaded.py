#!/usr/bin/env python3
"""Step 4-0 (after the sessions): grade the skills a session loaded or the offline selection picked that are not in
the task's oracle pool, with the unchanged 2b prompt (gen/sys-grade.txt), one call per task; frozen oracle files are
left as they are. Writes oracle-v3.jsonl (the 29 tasks, pool + added_in "4-0") and grade-4-0.json (counts, and the
offline class of each task recomputed with the v3 relevant set)."""
import glob
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S4, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S4 / "tasks.jsonl").open()}
oracle = {}
for p in (S4 / "oracle.jsonl", S4 / "oracle-r2.jsonl"):
    oracle.update({json.loads(l)["id"]: json.loads(l) for l in p.open()})
rank = {}
for p in (S4 / "rankings.json", S4 / "rankings-r2.json"):
    rank.update(json.loads(p.read_text()))
sessions = [json.loads(l) for l in (S4 / "sessions.jsonl").open()]
need = {}
for tid, t in tasks.items():
    pool = {x["skill"] for x in oracle[tid]["pool"]}
    src = {}
    for s in t["offline_skills"]:
        if s not in pool:
            src.setdefault(s, set()).add("offline")
    for r in sessions:
        if r["task"] == tid:
            for s in r["loaded"]:
                if s not in pool and not s.startswith("path:"):  # local project skills are not in the index
                    src.setdefault(s, set()).add(f"session_{r['env']}")
    if src:
        order = sorted(src)
        random.Random(f"grade40-{tid}").shuffle(order)
        need[tid] = {"order": order, "sources": {k: sorted(v) for k, v in src.items()}}
res = run_all([(f"grade40-{tid}", S4 / "gen" / "sys-grade.txt",
                f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(n['order'])})\n" + "\n".join(card(s) for s in n["order"]))
               for tid, n in need.items()], workers=8)
rows, added, added_rel, cost, changed = [], 0, 0, 0.0, {}
for tid in tasks:
    o = dict(oracle[tid], pool=list(oracle[tid]["pool"]))
    if tid in need:
        r = res[list(need).index(tid)]
        assert not r["is_error"], tid
        cost += r.get("cost_usd") or 0
        for x in parse_json_last(r["text"]):
            ids, _ = resolve_ids([x["skill"]], set(need[tid]["order"]))
            if ids:
                o["pool"].append({"skill": ids[0], "sources": need[tid]["sources"][ids[0]], "grade": int(x["grade"]),
                                  "process": bool(x.get("process")), "added_in": "4-0"})
                added += 1
                added_rel += int(x["grade"]) >= 2
    rel = sorted((x for x in o["pool"] if x["grade"] >= 2), key=lambda x: -x["grade"])
    o["relevant"] = [x["skill"] for x in rel]
    o["relevant_grades"] = {x["skill"]: x["grade"] for x in rel}
    o["relevant_process"] = [x["skill"] for x in rel if x["process"]]
    o["relevant_v2"] = oracle[tid]["relevant"]
    rows.append(o)
    R, S = set(o["relevant"]), set(tasks[tid]["offline_skills"])
    rk = rank[tid]
    if not R:
        cls = "over_load" if S else "ok"
    elif S & R:
        cls = "ok"
    elif R & set(rk["q3"][:50]):
        cls = "select_fail"
    elif R & (set(rk["q1"][:50]) | set(rk["q2"][:50])):
        cls = "restate_fail"
    else:
        cls = "search_fail"
    if cls != tasks[tid]["offline_class"]:
        changed[tid] = [tasks[tid]["offline_class"], cls]
(S4 / "oracle-v3.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
summary = {"tasks_graded": len(need), "added": added, "added_relevant": added_rel, "cost_usd": round(cost, 2),
           "offline_class_changed": changed}
(S4 / "grade-4-0.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary))
