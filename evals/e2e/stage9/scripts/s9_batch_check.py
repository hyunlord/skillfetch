#!/usr/bin/env python3
"""§12-1 batch-effect check: 60 tasks x (5 new-record rows graded in §5 + 5 baseline-index rows graded in v5-ss /
v5-ss-b), mixed in one list per task, regraded with the unchanged 2b prompt and the same card. Reports agreement with
the original grades by kind (and baseline rows by original batch). Without --run: estimate only.
Cost model from two measured runs: per call $0.0110 + per candidate $0.00100 (v5-ss-b expansion 380 calls x 66,
run-b §5 380 calls x 28)."""
import json
import random
import re
import statistics as st
import sys

from s9_common import BASE_INDEX, E2E, S9, by_id, records, tasks

sys.path.insert(0, str(E2E / "stage6" / "scripts"))
OUT = S9 / "batch-check"
OUT.mkdir(exist_ok=True)
base = records(BASE_INDEX)
stg = records(sys.argv[1])
so = by_id(S9 / "run-b" / "oracle-v5-ss-b-s9g.jsonl")
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
rows_new, rows_old = {}, {}
for t, o in so.items():
    for x in o["pool"]:
        k = x["skill"]
        if "s9-grade" in x.get("sources", []) and k in stg and k not in base:
            rows_new.setdefault(t, []).append({**x, "kind": "new", "batch": "s9"})
        elif k in base and "migrated_from" not in x and "merged_from" not in x and "s9-grade" not in x.get("sources", []):
            rows_old.setdefault(t, []).append({**x, "kind": "old", "batch": "v5ss-b-exp" if "s8b-expand" in x.get("sources", []) else "v5ss"})
elig = sorted(t for t in tasks if len(rows_new.get(t, [])) >= 5 and len(rows_old.get(t, [])) >= 5)
rng = random.Random("s9b-batch")
pick_t = sorted(rng.sample(elig, 60))
sample = {}
for t in pick_t:
    r = rng.sample(sorted(rows_new[t], key=lambda x: x["skill"]), 5) + rng.sample(sorted(rows_old[t], key=lambda x: x["skill"]), 5)
    random.Random(f"s9b-batch-{t}").shuffle(r)
    sample[t] = r
est = round(60 * 0.0110 + 600 * 0.00100, 2)
print(json.dumps({"eligible_tasks": len(elig), "tasks": 60, "rows": 600, "estimate_usd": est}))
if "--run" not in sys.argv:
    sys.exit(0)
if est > 10:
    sys.exit("estimate > $10: report first")
from batch import parse_json_last, run_all  # noqa: E402

rec = lambda k: stg[k] if k in stg else base[k]  # noqa: E731
jobs, labels = [], {}
for t, r in sample.items():
    lab = {f"b{i + 1:02d}": x for i, x in enumerate(r)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {rec(x['skill'])['name']}\n  summary: {desc220(rec(x['skill']).get('description'))}" for l, x in lab.items())
    jobs.append((f"s9b-batch-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
res = run_all(jobs, workers=8)
rows, problems = [], []
for (t, lab), r in zip(labels.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = int(x["grade"])
    if set(g) != set(lab):
        problems.append(t)
    rows += [{"task": t, "skill": x["skill"], "kind": x["kind"], "batch": x["batch"], "orig": x["grade"], "regrade": g[l]} for l, x in lab.items() if l in g]


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


def stats(rs):
    o, n = [r["orig"] for r in rs], [r["regrade"] for r in rs]
    return {"n": len(rs), "exact": round(sum(a == b for a, b in zip(o, n)) / len(rs), 3), "within1": round(sum(abs(a - b) <= 1 for a, b in zip(o, n)) / len(rs), 3),
            "relevance_kappa": kappa([a >= 2 for a in o], [b >= 2 for b in n]), "orig_ge2": sum(a >= 2 for a in o), "regrade_ge2": sum(b >= 2 for b in n),
            "mean_orig": round(st.mean(o), 3), "mean_regrade": round(st.mean(n), 3), "mean_diff": round(st.mean(b - a for a, b in zip(o, n)), 3),
            "orig_dist": {g: o.count(g) for g in range(4)}, "regrade_dist": {g: n.count(g) for g in range(4)}}


new = [r for r in rows if r["kind"] == "new"]
old = [r for r in rows if r["kind"] == "old"]
boot = random.Random("s9b-boot")
diffs = []
for _ in range(2000):
    a = [boot.choice(new) for _ in new]
    b = [boot.choice(old) for _ in old]
    diffs.append(st.mean(x["regrade"] - x["orig"] for x in a) - st.mean(x["regrade"] - x["orig"] for x in b))
diffs.sort()
out = {"rows": len(rows), "problems": problems, "cost_usd": round(sum(x.get("cost_usd") or 0 for x in res), 2),
       "new": stats(new), "old": stats(old),
       "old_by_batch": {b: stats([r for r in old if r["batch"] == b]) for b in sorted({r["batch"] for r in old})},
       "mean_diff_new_minus_old": round(st.mean(r["regrade"] - r["orig"] for r in new) - st.mean(r["regrade"] - r["orig"] for r in old), 3),
       "bootstrap95_new_minus_old": [round(diffs[49], 3), round(diffs[1949], 3)]}
(OUT / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
(OUT / "summary.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
