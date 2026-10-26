#!/usr/bin/env python3
"""Stage 11 DESIGN §3.2 pre-run check for the bundle (4) additions, Stage 10 §2.1 criterion with blind grading: R-c top-50
(Stage 3 R-c queries, k=50, no profile) on the Stage 10 release and staging-4 copies, blind 2b grading of the union per
task (same procedure as s11_b3_precheck.py, seed s11-b4pre-<task>). A task enters bundle (4) only if a grade >= 2 skill
is in the staging-4 top-50 and no grade >= 2 skill is in the release index (whether or not it reached the release
top-50). The task text is the Stage 3 text verbatim (repos are built to match it).
usage:
  search (skillfetch 3fef3f8):  uvx --from ~/skillfetch-e2e-wt/s10-server/3fef3f8 python s11_b4_precheck.py search <task>...
  grade  (system python):       python3 s11_b4_precheck.py grade <task>... [--run]
outputs (merged per task): stage11-private/b4/precheck-search.json, precheck-grades.jsonl, precheck-labels.json,
precheck.json"""
import json
import random
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
S10 = E2E / "stage10"
OUT = E2E / "stage11-private" / "b4"
TASKS = [a for a in sys.argv[2:] if not a.startswith("--")]
OUT.mkdir(parents=True, exist_ok=True)


def deep(old, new):
    for k, v in new.items():
        old[k] = deep(old.get(k, {}), v) if isinstance(v, dict) and isinstance(old.get(k, {}), dict) else v
    return old


def merge(name, new):
    f = OUT / name
    old = deep(json.loads(f.read_text()) if f.exists() else {}, new)
    f.write_text(json.dumps(old, indent=1))
    return old

if sys.argv[1] == "search":
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session

    q = {json.loads(l)["id"]: json.loads(l)["queries"] for l in (E2E / "stage3" / "followup" / "rc-R-c-380.jsonl").open()}
    res = {}
    for idx in ("release", "staging-4"):
        s = Session(Index.load(S10 / "index" / idx))
        res[idx] = {t: [r["id"] for r in s.search_skills(None, queries=q[t])["results"][:50]] for t in TASKS}
    merge("precheck-search.json", {"queries": {t: q[t] for t in TASKS}, "top50": res})
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
    random.Random(f"s11-b4pre-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s11-b4pre-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
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
rel_ids = {json.loads(l)["id"] for l in (S10 / "index" / "release" / "skills.jsonl").open()}
for r in rows:
    r["in_release_index"] = r["skill"] in rel_ids
summ = {}
for t in TASKS:
    tr = [r for r in rows if r["task"] == t]
    st = sorted((r["skill"], r["grade"]) for r in tr if r["grade"] >= 2 and r["in_staging4_top50"])
    rel = sorted((r["skill"], r["grade"]) for r in tr if r["grade"] >= 2 and r["in_release_index"])
    summ[t] = {"graded": len(tr), "staging4_top50_ge2": st, "release_index_ge2": rel, "enter_bundle": bool(st) and not rel}
gf = OUT / "precheck-grades.jsonl"
keep = [json.loads(l) for l in gf.open()] if gf.exists() else []
gf.write_text("".join(json.dumps(r) + "\n" for r in [r for r in keep if r["task"] not in TASKS] + rows))
merge("precheck-labels.json", labels)
res = merge("precheck.json", {"tasks": summ, "problems": {t: [p for p in problems if p["task"] == t] for t in TASKS},
                             "cost_usd": {"+".join(TASKS): round(sum(r.get("cost_usd") or 0 for r in out), 3)}})
print(json.dumps(res, indent=1))
