#!/usr/bin/env python3
"""§12-2: blind-run-b-60.jsonl for GPT cross-labels. 60 tasks (seed s9b-gpt60; task-type proportional, largest
remainder; phrasing round-robin within a type) among tasks whose run-b staging R-c top-10 has >= 1 new record.
Rows per task: every new-record row in the staging top-10 (n) + n existing-record rows (staging top-10 existing first,
rank order; then baseline R-c top-10, rank order). Fields: task_id, task_text, candidate_id, title, summary.
Key (source, original Opus grade) in blind-run-b-60-key.json. usage: s9_make_blind_60.py <staging_dir>"""
import json
import random
import re
import sys

from s9_common import BASE_INDEX, S9, by_id, records, tasks

base, stg = records(BASE_INDEX), records(sys.argv[1])
so = by_id(S9 / "run-b" / "oracle-v5-ss-b-s9g.jsonl")
grade = {t: {x["skill"]: x["grade"] for x in o["pool"]} for t, o in so.items()}
RS = {t: [x["id"] for x in r["results"]] for t, r in json.loads((S9 / "run-b" / "results-rc-staging-2.json").read_text()).items()}
RB = {t: [x["id"] for x in r["results"]] for t, r in json.loads((S9 / "dry" / "results-rc-baseline.json").read_text()).items()}
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
elig = [t for t in sorted(tasks) if any(k not in base for k in RS[t][:10])]
rng = random.Random("s9b-gpt60")
by_type = {}
for t in elig:
    by_type.setdefault(tasks[t]["task_type"], []).append(t)
quota = {k: 60 * len(v) / len(elig) for k, v in by_type.items()}
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
blind, key, short = [], {}, []
for t in sorted(pick):
    new = [k for k in RS[t][:10] if k not in base]
    old = [k for k in RS[t][:10] if k in base]
    old += [k for k in RB[t][:10] if k not in old]
    old = old[:len(new)]
    if len(old) < len(new):
        short.append((t, len(new), len(old)))
    rows = [(k, "new") for k in new] + [(k, "old_staging_top10" if k in RS[t][:10] else "old_baseline_top10") for k in old]
    random.Random(f"s9b-gpt60-{t}").shuffle(rows)
    key[t] = {}
    for i, (k, src) in enumerate(rows):
        r = stg[k]
        cid = f"g{i + 1:02d}"
        blind.append({"task_id": t, "task_text": tasks[t]["text"], "candidate_id": cid, "title": r["name"], "summary": desc220(r.get("description"))})
        key[t][cid] = {"skill": k, "source": src, "opus_grade": grade[t].get(k)}
(S9 / "blind-run-b-60.jsonl").write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in blind))
(S9 / "blind-run-b-60-key.json").write_text(json.dumps(key, indent=0, ensure_ascii=False))
src = [v["source"] for t in key.values() for v in t.values()]
print(json.dumps({"eligible_tasks": len(elig), "tasks": len(pick), "rows": len(blind), "new": src.count("new"),
                  "old_staging_top10": src.count("old_staging_top10"), "old_baseline_top10": src.count("old_baseline_top10"),
                  "tasks_short_of_old": short, "opus_unlabeled": sum(v["opus_grade"] is None for t in key.values() for v in t.values()),
                  "alloc": alloc}))
