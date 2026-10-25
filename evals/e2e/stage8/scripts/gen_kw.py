#!/usr/bin/env python3
"""Stage 8 §2-추가 3: kw query per task (380) from an isolated `claude -p` whose system prompt is load_skill's own
description + query/context argument descriptions (sys-kw.txt). User prompt = task text only. Writes kw-queries.jsonl."""
import json
import re
import sys
from pathlib import Path

S8 = Path(__file__).resolve().parents[1]
E2E = S8.parent
sys.path.insert(0, str(E2E / "stage6" / "scripts"))
from batch import run_all  # noqa: E402

tasks = [json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()]
res = run_all([(f"s8-kw-{t['id']}", S8 / "sys-kw.txt", t["text"]) for t in tasks], workers=8)
rows, bad = [], []
for t, r in zip(tasks, res):
    assert not r["is_error"], r["name"]
    q = r["text"].strip().strip("`").strip().strip('"').strip("'").strip()
    q = q.splitlines()[0].strip() if q else q
    n = len(re.findall(r"\S+", q))
    rows.append({"id": t["id"], "query": q, "words": n, "raw": r["text"]})
    if not 2 <= n <= 6:
        bad.append((t["id"], q))
(S8 / "kw-queries.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
summ = {"n": len(rows), "outside_2_6_words": len(bad), "examples_outside": bad[:10],
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 2),
        "multi_line_raw": sum("\n" in r["text"].strip() for r in res)}
(S8 / "kw-summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
print(json.dumps(summ, ensure_ascii=False))
