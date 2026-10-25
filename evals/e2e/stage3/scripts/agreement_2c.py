#!/usr/bin/env python3
"""Step 2c: agreement between the 2b grades and the 2c re-grades (different prompt wording) on the same 40 pools.
Writes label-agreement.json."""
import json
from collections import Counter
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
a = json.loads((S3 / "gen" / "grades-2b.json").read_text())
b = json.loads((S3 / "gen" / "grades-2c.json").read_text())
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
pairs = [(a[t][s]["grade"], b[t][s]["grade"], a[t][s]["process"], b[t][s]["process"], t, s) for t in b for s in b[t] if s in a[t]]
n = len(pairs)


def kappa(x, y):
    cats = sorted(set(x) | set(y))
    po = sum(i == j for i, j in zip(x, y)) / len(x)
    pe = sum((x.count(c) / len(x)) * (y.count(c) / len(y)) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


ga, gb = [p[0] for p in pairs], [p[1] for p in pairs]
rel_a, rel_b = [g >= 2 for g in ga], [g >= 2 for g in gb]
set_same = sum(1 for t in b if {s for s in b[t] if a[t][s]["grade"] >= 2} == {s for s in b[t] if b[t][s]["grade"] >= 2})
res = {"tasks": len(b), "pairs": n, "exact": round(sum(x == y for x, y in zip(ga, gb)) / n, 3),
       "within_1": round(sum(abs(x - y) <= 1 for x, y in zip(ga, gb)) / n, 3),
       "relevant_agree": round(sum(x == y for x, y in zip(rel_a, rel_b)) / n, 3), "relevant_kappa": kappa(rel_a, rel_b),
       "grade_kappa": kappa(ga, gb), "process_agree": round(sum(p[2] == p[3] for p in pairs) / n, 3),
       "relevant_set_identical_tasks": set_same,
       "confusion": {f"{x}->{y}": c for (x, y), c in sorted(Counter(zip(ga, gb)).items())},
       "grade_dist_2b": dict(sorted(Counter(ga).items())), "grade_dist_2c": dict(sorted(Counter(gb).items())),
       "biggest_disagreements": [{"task": p[4], "skill": p[5], "2b": p[0], "2c": p[1]} for p in pairs if abs(p[0] - p[1]) >= 2]}
(S3 / "label-agreement.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "biggest_disagreements"}, indent=1))
print("|diff|>=2:", len(res["biggest_disagreements"]))
