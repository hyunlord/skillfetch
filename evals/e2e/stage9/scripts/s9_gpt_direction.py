#!/usr/bin/env python3
"""Direction of GPT vs Opus disagreement on blind-run-b-60 rows, new records vs existing: mean (GPT - Opus), Opus-relevant
rows GPT demoted below 2, Opus-irrelevant rows GPT promoted to >= 2, by source; row-bootstrap 95% CI (2,000) for
new - existing on the mean difference and on the demotion rate. Writes gpt-run-b-60-direction.json."""
import json
import random
import statistics as st

from s9_common import S9, by_id

key = json.loads((S9 / "blind-run-b-60-key.json").read_text())
gpt = {(r["task_id"], r["candidate_id"]): int(r["grade"]) for r in map(json.loads, (S9 / "gpt-run-b-60.jsonl").open())}
rows = [{"src": v["source"], "kind": "new" if v["source"] == "new" else "old", "o": v["opus_grade"], "g": gpt[(t, c)]} for t, vv in key.items() for c, v in vv.items()]


def d(rs):
    rel = [r for r in rs if r["o"] >= 2]
    irr = [r for r in rs if r["o"] < 2]
    return {"n": len(rs), "mean_opus": round(st.mean(r["o"] for r in rs), 3), "mean_gpt": round(st.mean(r["g"] for r in rs), 3),
            "mean_gpt_minus_opus": round(st.mean(r["g"] - r["o"] for r in rs), 3),
            "gpt_lower": sum(r["g"] < r["o"] for r in rs), "gpt_higher": sum(r["g"] > r["o"] for r in rs),
            "opus_relevant": len(rel), "demoted_below_2": sum(r["g"] < 2 for r in rel),
            "demotion_rate": round(sum(r["g"] < 2 for r in rel) / len(rel), 3) if rel else None,
            "opus_irrelevant": len(irr), "promoted_to_ge2": sum(r["g"] >= 2 for r in irr),
            "promotion_rate": round(sum(r["g"] >= 2 for r in irr) / len(irr), 3) if irr else None,
            "opus_3_rows": sum(r["o"] == 3 for r in rs), "opus_3_gpt_lower": sum(r["o"] == 3 and r["g"] < 3 for r in rs)}


out = {k: d([r for r in rows if r["kind"] == k]) for k in ("new", "old")}
out["by_source"] = {s: d([r for r in rows if r["src"] == s]) for s in ("new", "old_staging_top10", "old_baseline_top10")}
new, old = [r for r in rows if r["kind"] == "new"], [r for r in rows if r["kind"] == "old"]
rng = random.Random("s9b-gpt-dir")
md, dr = [], []
for _ in range(2000):
    a, b = [rng.choice(new) for _ in new], [rng.choice(old) for _ in old]
    md.append(st.mean(r["g"] - r["o"] for r in a) - st.mean(r["g"] - r["o"] for r in b))
    ra, rb = [r for r in a if r["o"] >= 2], [r for r in b if r["o"] >= 2]
    if ra and rb:
        dr.append(sum(r["g"] < 2 for r in ra) / len(ra) - sum(r["g"] < 2 for r in rb) / len(rb))
md.sort()
dr.sort()
out["new_minus_old"] = {"mean_gpt_minus_opus": round(out["new"]["mean_gpt_minus_opus"] - out["old"]["mean_gpt_minus_opus"], 3),
                        "ci95": [round(md[49], 3), round(md[1949], 3)],
                        "demotion_rate": round(out["new"]["demotion_rate"] - out["old"]["demotion_rate"], 3),
                        "demotion_ci95": [round(dr[int(0.025 * len(dr))], 3), round(dr[int(0.975 * len(dr)) - 1], 3)]}
(S9 / "gpt-run-b-60-direction.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
