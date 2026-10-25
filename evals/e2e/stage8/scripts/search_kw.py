#!/usr/bin/env python3
"""Stage 8 §4-5: our search_skills (k=50, no profile; same call as stage6/scripts/search_rc.py) for R-c, [kw] and
R-c + [kw]. Run under uvx --from git+https://github.com/hyunlord/skillfetch@38dcb69. Writes search-kw.json
{cond: {task: [ids]}} and checks R-c against stage6/gen/results-rc.json."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import DEFAULT_TIERS, MAX_QUERY_CHARS, Session

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
s = Session(Index.load(DEFAULT_INDEX_DIR))
rc = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
kw = {json.loads(l)["id"]: json.loads(l)["query"] for l in (S8 / "kw-queries.jsonl").open()}
errs = {}


def ids(r, key):
    if "results" not in r:  # recorded, not hidden: e.g. a refused / over-long query
        errs[key] = r
        return []
    return [x["id"] for x in r["results"]]
out = {"R-c": {t: ids(s.search_skills(None, queries=q), f"R-c {t}") for t, q in rc.items()},
       "kw": {t: ids(s.search_skills(None, queries=[kw[t]]), f"kw {t}") for t in rc},
       # 5 queries exceed the session cap (MAX_QUERIES = 4): call the same searcher.search_many the session uses,
       # with the same arguments (cut to MAX_QUERY_CHARS, no profile, k=50, default tiers) — RRF code unchanged
       "R-c+kw": {t: [x["id"] for x in s.searcher.search_many([q[:MAX_QUERY_CHARS] for q in rc[t] + [kw[t]]], None, 50, list(DEFAULT_TIERS))] for t in rc},
       "R-c via search_many": {t: [x["id"] for x in s.searcher.search_many([q[:MAX_QUERY_CHARS] for q in rc[t]], None, 50, list(DEFAULT_TIERS))] for t in rc}}
out["_errors"] = errs
old = json.loads((E2E / "stage6" / "gen" / "results-rc.json").read_text())
same = sum(out["R-c"][t] == [x["id"] for x in old[t]["results"]] for t in rc)
same_many = sum(out["R-c via search_many"][t] == out["R-c"][t] for t in rc)
(S8 / "search-kw.json").write_text(json.dumps(out))
print(json.dumps({"rc_identical_to_results_rc": f"{same}/{len(rc)}", "search_many_path_identical_to_session": f"{same_many}/{len(rc)}",
                  "kw_empty_tasks": [t for t, v in out["kw"].items() if not v], "kw_empty": sum(not v for v in out["kw"].values()),
                  "errors": {k: str(v)[:300] for k, v in errs.items()},
                  "len_median": {c: sorted(len(v) for v in d.values())[190] for c, d in out.items() if c != "_errors"}}))
