#!/usr/bin/env python3
"""Router step-1 candidates R-a / R-b / R-c (router-cands/R-*/SKILL.md). The system prompt carries each candidate's step 1
cut verbatim from its SKILL.md (from "1. **Restate" up to "2. "), inside one wrapper shared by all three; isolated
claude -p (batch.py). Per candidate: 380 tasks (20 per call) -> followup/rc-<cand>-380.jsonl and the 50 variance tasks
(followup/variance-tasks.json, 10 per call) x 3 independent generations -> followup/rc-<cand>-var-r{1,2,3}.jsonl."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from batch import S3, parse_json_last, run_all  # noqa: E402

FU = S3 / "followup"
CANDS = ["R-a", "R-b", "R-c"]
WRAP = """You are a coding agent about to start a developer's task in their repository. Before doing anything else you
follow this step from your instructions (verbatim):

{step}
You have not read any code yet. For each task below, write the `queries` you would pass to `search_skills` under that
step, in the order the step gives them. Output JSON only: [{{"id": "<task id>", "queries": ["<query>", ...]}}] in the order given.
"""
tasks = [json.loads(l) for l in (S3 / "tasks.jsonl").open()]
vids = set(json.loads((FU / "variance-tasks.json").read_text()))


def step1(cand):
    t = (S3 / "router-cands" / cand / "SKILL.md").read_text()
    return t[t.index("1. **Restate"):t.index("2. If no")]


def gen(cand, name, sel, size):
    sysf = S3 / "gen" / f"sys-rc-{cand}.txt"
    chunks = [sel[i: i + size] for i in range(0, len(sel), size)]
    jobs = [(f"rc-{cand}-{name}-{n + 1:02d}", sysf, "TASKS\n\n" + "\n\n".join(f"### {t['id']}\n{t['text']}" for t in c))
            for n, c in enumerate(chunks)]
    return jobs, sel


if __name__ == "__main__":
    plan = []
    for cand in CANDS:
        (S3 / "gen" / f"sys-rc-{cand}.txt").write_text(WRAP.format(step=step1(cand)))
        plan.append((cand, "380", *gen(cand, "380", tasks, 20)))
        for rep in (1, 2, 3):
            plan.append((cand, f"var-r{rep}", *gen(cand, f"var-r{rep}", [t for t in tasks if t["id"] in vids], 10)))
    alljobs = [j for p in plan for j in p[2]]
    res = {r["name"]: r for r in run_all(alljobs, workers=8)}
    cost = sum(r.get("cost_usd") or 0 for r in res.values())
    for cand, name, jobs, sel in plan:
        out = {}
        for j in jobs:
            for x in parse_json_last(res[j[0]]["text"]):
                out[x["id"]] = x["queries"]
        assert set(out) == {t["id"] for t in sel}, (cand, name, len(out))
        (FU / f"rc-{cand}-{name}.jsonl").write_text("".join(json.dumps({"id": t["id"], "queries": out[t["id"]]}, ensure_ascii=False) + "\n" for t in sel))
    print(len(alljobs), "calls, cost_usd", round(cost, 2))
