#!/usr/bin/env python3
"""Supplementary slices for report-8 (not part of the fixed §2 metrics): hit@k split by whether v5-ss has a relevant
index skill for the task (SF-reachable) or only SS-side relevant skills; per-source relevant counts; the 4 kw tasks
whose generated query was a refusal; SF top-10 vs SS top-10 grade>=2 counts. Writes metrics-8-slices.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import metrics_8 as m  # noqa: E402  (recomputes and rewrites metrics-8.json identically)

out = {}
idx_rel = [t for t in m.REL if any(not k.startswith("ss:") for k in m.R[t])]
ss_only = [t for t in m.REL if all(k.startswith("ss:") for k in m.R[t])]
for name, ts in (("index_has_relevant", idx_rel), ("ss_only_relevant", ss_only)):
    out[name] = {"n": len(ts), **{c: {f"@{k}": round(sum(bool(set(m.rank[c][t][:k]) & m.R[t]) for t in ts) / len(ts), 3)
                                       for k in (1, 5, 10)} for c in m.rank}}
    out[name]["final_load"] = {}
    for i, s in enumerate(m.sel):
        out[name]["final_load"][f"SF r{i + 1}"] = round(sum(bool(set(s.get(t, [])) & m.R[t]) for t in ts) / len(ts), 3)
    for k in ("SS-load-kw", "SS-load-full"):
        out[name]["final_load"][k] = round(sum(bool({m.loaded_key(t, k)} & m.R[t]) for t in ts) / len(ts), 3)
# relevant skills per source universe
out["relevant_pairs"] = {"index": sum(1 for t in m.tasks for k in m.R[t] if not k.startswith("ss:")),
                         "ss_only": sum(1 for t in m.tasks for k in m.R[t] if k.startswith("ss:"))}
out["top10_grade_ge2_mean_per_task"] = {c: round(sum(len(set(m.rank[c][t][:10]) & m.R[t]) for t in m.tasks) / len(m.tasks), 3) for c in m.rank}
kw = {json.loads(l)["id"]: json.loads(l) for l in (m.S8 / "kw-queries.jsonl").open()}
out["kw_refusals"] = []
for t in ("t311", "t317", "t327", "t330"):
    out["kw_refusals"].append({"task": t, "task_type": m.tasks[t]["task_type"], "expect_none": m.tasks[t]["expect_none"],
                               "query": kw[t]["query"], "SS-kw_results": len(m.rank["SS-kw"][t]),
                               "SS-load-kw": m.loaded_key(t, "SS-load-kw"), "relevant_v5ss": len(m.R[t])})
out["kw_words"] = dict(sorted(__import__("collections").Counter(x["words"] for x in kw.values()).items()))
(m.S8 / "metrics-8-slices.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
