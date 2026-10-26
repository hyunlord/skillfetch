#!/usr/bin/env python3
"""Stage 11 DESIGN §3.1 pre-run check for bundle (3), same procedure as stage10/scripts/s10_b3_precheck.py (Stage 10
§11.2): R-c top-50 (Stage 3 R-c queries, k=50, no profile) on the Stage 10 release and staging-4 copies, then blind 2b
grading of the union per task (title = name, summary = 220-char description, stage3/gen/sys-grade.txt, one isolated
`claude -p` per task, seed s11-b3pre-<task>, labels m01...). A task enters the bundle only if no graded skill has
grade >= 2 (either index). The task text is the Stage 3 text verbatim (the repos are built to match its paths), so the
R-c queries are stage3/followup/rc-R-c-380.jsonl. Tasks are given on the command line (first t284 t160 t162; the
remaining Go task t286 only as a replacement).
usage:
  search (skillfetch 3fef3f8):  uvx --from ~/skillfetch-e2e-wt/s10-server/3fef3f8 python s11_b3_precheck.py search <task>...
  grade  (system python):       python3 s11_b3_precheck.py grade <task>... [--run]
outputs (merged per task): stage11-private/b3/precheck-search.json, precheck-grades.jsonl, precheck-labels.json,
precheck.json"""
import json
import random
import re
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
S10 = E2E / "stage10"
OUT = E2E / "stage11-private" / "b3"
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
    random.Random(f"s11-b3pre-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s11-b3pre-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['text']}\n\nCANDIDATES ({len(lab)})\n{body}"))
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
gf = OUT / "precheck-grades.jsonl"
keep = [json.loads(l) for l in gf.open()] if gf.exists() else []
gf.write_text("".join(json.dumps(r) + "\n" for r in [r for r in keep if r["task"] not in TASKS] + rows))
merge("precheck-labels.json", labels)
summ = {t: {"graded": sum(r["task"] == t for r in rows),
            "grade_ge2": sorted((r["skill"], r["grade"]) for r in rows if r["task"] == t and r["grade"] >= 2),
            "enter_bundle": not any(r["task"] == t and r["grade"] >= 2 for r in rows)} for t in TASKS}
res = merge("precheck.json", {"tasks": summ, "problems": {t: [p for p in problems if p["task"] == t] for t in TASKS},
                             "cost_usd": {"+".join(TASKS): round(sum(r.get("cost_usd") or 0 for r in out), 3)}})
print(json.dumps(res, indent=1))
