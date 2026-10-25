#!/usr/bin/env python3
"""GPT cross-label agreement: gpt-grades-120.jsonl ({task_id, candidate_id, grade, process}) vs the Opus 2b/3-0 labels in
oracle.jsonl for the same rows of blind-pool-120.jsonl. Exact, within ±1, relevant (grade >= 2) kappa, process kappa,
coverage of the returned rows; the 10 tasks with the largest disagreement (sum of |grade diff|, then relevant-set
mismatch). Writes cross-label.json."""
import json
from collections import Counter
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in set(x) | set(y))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


blind = [json.loads(l) for l in (S3 / "blind-pool-120.jsonl").open()]
gpt = {(r["task_id"], r["candidate_id"]): r for r in map(json.loads, (S3 / "gpt-grades-120.jsonl").open())}
orc = {json.loads(l)["id"]: {x["skill"]: x for x in json.loads(l)["pool"]} for l in (S3 / "oracle.jsonl").open()}
pairs, missing = [], []
for r in blind:
    k = (r["task_id"], r["candidate_id"])
    if k not in gpt:
        missing.append(k)
        continue
    o = orc[r["task_id"]][r["candidate_id"]]
    pairs.append((r["task_id"], r["candidate_id"], o["grade"], int(gpt[k]["grade"]), o["process"], bool(gpt[k]["process"])))
og, gg = [p[2] for p in pairs], [p[3] for p in pairs]
res = {"rows": len(blind), "returned": len(pairs), "missing": len(missing),
       "exact": round(sum(a == b for a, b in zip(og, gg)) / len(pairs), 3),
       "within_1": round(sum(abs(a - b) <= 1 for a, b in zip(og, gg)) / len(pairs), 3),
       "grade_kappa": kappa(og, gg), "relevant_kappa": kappa([g >= 2 for g in og], [g >= 2 for g in gg]),
       "relevant_agree": round(sum((a >= 2) == (b >= 2) for a, b in zip(og, gg)) / len(pairs), 3),
       "process_kappa": kappa([p[4] for p in pairs], [p[5] for p in pairs]),
       "process_agree": round(sum(p[4] == p[5] for p in pairs) / len(pairs), 3),
       "confusion_opus_to_gpt": {f"{a}->{b}": c for (a, b), c in sorted(Counter(zip(og, gg)).items())},
       "relevant_counts": {"opus": sum(g >= 2 for g in og), "gpt": sum(g >= 2 for g in gg)}}
per = {}
for t, c, a, b, *_ in pairs:
    d = per.setdefault(t, {"absdiff": 0, "opus_rel": set(), "gpt_rel": set()})
    d["absdiff"] += abs(a - b)
    if a >= 2:
        d["opus_rel"].add(c)
    if b >= 2:
        d["gpt_rel"].add(c)
worst = sorted(per.items(), key=lambda kv: (-kv[1]["absdiff"], -len(kv[1]["opus_rel"] ^ kv[1]["gpt_rel"])))[:10]
text = {r["task_id"]: r["task_text"] for r in blind}
res["worst_10"] = [{"task_id": t, "task_text": text[t][:300], "sum_abs_diff": d["absdiff"], "opus_relevant": sorted(d["opus_rel"]),
                    "gpt_relevant": sorted(d["gpt_rel"])} for t, d in worst]
(S3 / "cross-label.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
print(json.dumps({k: v for k, v in res.items() if k != "worst_10"}, indent=1))
