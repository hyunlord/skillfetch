#!/usr/bin/env python3
"""Stage 8 §2: oracle v5-ss. Per task, cands.json candidates shuffled with a fixed seed, given opaque labels c01..,
graded blind with the unchanged 2b prompt (stage3/gen/sys-grade.txt), one isolated `claude -p` per task. Card fields:
id (label), title (= name), summary (= 220-char description); no tags, no sources. Writes oracle-v5-ss.jsonl,
grade-labels.json (label -> key, kept apart from the blind rows), blind-ss-60.jsonl (seed s8-gpt60, stratified by task
type, then phrasing) and grade-summary.json."""
import json
import random
import sys
from pathlib import Path

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
sys.path.insert(0, str(E2E / "stage6" / "scripts"))
from batch import parse_json_last, run_all  # noqa: E402

tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
cands = json.loads((S8 / "cands.json").read_text())
labels, jobs = {}, []
for tid, c in cands.items():
    keys = sorted(c)
    random.Random(f"s8-grade-{tid}").shuffle(keys)
    lab = {f"c{i + 1:02d}": k for i, k in enumerate(keys)}
    labels[tid] = lab
    body = "\n".join(f"- id: {l}\n  title: {c[k]['title']}\n  summary: {c[k]['summary']}" for l, k in lab.items())
    jobs.append((f"s8-grade-{tid}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[tid]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
res = run_all(jobs, workers=8)
rows, problems = [], []
for (tid, lab), r in zip(labels.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    miss = sorted(set(lab) - set(g))
    if miss:
        problems.append({"task": tid, "missing": len(miss)})
    pool = [{"skill": k, "label": l, **g[l], "sources": cands[tid][k]["sources"], "ss_ids": cands[tid][k]["ss_ids"]}
            for l, k in lab.items() if l in g]
    rows.append({"id": tid, "expect_none": tasks[tid]["expect_none"], "pool": pool,
                 "relevant": [x["skill"] for x in pool if x["grade"] >= 2]})
(S8 / "oracle-v5-ss.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows))
(S8 / "grade-labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0))

# GPT-60 export: proportional per task_type (largest remainder), within a type round-robin over phrasing
rng = random.Random("s8-gpt60")
by_type = {}
for t in sorted(tasks):
    by_type.setdefault(tasks[t]["task_type"], []).append(t)
quota = {k: 60 * len(v) / len(tasks) for k, v in by_type.items()}
alloc = {k: int(q) for k, q in quota.items()}
for k in sorted(quota, key=lambda k: (-(quota[k] - alloc[k]), k))[:60 - sum(alloc.values())]:
    alloc[k] += 1
pick = []
for k, ids in sorted(by_type.items()):
    ph = {}
    for t in ids:
        ph.setdefault(tasks[t]["phrasing"], []).append(t)
    for v in ph.values():
        rng.shuffle(v)
    order = sorted(ph)
    rng.shuffle(order)
    got = []
    while len(got) < alloc[k]:
        for p in order:
            if ph[p] and len(got) < alloc[k]:
                got.append(ph[p].pop())
    pick += got
blind = []
for tid in sorted(pick):
    for l, k in labels[tid].items():
        blind.append({"task_id": tid, "task_text": tasks[tid]["text"], "candidate_id": l,
                      "title": cands[tid][k]["title"], "summary": cands[tid][k]["summary"]})
(S8 / "blind-ss-60.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in blind))
summ = {"tasks": len(rows), "graded": sum(len(o["pool"]) for o in rows),
        "grade_ge2": sum(len(o["relevant"]) for o in rows), "problems": problems,
        "cost_usd": round(sum(x.get("cost_usd") or 0 for x in res), 2),
        "gpt60_tasks": len(pick), "gpt60_rows": len(blind), "gpt60_alloc": alloc}
(S8 / "grade-summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps({k: summ[k] for k in ("tasks", "graded", "grade_ge2", "problems", "cost_usd", "gpt60_tasks", "gpt60_rows")}))
