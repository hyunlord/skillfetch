#!/usr/bin/env python3
"""§5: (task, skill) in staging R-c top-50 or S-b' staging picks with no grade in v5-ss-b-s9 -> blind grading, same
format as v5-ss-b (title = name, summary = 220-char description, 2b prompt, one isolated call per task, seed
s9-grade-<task>, labels m01...). Without --run: count and cost estimate only. Refuses when the estimate is over $10
unless --approved (the user approved it after the estimate was reported).
usage: s9_grade.py <staging_dir> <staging_results.json> <staging_select.jsonl> [--run] [--approved]"""
import json
import random
import re
import sys
from pathlib import Path

from s9_common import OUT, RUN, E2E, S9, by_id, records, tasks

sys.path.insert(0, str(E2E / "stage6" / "scripts"))
RATE = 29.37 / 25020  # v5-ss-b expansion, measured
stg = records(sys.argv[1])
res = json.loads(Path(sys.argv[2]).read_text())
sel = {r["id"]: r["skills"] for r in map(json.loads, Path(sys.argv[3]).open())} if Path(sys.argv[3]).exists() else {}
orc = by_id(OUT / "oracle-v5-ss-b-s9.jsonl")
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
new = {}
for t in tasks:
    have = {x["skill"] for x in orc[t]["pool"]}
    c = sorted(({x["id"] for x in res[t].get("results", [])[:50]} | set(sel.get(t, []))) - have)
    if c:
        new[t] = c
n = sum(len(v) for v in new.values())
est = round(n * RATE, 2)
print(json.dumps({"tasks": len(new), "candidates": n, "estimate_usd": est}))
if "--run" not in sys.argv:
    sys.exit(0)
if est > 10 and "--approved" not in sys.argv:
    sys.exit(f"estimate ${est} > $10: report to the user first (DESIGN §5)")
from batch import parse_json_last, run_all  # noqa: E402

labels, jobs = {}, []
for t, c in new.items():
    random.Random(f"s9-grade-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {stg[k]['name']}\n  summary: {desc220(stg[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s9{RUN}-grade-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
out = run_all(jobs, workers=8)
graded, problems = {}, []
for (t, lab), r in zip(labels.items(), out):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(lab):
        problems.append({"task": t, "missing": len(set(lab) - set(g))})
    graded[t] = [{"skill": lab[l], "label": l, **v, "sources": ["s9-grade"], "ss_ids": []} for l, v in g.items()]
rows = [{**o, "pool": o["pool"] + graded.get(t, []), "relevant": [x["skill"] for x in o["pool"] + graded.get(t, []) if x["grade"] >= 2]} for t, o in orc.items()]
(OUT / "oracle-v5-ss-b-s9g.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows))
(OUT / "grade-labels-s9.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0))
summ = {"graded": sum(len(v) for v in graded.values()), "grade_ge2": sum(x["grade"] >= 2 for v in graded.values() for x in v),
        "problems": problems, "cost_usd": round(sum(r.get("cost_usd") or 0 for r in out), 2)}
(OUT / "grade-s9-summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ))
