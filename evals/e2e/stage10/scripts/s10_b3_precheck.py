#!/usr/bin/env python3
"""DESIGN §11.1 pre-run check for the new bundle (3): R-c top-50 (Stage 3 R-c queries, k=50, no profile) on the release
and staging-4 copies, then blind 2b grading of the union per task (title = name, summary = 220-char description,
stage3/gen/sys-grade.txt, one isolated `claude -p` per task, seed s10-b3pre-<task>, labels m01...). A task enters the
bundle only if no graded skill has grade >= 2 (either index). The task text is the Stage 3 text verbatim (the repos are
built to match its paths), so the R-c queries are stage3/followup/rc-R-c-380.jsonl.
usage:
  search (skillfetch 3fef3f8):  uvx --from ~/skillfetch-e2e-wt/s10-server/3fef3f8 python s10_b3_precheck.py search
  grade  (system python):       python3 s10_b3_precheck.py grade [--run]
outputs: stage10-private/b3new/precheck-search.json, precheck-grades.jsonl, precheck-labels.json, precheck.json"""
import json
import random
import re
import sys
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
E2E = S10.parent
OUT = E2E / "stage10-private" / "b3new"
TASKS = ["t001", "t033", "t114", "t276"]
OUT.mkdir(parents=True, exist_ok=True)

if sys.argv[1] == "search":
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session

    q = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
    res = {}
    for idx in ("release", "staging-4"):
        s = Session(Index.load(S10 / "index" / idx))
        res[idx] = {t: [r["id"] for r in s.search_skills(None, queries=q[t])["results"][:50]] for t in TASKS}
    (OUT / "precheck-search.json").write_text(json.dumps({"queries": {t: q[t] for t in TASKS}, "top50": res}, indent=1))
    print(json.dumps({idx: {t: len(v) for t, v in r.items()} for idx, r in res.items()}))
    sys.exit(0)

sys.path.insert(0, str(E2E / "stage6" / "scripts"))
srch = json.loads((OUT / "precheck-search.json").read_text())
tasks = {json.loads(l)["id"]: json.loads(l) for l in (E2E / "stage3" / "tasks.jsonl").open()}
recs = {}
for idx in ("release", "staging-4"):
    for line in (S10 / "index" / idx / "skills.jsonl").open():
        r = json.loads(line)
        recs[r["id"]] = r
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731
cands = {t: sorted(set(srch["top50"]["release"][t]) | set(srch["top50"]["staging-4"][t])) for t in TASKS}
n = sum(len(v) for v in cands.values())
print(json.dumps({"rows": n, "per_task": {t: len(v) for t, v in cands.items()}, "estimate_usd": round(len(TASKS) * 0.011 + n * 0.001, 2)}))
if "--run" not in sys.argv:
    sys.exit(0)
from batch import parse_json_last, run_all  # noqa: E402

labels, jobs = {}, []
for t in TASKS:
    c = list(cands[t])
    random.Random(f"s10-b3pre-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s10-b3pre-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
out = run_all(jobs, workers=4)
rows, problems = [], []
for (t, lab), r in zip(labels.items(), out):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = int(x["grade"])
    if set(g) != set(lab):
        problems.append({"task": t, "missing": sorted(set(lab) - set(g))})
    for l, gr in g.items():
        k = lab[l]
        rows.append({"task": t, "skill": k, "grade": gr, "in_release_top50": k in srch["top50"]["release"][t],
                     "in_staging4_top50": k in srch["top50"]["staging-4"][t]})
(OUT / "precheck-grades.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
(OUT / "precheck-labels.json").write_text(json.dumps(labels, indent=0))
summ = {t: {"graded": sum(r["task"] == t for r in rows),
            "grade_ge2": sorted((r["skill"], r["grade"]) for r in rows if r["task"] == t and r["grade"] >= 2),
            "enter_bundle": not any(r["task"] == t and r["grade"] >= 2 for r in rows)} for t in TASKS}
res = {"tasks": summ, "problems": problems, "cost_usd": round(sum(r.get("cost_usd") or 0 for r in out), 3)}
(OUT / "precheck.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
