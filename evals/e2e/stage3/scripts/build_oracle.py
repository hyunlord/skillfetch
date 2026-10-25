#!/usr/bin/env python3
"""oracle.jsonl: per task the graded pool (skill, sources, grade 0-3, process flag), the relevant set (grade >= 2),
its process subset, and the 2a picks/reason."""
import json
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
pools = json.loads((S3 / "gen" / "pools.json").read_text())
g = json.loads((S3 / "gen" / "grades-2b.json").read_text())
o2a = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle-2a.jsonl").open()}
rows = []
for line in (S3 / "tasks.jsonl").open():
    t = json.loads(line)
    p = pools[t["id"]]
    pool = [{"skill": s, "sources": p["sources"][s], **g[t["id"]][s]} for s in p["order"]]
    rel = sorted((x for x in pool if x["grade"] >= 2), key=lambda x: -x["grade"])
    rows.append({"id": t["id"], "expect_none": t["expect_none"], "relevant": [x["skill"] for x in rel],
                 "relevant_grades": {x["skill"]: x["grade"] for x in rel},
                 "relevant_process": [x["skill"] for x in rel if x["process"]],
                 "oracle_2a": o2a[t["id"]]["skills"], "oracle_2a_reason": o2a[t["id"]]["reason"], "pool": pool})
(S3 / "oracle.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
n = [len(r["relevant"]) for r in rows]
print(len(rows), "tasks; relevant (grade>=2) per task: none", sum(1 for x in n if x == 0), "mean", round(sum(n) / len(n), 2),
      "| expect_none with relevant:", sum(1 for r in rows if r["expect_none"] and r["relevant"]),
      "| tasks with a process skill:", sum(1 for r in rows if r["relevant_process"]))
