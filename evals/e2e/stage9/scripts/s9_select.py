#!/usr/bin/env python3
"""§0/§4-4: one S-b' offline selection on a results file, with stage6/scripts/select_cands.py's wrapper, system prompt
file (stage6/gen/sys-select-S-bp.txt, same bytes), 10-task chunks and lone retry for out-of-range ids.
usage: s9_select.py <results.json> <out.jsonl> [--run]   (without --run: print the call count only; spends nothing)"""
import json
import sys
from pathlib import Path

from s9_common import E2E, tasks

sys.path.insert(0, str(E2E / "stage6" / "scripts"))
from batch import parse_json_last, resolve_ids, run_all  # noqa: E402

res = json.loads(Path(sys.argv[1]).read_text())
queries = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
sysf = E2E / "stage6" / "gen" / "sys-select-S-bp.txt"
T = list(tasks.values())
item = lambda t: (f"### {t['id']}\nRequest:\n{t['text']}\n\nqueries: {json.dumps(queries[t['id']], ensure_ascii=False)}\n\n"  # noqa: E731
                  f"search_skills result:\n{json.dumps(res[t['id']], ensure_ascii=False)}")
chunks = [T[i: i + 10] for i in range(0, len(T), 10)]
tag = Path(sys.argv[2]).stem
if "--run" not in sys.argv:
    print(json.dumps({"calls": len(chunks), "note": "dry: nothing sent"}))
    sys.exit(0)
out = run_all([(f"s9-{tag}-{n + 1:02d}", sysf, "TASKS\n\n" + "\n\n".join(item(t) for t in c)) for n, c in enumerate(chunks)], workers=6)
sel, redo = {}, set()
for c, r in zip(chunks, out):
    assert not r["is_error"], r["name"]
    got = {x["id"]: x.get("skills") or [] for x in parse_json_last(r["text"]) if isinstance(x, dict) and "id" in x}
    for t in c:
        if t["id"] not in got:
            redo.add(t["id"])
            continue
        ids, bad = resolve_ids(got[t["id"]], {y["id"] for y in res[t["id"]]["results"]})
        if bad:
            redo.add(t["id"])
        sel[t["id"]] = ids[:3]
alone = run_all([(f"s9-{tag}-1-{tid}", sysf, "TASKS\n\n" + item(tasks[tid])) for tid in sorted(redo)], workers=6)
for tid, r in zip(sorted(redo), alone):
    x = parse_json_last(r["text"])
    x = x[0] if isinstance(x, list) else x
    sel[tid] = resolve_ids(x.get("skills") or [], {y["id"] for y in res[tid]["results"]})[0][:3]
Path(sys.argv[2]).write_text("".join(json.dumps({"id": t["id"], "skills": sel[t["id"]], "redone_alone": t["id"] in redo}) + "\n" for t in T))
print(json.dumps({"calls": len(out) + len(alone), "redone_alone": len(redo), "cost_usd": round(sum(r.get("cost_usd") or 0 for r in out + alone), 2),
                  "none": sum(not v for v in sel.values())}))
