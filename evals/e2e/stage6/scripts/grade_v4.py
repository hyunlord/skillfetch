#!/usr/bin/env python3
"""Pool check for the selections: skills picked by any candidate (select-S-*.jsonl) that are not in the task's oracle v3
pool (stage3/followup/oracle-v3.jsonl) are graded with the unchanged 2b prompt (gen/sys-grade.txt = stage3), one call per
task. Writes oracle-v4.jsonl (v3 + new grades, relevant sets recomputed) and pool-v4.json."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S6, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

CANDS = ["S-0", "S-a", "S-b", "S-c"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()}
v3 = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "followup" / "oracle-v3.jsonl").open()}
sel = {c: {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f"select-{c}.jsonl").open()} for c in CANDS}
new = {}
for tid, o in v3.items():
    have = {x["skill"] for x in o["pool"]}
    add = {}
    for c in CANDS:
        for s in sel[c][tid]:
            if s not in have:
                add.setdefault(s, []).append(c)
    if add:
        order = sorted(add)
        random.Random(f"v4-{tid}").shuffle(order)
        new[tid] = {"order": order, "sources": add}
res = run_all([(f"grade-v4-{tid}", S6 / "gen" / "sys-grade.txt",
                f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(n['order'])})\n" + "\n".join(card(s) for s in n["order"])) for tid, n in new.items()], workers=8)
graded, problems = {}, []
for (tid, n), r in zip(new.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(n["order"]))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(n["order"]):
        problems.append((tid, len(set(n["order"]) - set(g))))
    graded[tid] = g
rows, added, rel_added = [], 0, 0
for tid, o in v3.items():
    o = dict(o, pool=list(o["pool"]))
    for s in new.get(tid, {}).get("order", []):
        if s in graded[tid]:
            o["pool"].append({"skill": s, "sources": ["sel:" + c for c in new[tid]["sources"][s]], **graded[tid][s], "added_in": "6a"})
            added += 1
            rel_added += graded[tid][s]["grade"] >= 2
    rel = sorted((x for x in o["pool"] if x["grade"] >= 2), key=lambda x: -x["grade"])
    o["relevant_v3"] = v3[tid]["relevant"]
    o["relevant"] = [x["skill"] for x in rel]
    o["relevant_grades"] = {x["skill"]: x["grade"] for x in rel}
    o["relevant_process"] = [x["skill"] for x in rel if x["process"]]
    o["relevant_2a"] = [x["skill"] for x in rel if "2a" in x["sources"]]
    rows.append(o)
(S6 / "oracle-v4.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
out = {"tasks_graded": len(new), "added": added, "added_relevant": rel_added, "problems": problems,
       "relevant_v3": sum(len(v3[t]["relevant"]) for t in v3), "relevant_v4": sum(len(r["relevant"]) for r in rows),
       "no_relevant_v3": sum(not v3[t]["relevant"] for t in v3), "no_relevant_v4": sum(not r["relevant"] for r in rows),
       "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2)}
(S6 / "pool-v4.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out))
