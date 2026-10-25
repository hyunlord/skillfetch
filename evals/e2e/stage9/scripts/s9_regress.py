#!/usr/bin/env python3
"""§2: fixed baseline labels and denominators; R-c hit@50 / recall@50 on baseline vs staging results; reject if any of
the four drops > 0.01. usage: s9_regress.py <baseline_results.json> <staging_results.json> -> regress.json"""
import json
import statistics as st
import sys
from pathlib import Path

from s9_common import OUT, BASE_INDEX, S9, rel_sets, records, tasks, v3, vb

ids = lambda p: {t: [x["id"] for x in r.get("results", [])] for t, r in json.loads(Path(p).read_text()).items()}  # noqa: E731
B, S = ids(sys.argv[1]), ids(sys.argv[2])
base_ids = set(records(BASE_INDEX))
labs = {"v3": {t: set(v3[t]["relevant"]) for t in tasks}, "v5-ss-b": rel_sets(vb, base_ids)}
out = {}
for ln, R in labs.items():
    ts = [t for t in tasks if not tasks[t]["expect_none"] and R[t]]
    row = {"n": len(ts)}
    for nm, rk in (("baseline", B), ("staging", S)):
        row[nm] = {"hit@50": round(sum(bool(set(rk[t][:50]) & R[t]) for t in ts) / len(ts), 4),
                   "recall@50": round(st.mean(len(set(rk[t][:50]) & R[t]) / len(R[t]) for t in ts), 4)}
    row["delta"] = {m: round(row["staging"][m] - row["baseline"][m], 4) for m in ("hit@50", "recall@50")}
    out[ln] = row
out["reject"] = any(out[ln]["delta"][m] < -0.01 for ln in labs for m in ("hit@50", "recall@50"))
out["baseline_matches_stage8"] = {"v3": (round(out["v3"]["baseline"]["hit@50"], 3), round(out["v3"]["baseline"]["recall@50"], 3)) == (0.930, 0.808),
                                  "v5-ss-b": (round(out["v5-ss-b"]["baseline"]["hit@50"], 3), round(out["v5-ss-b"]["baseline"]["recall@50"], 3)) == (0.941, 0.822)}
(OUT / "regress.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out))
