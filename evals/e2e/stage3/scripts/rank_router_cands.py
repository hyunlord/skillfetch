#!/usr/bin/env python3
"""Top-50 of skillfetch a1cbcd5 search_skills(queries=...) (server-side RRF k=60, compact k=50, no profile) for the router
candidates' generated queries (followup/rc-*.jsonl) and, for reference, the stage-3 frozen Q3. Run under
uvx --from git+https://github.com/hyunlord/skillfetch@a1cbcd5 python scripts/rank_router_cands.py
Writes followup/rc-rankings.json {run: {task: [50 ids]}} and followup/rc-query-stats.json."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S3 = Path(__file__).resolve().parents[1]
FU = S3 / "followup"
s = Session(Index.load(DEFAULT_INDEX_DIR))
q = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "queries.jsonl").open()}
runs, stats = {}, {}
runs["Q3-stage3"] = {t: [r["id"] for r in s.search_skills(None, queries=[v["q3"][k] for k in ("domain", "method", "stack")])["results"]]
                     for t, v in q.items()}
for cand in ("R-a", "R-b", "R-c"):
    for name in ("380", "var-r1", "var-r2", "var-r3"):
        gen = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (FU / f"rc-{cand}-{name}.jsonl").open()}
        st = {"n_queries": {}, "truncated_to_4": 0}
        out = {}
        for t, qs in gen.items():
            qs = [x for x in qs if isinstance(x, str) and x.strip()]
            st["n_queries"][len(qs)] = st["n_queries"].get(len(qs), 0) + 1
            if len(qs) > 4:
                st["truncated_to_4"] += 1
                qs = qs[:4]
            out[t] = [r["id"] for r in s.search_skills(None, queries=qs)["results"]]
        runs[f"{cand}|{name}"] = out
        stats[f"{cand}|{name}"] = st
(FU / "rc-rankings.json").write_text(json.dumps(runs))
(FU / "rc-query-stats.json").write_text(json.dumps(stats, indent=1))
print(json.dumps(stats, indent=1))
