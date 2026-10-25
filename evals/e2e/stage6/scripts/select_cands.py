#!/usr/bin/env python3
"""Steps 0 and 2: offline selection with each candidate router (select-cands/<C>/SKILL.md, the whole file verbatim in the
system prompt) on the exact search_skills output for the R-c queries (gen/results-rc.json; S-a/S-b/S-c get each
result's `kind` from kind.jsonl, placed after `tier`). The wrapper adds no selection rule: it asks for the ids the agent
would pass to resolve_set, [] when it would not call it. 10 tasks per call; a task whose answer names an id outside its
own 50 is redone alone. Writes select-<C>.jsonl {id, skills, redone_alone}.
usage: select_cands.py S-0 S-a S-b S-c   (REP=2 / REP=3: independent repeats, select-<C>-rep<N>.jsonl, own cache names)"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S6, parse_json_last, resolve_ids, run_all  # noqa: E402

WRAP = """You are a coding agent following your "skillfetch router" skill at the start of a developer's task. Steps 1-3 have
already run: for each task you get the user's request, the `queries` you passed to `search_skills`, and the exact result
it returned. Do only the selection in step 4. Your router skill, verbatim:

<skill>
{skill}</skill>

For each task, give the skill ids you would pass to `resolve_set` as `auto_ids`, following the skill, or an empty list if
you would not call `resolve_set`. Use ids exactly as given in that task's result. You cannot see the code.
Output JSON only: [{{"id": "<task id>", "skills": ["<skill id>", ...]}}] in the order given.
"""
tasks = [json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()]
queries = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (S6.parent / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
base = json.loads((S6 / "gen" / "results-rc.json").read_text())
kind = {json.loads(l)["id"]: json.loads(l)["kind"] for l in (S6 / "kind.jsonl").open()}


def with_kind(res):
    out = []
    for r in res["results"]:
        x = {}
        for k, v in r.items():
            x[k] = v
            if k == "tier":
                x["kind"] = kind[r["id"]]
        out.append(x)
    return {**res, "results": out}


def item(t, res):
    return (f"### {t['id']}\nRequest:\n{t['text']}\n\nqueries: {json.dumps(queries[t['id']], ensure_ascii=False)}\n\n"
            f"search_skills result:\n{json.dumps(res[t['id']], ensure_ascii=False)}")


NO_KIND = {"S-0", "S-bp"}  # search results exactly as the server returns them (no kind field)
REP = os.environ.get("REP", "1")
SUF = "" if REP == "1" else f"-rep{REP}"
for cand in sys.argv[1:]:
    sysf = S6 / "gen" / f"sys-select-{cand}.txt"
    sysf.write_text(WRAP.format(skill=(S6 / "select-cands" / cand / "SKILL.md").read_text()))
    res = base if cand in NO_KIND else {t: with_kind(v) for t, v in base.items()}
    chunks = [tasks[i: i + 10] for i in range(0, len(tasks), 10)]
    out = run_all([(f"sel{SUF}-{cand}-{n + 1:02d}", sysf, "TASKS\n\n" + "\n\n".join(item(t, res) for t in c)) for n, c in enumerate(chunks)], workers=6)
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
    by = {t["id"]: t for t in tasks}
    alone = run_all([(f"sel1{SUF}-{cand}-{tid}", sysf, "TASKS\n\n" + item(by[tid], res)) for tid in sorted(redo)], workers=6)
    still = []
    for tid, r in zip(sorted(redo), alone):
        x = parse_json_last(r["text"])
        x = x[0] if isinstance(x, list) else x
        ids, bad = resolve_ids(x.get("skills") or [], {y["id"] for y in res[tid]["results"]})
        still += bad
        sel[tid] = ids[:3]
    (S6 / f"select-{cand}{SUF}.jsonl").write_text("".join(json.dumps({"id": t["id"], "skills": sel[t["id"]], "redone_alone": t["id"] in redo}) + "\n" for t in tasks))
    cost = sum(r.get("cost_usd") or 0 for r in out + alone)
    print(cand, "calls", len(out) + len(alone), "redone alone", len(redo), "still outside", len(still), "cost", round(cost, 2),
          "| none", sum(not v for v in sel.values()), "mean", round(sum(len(v) for v in sel.values()) / len(sel), 2))
