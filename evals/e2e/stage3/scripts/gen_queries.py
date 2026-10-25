#!/usr/bin/env python3
"""Q2 (restatement, router step 1 verbatim) and Q3 (three sentences split from Q2), 20 tasks per call.
Writes queries.jsonl {id, q1, q2, q3: {domain, method, stack}}."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, run_all  # noqa: E402

tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
chunks = [tasks[i: i + 20] for i in range(0, len(tasks), 20)]
r2 = run_all([(f"q2-{n + 1:02d}", S3 / "gen" / "sys-q2.txt", "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in c))
              for n, c in enumerate(chunks)], workers=6)
q2 = {x["id"]: x["q"] for r in r2 for x in parse_json_last(r["text"])}
assert set(q2) == {t["id"] for t in tasks}, len(q2)
r3 = run_all([(f"q3-{n + 1:02d}", S3 / "gen" / "sys-q3.txt", "ITEMS\n\n" + "\n\n".join(f"### {t['id']}\ntask: {t['text']}\nrestatement: {q2[t['id']]}" for t in c))
              for n, c in enumerate(chunks)], workers=6)
q3 = {x["id"]: {k: x[k] for k in ("domain", "method", "stack")} for r in r3 for x in parse_json_last(r["text"])}
assert set(q3) == set(q2), len(q3)
(S3 / "queries.jsonl").write_text("".join(json.dumps({"id": t["id"], "q1": t["text"], "q2": q2[t["id"]], "q3": q3[t["id"]]}, ensure_ascii=False) + "\n" for t in tasks))
for t in tasks[:3] + tasks[200:202]:
    print(t["id"], "|", q2[t["id"]], "|", q3[t["id"]])
