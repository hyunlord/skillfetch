#!/usr/bin/env python3
"""Router-rule Q3 (skillfetch a1cbcd5 router step 1: up to three sentences (a) what, (b) how if asked, (c) stack/files),
isolated claude -p, gen/sys-q3r.txt (= stage4/gen/sys-q3r.txt).
  gen_q3r.py all       -> followup/q3r-380.jsonl (380 tasks, 20 per call, one generation)
  gen_q3r.py variance  -> followup/variance-tasks.json (50 stratified) + followup/q3r-var-r{1,2,3}.jsonl
                          (3 independent generations, the same 10-task batches each time)"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, run_all  # noqa: E402

FU = S3 / "followup"
tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}


def gen(name, chunk_tasks, size):
    chunks = [chunk_tasks[i: i + size] for i in range(0, len(chunk_tasks), size)]
    res = run_all([(f"{name}-{n + 1:02d}", S3 / "gen" / "sys-q3r.txt", "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in c))
                   for n, c in enumerate(chunks)], workers=6)
    out = {x["id"]: x["queries"] for r in res for x in parse_json_last(r["text"])}
    assert set(out) == {t["id"] for t in chunk_tasks}, (name, len(out))
    return out


if sys.argv[1] == "all":
    q = gen("q3r380", tasks, 20)
    (FU / "q3r-380.jsonl").write_text("".join(json.dumps({"id": t["id"], "queries": q[t["id"]]}, ensure_ascii=False) + "\n" for t in tasks))
else:
    vt = FU / "variance-tasks.json"
    if not vt.exists():  # 50: non-trivial with a relevant set, 10 per phrasing, spread over task types
        rng = random.Random("variance-50")
        pick = []
        for ph in ("terminal", "normal", "spec", "korean", "directive"):
            pool = [t for t in tasks if t["phrasing"] == ph and not t["expect_none"] and orc[t["id"]]["relevant"]]
            rng.shuffle(pool)
            used = set()
            for t in pool:  # one per task type first
                if t["task_type"] not in used:
                    pick.append(t["id"]); used.add(t["task_type"])
                if len([p for p in pick if next(x for x in tasks if x["id"] == p)["phrasing"] == ph]) == 10:
                    break
        vt.write_text(json.dumps(pick))
    ids = json.loads(vt.read_text())
    sel = [t for t in tasks if t["id"] in set(ids)]
    for rep in (1, 2, 3):
        q = gen(f"q3rvar-r{rep}", sel, 10)
        (FU / f"q3r-var-r{rep}.jsonl").write_text("".join(json.dumps({"id": t["id"], "queries": q[t["id"]]}, ensure_ascii=False) + "\n" for t in sel))
    print(len(ids), "variance tasks x 3 generations")
