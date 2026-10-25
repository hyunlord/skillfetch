#!/usr/bin/env python3
"""Step 2b (and 2c with --alt): grade each task's pool 0-3 + process flag, one call per task.
2b: gen/sys-grade.txt over all 380 tasks -> gen/grades-2b.json
2c: gen/sys-grade-alt.txt over the 40 tasks in gen/relabel-ids.json -> gen/grades-2c.json"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, resolve_ids, run_all  # noqa: E402
from cards import card  # noqa: E402

ALT = "--alt" in sys.argv
tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
pools = json.loads((S3 / "gen" / "pools.json").read_text())
if ALT:
    rel = S3 / "gen" / "relabel-ids.json"
    if not rel.exists():  # 40 tasks: 3 per task type (36) + 4 trivial, seeded
        rng = random.Random("relabel-2c")
        ids = []
        for tt in sorted({t["task_type"] for t in tasks}):
            pick = [t["id"] for t in tasks if t["task_type"] == tt]
            ids += rng.sample(pick, 4 if tt == "trivial" else 3)
        rel.write_text(json.dumps(sorted(ids)))
    keep = set(json.loads(rel.read_text()))
    tasks = [t for t in tasks if t["id"] in keep]


jobs = []
for t in tasks:
    order = pools[t["id"]]["order"]
    prompt = f"TASK\n{t['text']}\n\nCANDIDATES ({len(order)})\n" + "\n".join(card(s) for s in order)
    jobs.append((f"{'grade2c' if ALT else 'grade2b'}-{t['id']}", S3 / "gen" / ("sys-grade-alt.txt" if ALT else "sys-grade.txt"), prompt))
res = run_all(jobs, workers=8)
out, problems = {}, []
for t, r in zip(tasks, res):
    if r["is_error"]:
        problems.append((t["id"], "call error"))
        continue
    order = pools[t["id"]]["order"]
    g = {}
    for x in parse_json_last(r["text"]):
        ids, _ = resolve_ids([x["skill"]], set(order))
        if ids:
            g[ids[0]] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    missing = [s for s in order if s not in g]
    if missing:
        problems.append((t["id"], f"missing {len(missing)}"))
    out[t["id"]] = g
(S3 / "gen" / ("grades-2c.json" if ALT else "grades-2b.json")).write_text(json.dumps(out, indent=1))
print(len(out), "tasks graded; problems:", problems[:10], len(problems))
