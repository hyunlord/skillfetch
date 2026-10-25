#!/usr/bin/env python3
"""Step 2a: oracle picks. Catalog fixed in the system prompt (cached across the 38 calls); 10 tasks per call."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, resolve_ids, run_all  # noqa: E402

tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
valid = {l.split(" | ")[0] for l in (S3 / "gen" / "catalog.md").read_text().splitlines()}
jobs = []
for b in range(0, len(tasks), 10):
    chunk = tasks[b: b + 10]
    prompt = "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in chunk)
    jobs.append((f"oracle2a-{b // 10 + 1:02d}", S3 / "gen" / "sys-oracle.txt", prompt))
res = run_all(jobs, workers=6)
out, bad = {}, []
for r in res:
    assert not r["is_error"], r["name"]
    for x in parse_json_last(r["text"]):
        ids, dropped = resolve_ids(x["skills"], valid)
        bad += [(x["id"], s) for s in dropped]
        out[x["id"]] = {"skills": ids, "reason": x.get("reason", ""), "raw_skills": x["skills"]}
(S3 / "gen" / "oracle-2a.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
u = [r["usage"] or {} for r in res]
print(len(out), "tasks; invalid ids dropped:", bad[:10], len(bad))
print("cache read per call:", [x.get("cache_read_input_tokens") for x in u])
print("none:", sum(1 for v in out.values() if not v["skills"]), "mean picks:", sum(len(v["skills"]) for v in out.values()) / len(out))
