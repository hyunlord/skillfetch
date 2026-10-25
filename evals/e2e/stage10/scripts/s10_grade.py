#!/usr/bin/env python3
"""Stage 10 load grading (DESIGN §3): every (task, skill) loaded in a stage 10 session gets a grade. Bundle (4) takes the
run-c label (stage9/run-c/oracle-v5-ss-b-s9g.jsonl, same request text) when one exists, and the new bundle (3)
(tasks-b3new.jsonl) takes its §11.2 pre-run grade when one exists; the rest are graded blind in
the v5-ss-b / Stage 9 format: title = name, summary = 220-char description, stage3/gen/sys-grade.txt, one isolated
`claude -p` per task (stage6 batch.run_all), candidates shuffled with seed s10-grade-<task> under labels m01...
The grader sees the request text and the candidate cards only (no condition, no session).
usage: s10_grade.py <sessions.jsonl> [<sessions.jsonl> ...] [--run]
  [--out <name>]  -> stage10-private/<name, default grades-s10>.jsonl {"task", "skill", "grade", "process", "source": "run-c" | "s10-grade"}
     stage10-private/grade-labels-<name>.json, grade-<name>-summary.json (name without the "grades-" prefix)"""
import json
import random
import re
import sys
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
E2E = S10.parent
PRIV = E2E / "stage10-private"
sys.path.insert(0, str(E2E / "stage6" / "scripts"))

files = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--out"]
rows = [json.loads(l) for f in files for l in open(f)]
tasks = {json.loads(l)["id"]: json.loads(l) for f in ("tasks.jsonl", "tasks-b3new.jsonl") for l in (S10 / f).open()}
pre = {}  # DESIGN §11.2 pre-run grades of the new bundle (3) (same text, same 2b format)
if (PRIV / "b3new" / "precheck-grades.jsonl").exists():
    for line in (PRIV / "b3new" / "precheck-grades.jsonl").open():
        g = json.loads(line)
        pre.setdefault(f"s10-{g['task']}", {})[g["skill"]] = {"grade": g["grade"], "process": None}
recs = {}
for idx in ("release", "staging-4"):
    for line in (S10 / "index" / idx / "skills.jsonl").open():
        r = json.loads(line)
        recs[r["id"]] = r
runc = {}
for line in (E2E / "stage9" / "run-c" / "oracle-v5-ss-b-s9g.jsonl").open():
    r = json.loads(line)
    runc[r["id"]] = {x["skill"]: x for x in r["pool"]}
desc220 = lambda s: (lambda x: x if len(x) <= 220 else x[:217] + "...")(re.sub(r"\s+", " ", s or "").strip())  # noqa: E731

loaded = {}
for r in rows:
    for s in r.get("loaded") or []:
        loaded.setdefault(r["task"], set()).add(s)
out, new = [], {}
for t, ss in sorted(loaded.items()):
    lab = runc.get(t.removeprefix("s10-"), {}) if tasks[t]["bundle"] == 4 else pre.get(t, {})
    src = "run-c" if tasks[t]["bundle"] == 4 else "b3new-precheck"
    for s in sorted(ss):
        if s in lab:
            out.append({"task": t, "skill": s, "grade": lab[s]["grade"], "process": lab[s].get("process"), "source": src})
        else:
            new.setdefault(t, []).append(s)
n = sum(len(v) for v in new.values())
print(json.dumps({"from_run_c": len(out), "to_grade": n, "tasks": len(new), "estimate_usd": round(len(new) * 0.011 + n * 0.001, 2)}))
if "--run" not in sys.argv:
    sys.exit(0)
from batch import parse_json_last, run_all  # noqa: E402

labels, jobs = {}, []
for t, c in new.items():
    random.Random(f"s10-grade-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s10-grade-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['prompt']}\n\nCANDIDATES ({len(lab)})\n{body}"))
res = run_all(jobs, workers=8)
problems = []
for (t, lab), r in zip(labels.items(), res):
    assert not r["is_error"], r["name"]
    g = {}
    for x in parse_json_last(r["text"]):
        l = str(x.get("skill", "")).strip()
        if l in lab and l not in g:
            g[l] = {"grade": int(x["grade"]), "process": bool(x.get("process"))}
    if set(g) != set(lab):
        problems.append({"task": t, "missing": sorted(set(lab) - set(g))})
    out += [{"task": t, "skill": lab[l], **v, "source": "s10-grade"} for l, v in g.items()]
outname = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "grades-s10"
(PRIV / f"{outname}.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out))
(PRIV / f"grade-labels-{outname.removeprefix('grades-')}.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0))
summ = {"pairs": len(out), "graded_now": sum(o["source"] == "s10-grade" for o in out), "problems": problems,
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 3)}
(PRIV / f"grade-{outname.removeprefix('grades-')}-summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ))
