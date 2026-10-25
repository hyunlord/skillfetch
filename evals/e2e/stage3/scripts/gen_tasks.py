#!/usr/bin/env python3
"""Step 1b: generate the task texts with isolated claude -p calls (gen/sys-generate.txt as system prompt):
12 batches of 25 cells (one per task type), 1 batch of 40 trivial requests, 1 batch of 20 direction pairs.
Writes gen/generated.json (all raw items, cell metadata attached)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json, run_all  # noqa: E402

SYS = S3 / "gen" / "sys-generate.txt"
d = json.loads((S3 / "gen" / "cells.json").read_text())
jobs, meta = [], {}
types = sorted({c["task_type"] for c in d["cells"]}, key=[c["task_type"] for c in d["cells"]].index)
for t in types:
    items = [c for c in d["cells"] if c["task_type"] == t]
    lines = [f"{i + 1}. task_type={c['task_type']}, stack={c['stack']}, phrasing={c['phrasing']}" for i, c in enumerate(items)]
    jobs.append((f"gen-{t}", SYS, f"Write {len(items)} requests, one per item:\n" + "\n".join(lines)))
    meta[f"gen-{t}"] = items
tr = d["trivial"]
lines = [f"{i + 1}. stack={c['stack']}, phrasing={c['phrasing']}, kind={c['kind']}" for i, c in enumerate(tr)]
jobs.append(("gen-trivial", SYS, "Write 40 TRIVIAL requests: each needs no expertise and no plan — a one-line fix, a rename, a typo, "
             "a constant or version change, an import fix, a comment edit, or just a question to answer about the code. "
             "They must still sound real (file names, identifiers). The task_type rules above do not apply; follow each item's kind:\n" + "\n".join(lines)))
meta["gen-trivial"] = tr
pr = d["pairs"]
lines = [f"{i + 1}. task_type={c['task_type']}, stack={c['stack']}, direction A = {c['directions'][0]}, direction B = {c['directions'][1]}" for i, c in enumerate(pr)]
jobs.append(("gen-pairs", SYS, "Write 20 PAIRS. For each item write one realistic request (phrasing: normal or spec, your choice) and then "
             "two versions of it that are word for word the same except for one added sentence or clause giving the direction "
             "(A or B). Output: [{\"i\": n, \"a\": \"<request with direction A>\", \"b\": \"<request with direction B>\"}]\n" + "\n".join(lines)))
meta["gen-pairs"] = pr
res = run_all(jobs, workers=7)
out = {}
for r in res:
    assert not r["is_error"], r
    out[r["name"]] = {"items": parse_json(r["text"]), "meta": meta[r["name"]], "usage": r["usage"], "cost_usd": r["cost_usd"]}
    print(r["name"], len(out[r["name"]]["items"]), r["secs"], (r["usage"] or {}).get("cache_read_input_tokens"))
(S3 / "gen" / "generated.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
