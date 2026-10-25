#!/usr/bin/env python3
"""7a-pool step 1b: for each pair, add the top-50 of both sides' direction phrases (direction-top50.json) to both tasks'
pools; grade only candidates not already graded in oracle-v5-direction.jsonl, blind (task text + card; seeded order),
with sys-grade-direction.txt, one isolated call per task. Writes oracle-v5-direction-b.jsonl and expand-summary.json."""
import json
import random
import sys
from pathlib import Path

S7 = Path(__file__).resolve().parents[1]
S6 = S7.parent / "stage6"
sys.path.insert(0, str(S6 / "scripts"))
from batch import parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S7.parent / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S7 / "oracle-v5-direction.jsonl").open()}
top = json.loads((S7 / "direction-top50.json").read_text())
pairs = {}
for t in tasks.values():
    if t["pair_id"]:
        pairs.setdefault(t["pair_id"], {})[t["pair_side"]] = t
new = {}
for p, s in pairs.items():
    add = set(top[s["a"]["direction"]]) | set(top[s["b"]["direction"]])
    for side in ("a", "b"):
        tid = s[side]["id"]
        have = {x["skill"] for x in orc[tid]["pool"]}
        cand = sorted(add - have)
        random.Random(f"dir-pool-{tid}").shuffle(cand)
        if cand:
            new[tid] = cand
res = run_all([(f"s7-dirpool-{t}", S7 / "sys-grade-direction.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(c)})\n" + "\n".join(card(x) for x in c))
               for t, c in new.items()], workers=8)
graded, problems = {}, []
for (t, c), r in zip(new.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(c))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(c):
        problems.append((t, len(set(c) - set(g))))
    graded[t] = g
rows, added, rel_added = [], 0, 0
for t, o in orc.items():
    if t in graded:
        pool = list(o["pool"]) + [{"skill": s, **graded[t][s], "sources": ["direction-top50"], "graded_in": "7a-pool"} for s in new[t] if s in graded[t]]
        added += len(graded[t])
        rel_added += sum(v["grade"] >= 2 for v in graded[t].values())
        o = {**o, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]}
    rows.append(o)
(S7 / "oracle-v5-direction-b.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows))
summary = {"tasks_graded": len(new), "added_graded": added, "added_grade_ge2": rel_added, "problems": problems,
           "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2),
           "per_task_added": {t: len(c) for t, c in new.items()}}
(S7 / "expand-summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in ("tasks_graded", "added_graded", "added_grade_ge2", "problems", "cost_usd")}))
