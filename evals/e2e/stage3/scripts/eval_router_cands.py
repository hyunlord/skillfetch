#!/usr/bin/env python3
"""Metrics for the router candidates (followup/rc-rankings.json):
  recall@10/@50 (all relevant, 2a-sourced relevant, process relevant) on 380 tasks against oracle v2 (oracle.jsonl) and
  v3 (followup/oracle-v3.jsonl = v2 + candidates' top-10 graded), macro over tasks with a non-empty set, expect_none out;
  per-task paired comparison on all@50 (v3); on the 120 cross-label tasks, recall against the intersection labels
  (Opus and GPT both >= 2, v2 pool); 50 variance tasks x 3 generations: mean pairwise top-50 Jaccard and recall;
  R-c: how often the 4th query is the request word for word. Writes followup/router-cands.json."""
import json
import re
from itertools import combinations
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
FU = S3 / "followup"
SETS = {"all": "relevant", "2a": "relevant_2a", "process": "relevant_process"}
RUNS = ["Q3-stage3", "R-a|380", "R-b|380", "R-c|380"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
orc = {"v2": {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()},
       "v3": {json.loads(l)["id"]: json.loads(l) for l in (FU / "oracle-v3.jsonl").open()}}
rk = json.loads((FU / "rc-rankings.json").read_text())


def recall(rank, ids, o):
    out = {}
    for k, f in SETS.items():
        for cut in (10, 50):
            v = [sum(x in rank[t][:cut] for x in o[t][f]) / len(o[t][f]) for t in ids if not tasks[t]["expect_none"] and o[t][f]]
            out[f"{k}@{cut}"] = round(sum(v) / len(v), 3)
        out[f"{k}_n"] = len(v)
    return out


def per_task(rank, o, t):
    rel = o[t]["relevant"]
    return sum(x in rank[t][:50] for x in rel) / len(rel)


def jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


ids = list(tasks)
res = {"recall_380": {v: {r: recall(rk[r], ids, o) for r in RUNS} for v, o in orc.items()}}
evald = [t for t in ids if not tasks[t]["expect_none"] and orc["v3"][t]["relevant"]]
pairs = {}
for a, b in (("R-b|380", "R-a|380"), ("R-c|380", "R-b|380"), ("R-c|380", "R-a|380")):
    d = [per_task(rk[a], orc["v3"], t) - per_task(rk[b], orc["v3"], t) for t in evald]
    pairs[f"{a.split('|')[0]} vs {b.split('|')[0]}"] = {"better": sum(x > 0 for x in d), "worse": sum(x < 0 for x in d), "same": sum(x == 0 for x in d)}
res["paired_all@50_v3"] = pairs
# 120 cross-label tasks, intersection labels on the v2 pool
gpt = {}
for r in map(json.loads, (S3 / "gpt-grades-120.jsonl").open()):
    gpt.setdefault(r["task_id"], {})[r["candidate_id"]] = r
x120 = json.loads((S3 / "blind-pool-120-ids.json").read_text())
both = {}
for t in x120:
    rel = [x["skill"] for x in orc["v2"][t]["pool"] if x["grade"] >= 2 and int(gpt[t].get(x["skill"], {}).get("grade", 0)) >= 2]
    both[t] = {"relevant": rel, "relevant_2a": [s for s in rel if s in set(orc["v2"][t]["relevant_2a"])],
               "relevant_process": [x["skill"] for x in orc["v2"][t]["pool"] if x["skill"] in rel and x["process"] and gpt[t][x["skill"]]["process"]]}
res["recall_120_intersection"] = {r: recall(rk[r], x120, both) for r in RUNS}
res["recall_120_opus_v2"] = {r: recall(rk[r], x120, orc["v2"]) for r in RUNS}
# variance
vids = json.loads((FU / "variance-tasks.json").read_text())
var = {}
for cand in ("R-a", "R-b", "R-c"):
    ranks = [rk[f"{cand}|var-r{n}"] for n in (1, 2, 3)]
    pj = [sum(jac(ranks[i][t], ranks[j][t]) for i, j in combinations(range(3), 2)) / 3 for t in vids]
    gens = [{json.loads(l)["id"]: json.loads(l)["queries"] for l in (FU / f"rc-{cand}-var-r{n}.jsonl").open()} for n in (1, 2, 3)]
    recs = {v: [recall(r, vids, o) for r in ranks] for v, o in orc.items()}
    var[cand] = {"mean_pairwise_jaccard_top50": round(sum(pj) / len(pj), 3), "median": round(sorted(pj)[len(pj) // 2], 3),
                 "min": round(min(pj), 3), "tasks_jaccard_1.0": sum(x == 1.0 for x in pj),
                 "identical_query_lists": {f"r{i + 1}-r{j + 1}": sum(gens[i][t] == gens[j][t] for t in vids) for i, j in combinations(range(3), 2)},
                 "recall_mean": {v: {k: round(sum(r[k] for r in rr) / 3, 3) for k in rr[0] if "@" in k} for v, rr in recs.items()}}
res["variance_50"] = var
# R-c fidelity of (d)
norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
fid = {"exact": 0, "exact_after_whitespace": 0, "no_4th": 0, "n": 0}
for name in ("380", "var-r1", "var-r2", "var-r3"):
    for l in (FU / f"rc-R-c-{name}.jsonl").open():
        r = json.loads(l)
        fid["n"] += 1
        if len(r["queries"]) < 4:
            fid["no_4th"] += 1
            continue
        d = r["queries"][3]
        fid["exact"] += d == tasks[r["id"]]["text"]
        fid["exact_after_whitespace"] += norm(d) == norm(tasks[r["id"]]["text"])
res["R-c_4th_query_fidelity"] = fid
res["query_stats"] = json.loads((FU / "rc-query-stats.json").read_text())
(FU / "router-cands.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
