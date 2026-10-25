#!/usr/bin/env python3
"""7a-pool step 4: gpt-direction-40.jsonl vs the Opus direction relabel (oracle-v5-direction.jsonl rows graded_in
7a-relabel), same 1,611 rows of blind-direction-40.jsonl. Exact, within 1, grade kappa, relevant (>=2) kappa, process kappa.
If relevant kappa < 0.6: oracle-v5-direction-b-inter.jsonl = v5-direction-b where the 40 pair tasks keep a skill as
relevant only if both Opus and GPT grade it >= 2 (rows GPT did not grade, i.e. the 7a-pool additions, count as not
confirmed). Writes gpt-kappa.json."""
import json
from collections import Counter
from pathlib import Path

S7 = Path(__file__).resolve().parents[1]


def kappa(x, y):
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in set(x) | set(y))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


blind = [json.loads(l) for l in (S7 / "blind-direction-40.jsonl").open()]
gpt = {(r["task_id"], r["candidate_id"]): r for r in map(json.loads, (S7 / "gpt-direction-40.jsonl").open())}
opus = {}
for l in (S7 / "oracle-v5-direction.jsonl").open():
    o = json.loads(l)
    for x in o["pool"]:
        if x.get("graded_in") == "7a-relabel":
            opus[(o["id"], x["skill"])] = x
pairs, missing = [], []
for r in blind:
    k = (r["task_id"], r["candidate_id"])
    if k not in gpt or k not in opus:
        missing.append(k)
        continue
    pairs.append((opus[k]["grade"], int(gpt[k]["grade"]), opus[k]["process"], bool(gpt[k]["process"])))
og, gg = [p[0] for p in pairs], [p[1] for p in pairs]
res = {"rows": len(blind), "compared": len(pairs), "missing": len(missing),
       "exact": round(sum(a == b for a, b in zip(og, gg)) / len(pairs), 3), "within_1": round(sum(abs(a - b) <= 1 for a, b in zip(og, gg)) / len(pairs), 3),
       "grade_kappa": kappa(og, gg), "relevant_kappa": kappa([g >= 2 for g in og], [g >= 2 for g in gg]),
       "process_kappa": kappa([p[2] for p in pairs], [p[3] for p in pairs]),
       "relevant_counts": {"opus": sum(g >= 2 for g in og), "gpt": sum(g >= 2 for g in gg), "both": sum(a >= 2 and b >= 2 for a, b in zip(og, gg))},
       "confusion_opus_to_gpt": {f"{a}->{b}": c for (a, b), c in sorted(Counter(zip(og, gg)).items())}}
if res["relevant_kappa"] < 0.6:
    rows = []
    for l in (S7 / "oracle-v5-direction-b.jsonl").open():
        o = json.loads(l)
        if any(k[0] == o["id"] for k in opus):
            pool = [{**x, "grade_opus": x["grade"], "grade": (x["grade"] if (o["id"], x["skill"]) in gpt and int(gpt[(o["id"], x["skill"])]["grade"]) >= 2 and x["grade"] >= 2 else min(x["grade"], 1))}
                    for x in o["pool"]]
            o = {**o, "pool": pool, "relevant": [x["skill"] for x in pool if x["grade"] >= 2]}
        rows.append(o)
    (S7 / "oracle-v5-direction-b-inter.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in rows))
    res["intersection_oracle"] = "oracle-v5-direction-b-inter.jsonl"
(S7 / "gpt-kappa.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
