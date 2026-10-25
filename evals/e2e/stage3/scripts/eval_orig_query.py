#!/usr/bin/env python3
"""Does adding the request as typed (q1) as one more query help? Offline, skillfetch a1cbcd5 search_skills(queries=...)
(server-side RRF, k=60; k=50 compact; no profile), stage-3 oracle v2.
  A  stage-3 frozen Q3 (domain / method / stack)          vs  A + q1 (4 queries)
  B  router-rule Q3 (a1cbcd5 step 1, followup/q3r-380)     vs  B + q1
  variance: 50 tasks x 3 generations of B; mean pairwise top-50 Jaccard with / without q1; recall per generation
Writes followup/orig-query.json."""
import json
from itertools import combinations
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S3 = Path(__file__).resolve().parents[1]
FU = S3 / "followup"
SETS = {"all": "relevant", "2a": "relevant_2a", "process": "relevant_process"}
s = Session(Index.load(DEFAULT_INDEX_DIR))
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
q = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "queries.jsonl").open()}
q3r = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (FU / "q3r-380.jsonl").open()}


def top(queries):
    return [r["id"] for r in s.search_skills(None, queries=queries)["results"]]


def recall(rank_by_task, ids):
    out = {}
    for k, f in SETS.items():
        for cut in (10, 50):
            v = [sum(1 for x in orc[t][f] if x in rank_by_task[t][:cut]) / len(orc[t][f]) for t in ids if not tasks[t]["expect_none"] and orc[t][f]]
            out[f"{k}@{cut}"] = round(sum(v) / len(v), 3)
            out[f"{k}_n"] = len(v)
    return out


def jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


ids = list(tasks)
runs = {"A_q3": {t: top([q[t]["q3"][k] for k in ("domain", "method", "stack")]) for t in ids}}
runs["A_q3+q1"] = {t: top([q[t]["q3"][k] for k in ("domain", "method", "stack")] + [tasks[t]["text"]]) for t in ids}
runs["B_q3r"] = {t: top(q3r[t]) for t in ids}
runs["B_q3r+q1"] = {t: top(q3r[t][:3] + [tasks[t]["text"]]) for t in ids}
res = {"recall_380": {name: recall(r, ids) for name, r in runs.items()}}
vids = json.loads((FU / "variance-tasks.json").read_text())
gens = [{json.loads(l)["id"]: json.loads(l)["queries"] for l in (FU / f"q3r-var-r{n}.jsonl").open()} for n in (1, 2, 3)]
var = {}
for label, add in (("without_q1", False), ("with_q1", True)):
    ranks = [{t: top(g[t][:3] + ([tasks[t]["text"]] if add else [])) for t in vids} for g in gens]
    pair = [sum(jac(ranks[i][t], ranks[j][t]) for i, j in combinations(range(3), 2)) / 3 for t in vids]
    rec = [recall(r, vids) for r in ranks]
    var[label] = {"mean_pairwise_jaccard_top50": round(sum(pair) / len(pair), 3), "median": round(sorted(pair)[len(pair) // 2], 3),
                  "tasks_jaccard_1.0": sum(1 for x in pair if x == 1.0),
                  "recall_per_generation": rec,
                  "recall_mean": {k: round(sum(r[k] for r in rec) / 3, 3) for k in rec[0] if "@" in k}}
var["identical_query_lists"] = {f"r{i + 1}-r{j + 1}": sum(gens[i][t] == gens[j][t] for t in vids) for i, j in combinations(range(3), 2)}
res["variance_50"] = var
(FU / "orig-query.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res["recall_380"], indent=1))
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "recall_per_generation"} if isinstance(v, dict) else v for k, v in var.items()}, indent=1))
