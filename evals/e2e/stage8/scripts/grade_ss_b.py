#!/usr/bin/env python3
"""Stage 8 §4-2: oracle v5-ss-b = v5-ss + blind grades for index skills in the top-50 of SF R-c, [kw] and R-c+[kw]
(search-kw.json) that v5-ss did not grade. Same card (title = name, summary = 220-char description), unchanged 2b
prompt, one isolated call per task, seed s8b-grade-<task>, labels n01... Existing grades unchanged."""
import json
import random
import sys
from pathlib import Path

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
sys.path.insert(0, str(E2E / "stage6" / "scripts"))
sys.path.insert(0, str(S8 / "scripts"))
from batch import parse_json_last, run_all  # noqa: E402
from ss_parse import desc220, index  # noqa: E402

recs = index()[0]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S8 / "oracle-v5-ss.jsonl").open()}
sk = json.loads((S8 / "search-kw.json").read_text())
new, labels, jobs = {}, {}, []
for t in tasks:
    have = {x["skill"] for x in orc[t]["pool"]}
    c = sorted({i for cond in ("R-c", "kw", "R-c+kw") for i in sk[cond][t][:50]} - have)
    random.Random(f"s8b-grade-{t}").shuffle(c)
    if not c:
        continue
    lab = {f"n{i + 1:02d}": k for i, k in enumerate(c)}
    new[t], labels[t] = c, lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s8b-grade-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
res = run_all(jobs, workers=8)
problems, added, ge2 = [], 0, 0
graded = {}
for (t, lab), r in zip(labels.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(lab):
        problems.append({"task": t, "missing": len(set(lab) - set(g))})
    graded[t] = {lab[l]: v for l, v in g.items()}
rows = []
for t, o in orc.items():
    pool = list(o["pool"]) + [{"skill": k, "label": l, **graded[t][k], "sources": ["s8b-expand"], "ss_ids": []}
                              for l, k in labels.get(t, {}).items() if k in graded.get(t, {})]
    added += len(graded.get(t, {}))
    ge2 += sum(v["grade"] >= 2 for v in graded.get(t, {}).values())
    rows.append({**o, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]})
(S8 / "oracle-v5-ss-b.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows))
(S8 / "grade-labels-b.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0))
summ = {"tasks_graded": len(labels), "added": added, "added_grade_ge2": ge2, "problems": problems,
        "cost_usd": round(sum(x.get("cost_usd") or 0 for x in res), 2)}
(S8 / "grade-b-summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ))
