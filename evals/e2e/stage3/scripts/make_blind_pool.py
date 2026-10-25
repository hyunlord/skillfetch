#!/usr/bin/env python3
"""Cross-label input: 120 tasks from evals/retrieval (= frozen stage-3 tasks/oracle v2), stratified: 9 per task type
(spread over phrasings and stacks) + 12 trivial; every candidate of each task's graded pool as one row
{task_id, task_text, candidate_id, title, full_summary, tags} — no grade, process flag or pool source; rows shuffled
within each task. Writes blind-pool-120.jsonl, blind-pool-120-ids.json and rubric-2b.md (the 2b prompt verbatim)."""
import json
import random
from collections import defaultdict
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
recs = {}
for l in (Path.home() / ".skillfetch/index/skills.jsonl").open():
    r = json.loads(l)
    recs[r["id"]] = r
tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
rng = random.Random("cross-label-120")
by = defaultdict(list)
for t in tasks:
    by[t["task_type"]].append(t)
pick = []
for tt, ts in sorted(by.items()):
    n = 12 if tt == "trivial" else 9
    rng.shuffle(ts)
    chosen, seen = [], set()
    for t in ts:  # first pass: distinct (phrasing, stack); then fill
        key = (t["phrasing"], t["stack"])
        if key not in seen and len(chosen) < n:
            chosen.append(t); seen.add(key)
    for t in ts:
        if len(chosen) >= n:
            break
        if t not in chosen:
            chosen.append(t)
    pick += chosen
rows = []
for t in pick:
    cands = [x["skill"] for x in orc[t["id"]]["pool"]]
    rng.shuffle(cands)
    for c in cands:
        r = recs[c]
        rows.append({"task_id": t["id"], "task_text": t["text"], "candidate_id": c, "title": r.get("title") or r["name"],
                     "full_summary": r.get("summary") or r.get("description", ""), "tags": r.get("tags") or {}})
(S3 / "blind-pool-120.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
(S3 / "blind-pool-120-ids.json").write_text(json.dumps([t["id"] for t in pick]))
prompt = (S3 / "gen" / "sys-grade.txt").read_text()
(S3 / "rubric-2b.md").write_text(
    "# Grading rubric (stage 3, step 2b) — the prompt used for the Opus labels, verbatim\n\n"
    "Each task in `blind-pool-120.jsonl` is graded on its own: the task text plus all its candidate rows "
    "(candidate_id, title, full_summary, tags).\n\n```text\n" + prompt + "```\n\n"
    "## Return file: `gpt-grades-120.jsonl`\n\nOne line per row of `blind-pool-120.jsonl`: "
    '`{"task_id": "...", "candidate_id": "...", "grade": 0-3, "process": true|false}`.\n')
n = defaultdict(int)
for t in pick:
    n[t["task_type"]] += 1
print(len(pick), "tasks,", len(rows), "rows;", dict(n), "| phrasings", dict(__import__("collections").Counter(t["phrasing"] for t in pick)))
