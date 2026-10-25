#!/usr/bin/env python3
"""7a-relabel (DESIGN.md "7a-relabel"): the 40 tasks of the 20 direction pairs, pool = oracle v5 pool ∪ every pick of 6a
(S-0, S-a, S-b, S-c, S-0/S-b repeats) and 7a (S-b' x3). Blind rows (task text + candidate card: id, title, full summary,
tags; no sources, picks or earlier grades), shuffled per task with a fixed seed -> blind-direction-40.jsonl. Graded with
sys-grade-direction.txt (2b prompt + the direction paragraph), one isolated claude -p call per task (stage-6 batch helper).
Writes oracle-v5-direction.jsonl (380 tasks: the 40 regraded, the rest v5) and relabel-summary.json."""
import json
import random
import sys
from pathlib import Path

S7 = Path(__file__).resolve().parents[1]
S6 = S7.parent / "stage6"
sys.path.insert(0, str(S6 / "scripts"))
from batch import parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card, recs  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (S7.parent / "stage3" / "tasks.jsonl").open()}
v5 = {json.loads(l)["id"]: json.loads(l) for l in (S7 / "oracle-v5.jsonl").open()}
PAIR = sorted(t for t in tasks if tasks[t]["pair_id"])
assert len(PAIR) == 40
SEL = ["select-S-0.jsonl", "select-S-a.jsonl", "select-S-b.jsonl", "select-S-c.jsonl", "select-S-0-rep2.jsonl", "select-S-0-rep3.jsonl",
       "select-S-b-rep2.jsonl", "select-S-b-rep3.jsonl", "select-S-bp.jsonl", "select-S-bp-rep2.jsonl", "select-S-bp-rep3.jsonl"]
picks = {t: set() for t in PAIR}
for f in SEL:
    for l in (S6 / f).open():
        r = json.loads(l)
        if r["id"] in picks:
            picks[r["id"]] |= set(r["skills"])
pools, rows, outside = {}, [], 0
for t in PAIR:
    have = {x["skill"] for x in v5[t]["pool"]}
    outside += len(picks[t] - have)
    order = sorted(have | picks[t])
    random.Random(f"dir40-{t}").shuffle(order)
    pools[t] = order
    for s in order:
        r = recs[s]
        rows.append({"task_id": t, "task_text": tasks[t]["text"], "candidate_id": s, "title": r.get("title") or r["name"],
                     "full_summary": r.get("summary") or r.get("description", ""), "tags": r.get("tags") or {}})
(S7 / "blind-direction-40.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
res = run_all([(f"s7-dir-{t}", S7 / "sys-grade-direction.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(pools[t])})\n" + "\n".join(card(s) for s in pools[t]))
               for t in PAIR], workers=8)
new, problems = {}, []
for t, r in zip(PAIR, res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(pools[t]))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(pools[t]):
        problems.append((t, sorted(set(pools[t]) - set(g))[:5]))
    new[t] = g
out_rows = []
for t, o in v5.items():
    if t in new:
        old = {x["skill"]: x for x in o["pool"]}
        pool = [{"skill": s, **new[t][s], "sources": old.get(s, {}).get("sources", ["pick"]), "graded_in": "7a-relabel",
                 "grade_v5": old.get(s, {}).get("grade")} for s in pools[t] if s in new[t]]
        o = {"id": t, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2], "relevant_v5": o["relevant"]}
    out_rows.append(o)
(S7 / "oracle-v5-direction.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out_rows))
changed = sum(1 for t in PAIR for x in next(o for o in out_rows if o["id"] == t)["pool"] if x["grade_v5"] is not None and x["grade_v5"] != x["grade"])
summary = {"tasks": len(PAIR), "rows": len(rows), "picks_outside_v5_pool": outside, "problems": problems,
           "relevant_v5": sum(len(v5[t]["relevant"]) for t in PAIR), "relevant_new": sum(len([s for s in new[t] if new[t][s]["grade"] >= 2]) for t in PAIR),
           "grades_changed": changed, "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2)}
(S7 / "relabel-summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
