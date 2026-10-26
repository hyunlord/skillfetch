#!/usr/bin/env python3
"""Stage 11 load grading (DESIGN §5), same procedure as stage10/scripts/s10_grade.py: every (task, skill) loaded in a
Stage 11 session gets a grade. Bundle (4) (s10-t016, s10-t263, s10-t115, s10-t198, s11-t266) takes the run-c label
(stage9/run-c/oracle-v5-ss-b-s9g.jsonl, same request text) when one exists; bundle (3) (s11-t160, s11-t162, s11-t118)
takes its pre-run 2b grade (stage11-private/b3/precheck-grades.jsonl, §3.1.1/3.1.3) when one exists; the rest are graded blind in
the v5-ss-b / Stage 9 format: title = name, summary = 220-char description, stage3/gen/sys-grade.txt, one isolated
`claude -p` per task (stage6 batch.run_all), candidates shuffled with seed s11-grade-<task> under labels m01...
The grader sees the request text and the candidate cards only (no condition, no session).
usage: s10_grade.py <sessions.jsonl> [<sessions.jsonl> ...] [--run]
  [--out <name>]  -> stage11-private/<name, default grades-s11>.jsonl {"task", "skill", "grade", "process", "source": "run-c" | "b3-precheck" | "s11-grade"}
     stage11-private/grade-labels-<name>.json, grade-<name>-summary.json (name without the "grades-" prefix)"""
import json
import random
import re
import sys
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
E2E = S11.parent
S10 = E2E / "stage10"
PRIV = E2E / "stage11-private"
sys.path.insert(0, str(E2E / "stage6" / "scripts"))
sys.path.insert(0, str(S11 / "scripts"))
from run_s11 import load_tasks  # noqa: E402

files = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--out"]
rows = [json.loads(l) for f in files for l in open(f)]
tasks = load_tasks()
pre = {}  # DESIGN §3.1.1/3.1.3 pre-run grades of bundle (3) (same text, same 2b format)
for line in (PRIV / "b3" / "precheck-grades.jsonl").open():
    g = json.loads(line)
    pre.setdefault(f"s11-{g['task']}", {})[g["skill"]] = {"grade": g["grade"], "process": None}
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
    src_id = t.split("-", 1)[1]  # s10-t016 / s11-t266 -> t016 / t266
    lab = runc.get(src_id, {}) if tasks[t]["bundle"] == 4 else pre.get(t, {})
    src = "run-c" if tasks[t]["bundle"] == 4 else "b3-precheck"
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
    random.Random(f"s11-grade-{t}").shuffle(c)
    lab = {f"m{i + 1:02d}": k for i, k in enumerate(c)}
    labels[t] = lab
    body = "\n".join(f"- id: {l}\n  title: {recs[k]['name']}\n  summary: {desc220(recs[k].get('description'))}" for l, k in lab.items())
    jobs.append((f"s11-grade-{t}", E2E / "stage3" / "gen" / "sys-grade.txt", f"TASK\n{tasks[t]['prompt']}\n\nCANDIDATES ({len(lab)})\n{body}"))
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
    out += [{"task": t, "skill": lab[l], **v, "source": "s11-grade"} for l, v in g.items()]
outname = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "grades-s11"
(PRIV / f"{outname}.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out))
(PRIV / f"grade-labels-{outname.removeprefix('grades-')}.json").write_text(json.dumps(labels, ensure_ascii=False, indent=0))
summ = {"pairs": len(out), "graded_now": sum(o["source"] == "s11-grade" for o in out), "problems": problems,
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in res), 3)}
(PRIV / f"grade-{outname.removeprefix('grades-')}-summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ))
