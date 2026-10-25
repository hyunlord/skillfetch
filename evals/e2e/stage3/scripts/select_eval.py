#!/usr/bin/env python3
"""Step 4: offline selection. Q2 search_skills output (compact, k=50, as the server returns it) + router step 4 and
its skip rules (gen/sys-select.txt), 20 tasks per call -> selection.jsonl {id, query, skills}.
Run in a venv with skillfetch 64f4bd8 (for the exact compact results)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, resolve_ids, run_all  # noqa: E402
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index  # noqa: E402
from skillfetch.mcp.session import Session  # noqa: E402

s = Session(Index.load(DEFAULT_INDEX_DIR))
tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
q2 = {json.loads(l)["id"]: json.loads(l)["q2"] for l in (S3 / "queries.jsonl").open()}
results = {t["id"]: s.search_skills(q2[t["id"]]) for t in tasks}
chunks = [tasks[i: i + 20] for i in range(0, len(tasks), 20)]
jobs = [(f"select-{n + 1:02d}", S3 / "gen" / "sys-select.txt", "TASKS\n\n" + "\n\n".join(
    f"### {t['id']}\nTask:\n{t['text']}\n\nsearch_skills result:\n{json.dumps(results[t['id']], ensure_ascii=False)}" for t in c))
    for n, c in enumerate(chunks)]
res = run_all(jobs, workers=5)
sel, dropped = {}, []
for c, r in zip(chunks, res):
    assert not r["is_error"], r["name"]
    for x in parse_json_last(r["text"]):
        valid = {y["id"] for y in results.get(x["id"], {}).get("results", [])}
        ids, bad = resolve_ids(x.get("skills") or [], valid)
        dropped += [(x["id"], b) for b in bad]
        sel[x["id"]] = ids[:3]
missing = [t["id"] for t in tasks if t["id"] not in sel]
(S3 / "selection.jsonl").write_text("".join(json.dumps({"id": t["id"], "query": q2[t["id"]], "skills": sel.get(t["id"])}) + "\n" for t in tasks))
print(len(sel), "selected; missing", missing, "; dropped ids (not in the 50)", dropped[:8], len(dropped))
print("cache read per call:", [(r["usage"] or {}).get("cache_read_input_tokens") for r in res])

# tasks whose batched answer named an id outside their own 50 (borrowed from another task in the batch): redo alone
redo = sorted({d[0] for d in dropped})
if redo:
    by = {t["id"]: t for t in tasks}
    res1 = run_all([(f"select1-{tid}", S3 / "gen" / "sys-select.txt",
                     f"TASKS\n\n### {tid}\nTask:\n{by[tid]['text']}\n\nsearch_skills result:\n{json.dumps(results[tid], ensure_ascii=False)}")
                    for tid in redo], workers=6)
    still = []
    for tid, r in zip(redo, res1):
        x = parse_json_last(r["text"])[0]
        ids, bad = resolve_ids(x.get("skills") or [], {y["id"] for y in results[tid]["results"]})
        still += bad
        sel[tid] = ids[:3]
    rows = [{"id": t["id"], "query": q2[t["id"]], "skills": sel[t["id"]], **({"redone_alone": True} if t["id"] in redo else {})} for t in tasks]
    (S3 / "selection.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print("redone alone:", len(redo), "tasks; ids still outside their 50:", still)
