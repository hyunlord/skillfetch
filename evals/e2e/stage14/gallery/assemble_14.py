#!/usr/bin/env python3
"""Stage 14 gallery data (no model calls). From stage14-private/metrics-14.json (rows = the 36 main requests with scores,
reasons, skills, traces, costs) plus, per request: screenshots (landing), the request's diff, automatic diff metrics
(stageQ/gallery/autometrics.py) and the final text of the task's core file after the request. Final texts are rebuilt by
replaying each session's request diffs in order on a clone of s14-a (binary file chunks skipped). Core file per task =
the most-changed non-test, non-lock, non-README file inside the task's area over its six outputs (docs: README.md).
Also the trace (c) items (stage14-private/trace-14.json) and the pilot rows (usage-14-p.json, for the session strip only).
Writes stage14-private/gallery-data-14.json.
usage: assemble_14.py"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
PRIV = E2E / "stage14-private"
sys.path.insert(0, str(E2E / "stageQ" / "gallery"))
from autometrics import metrics, split  # noqa: E402

REPO = E2E / "repos" / "s14-mono"
AREA = {"landing": "web/", "api": "api/", "apitests": "api/", "rust": "media/", "docs": "", "data": "data/"}
SKIP = re.compile(r"(^|/)(tests?|__tests__)/|_test\.|\.test\.|(^|/)test_|(^|/)README|\.(lock|svg|png|jpe?g|mp4|webm|ico|csv|json)$|"
                  r"(^|/)(Cargo\.lock|package-lock\.json|uv\.lock)$|(^|/)\.")


def text_only(diff):
    return "".join(ch for ch in re.split(r"(?=^diff --git )", diff, flags=re.M)
                   if ch.startswith("diff --git") and "\nBinary files " not in ch and "GIT binary patch" not in ch)


def core_file(task, outs):
    if task == "docs":
        return "README.md"
    tot = {}
    for o in outs:
        for f, ch in split(o["diff"]).items():
            if not f.startswith(AREA[task]) or SKIP.search(f[len(AREA[task]):]):
                continue
            tot[f] = tot.get(f, 0) + sum(1 for l in ch.split("\n") if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    if task == "apitests":  # the request is about tests: most-changed test file
        tot = {}
        for o in outs:
            for f, ch in split(o["diff"]).items():
                if f.startswith("api/") and re.search(r"(^|/)tests?/|test_", f):
                    tot[f] = tot.get(f, 0) + sum(1 for l in ch.split("\n") if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    return max(tot, key=tot.get) if tot else None


def main():
    m = json.loads((PRIV / "metrics-14.json").read_text())
    rows = m["rows"]
    for r in rows:
        base = PRIV / "runs" / f"{r['session']}.p{r['k']}"
        r["diff"] = Path(str(base) + ".diff").read_text(errors="replace")
        r["diff_path"] = str(base) + ".diff"
        r["auto"] = metrics(r["diff"])
        cdir = Path(str(base) + ".check")
        r["shots"] = {sub: [str(p) for p in sorted((cdir / sub).glob("*.png"))] for sub in ("screens", "screens-375") if (cdir / sub).exists()}
    cores = {t: core_file(t, [r for r in rows if r["task"] == t]) for t in AREA}
    tmp = Path(tempfile.mkdtemp(prefix="s14g-"))
    try:
        for sess in sorted({r["session"] for r in rows}):
            wt = tmp / sess
            subprocess.run(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", "s14-a", str(REPO), str(wt)], check=True)
            for r in sorted((x for x in rows if x["session"] == sess), key=lambda x: x["k"]):
                body = text_only(r["diff"])
                ok = not body  # an empty diff (no change) needs no replay
                # the harness stored diffs with str.strip(): a final blank context line (" ") may be missing; retry with it
                for extra in ("", " \n"):
                    if ok:
                        break
                    p = subprocess.run(["git", "-C", str(wt), "apply", "--whitespace=nowarn", "-"], input=body + extra,
                                       capture_output=True, text=True)
                    ok = p.returncode == 0
                r["replay_ok"] = ok
                cf = cores[r["task"]]
                r["core_file"] = cf
                r["core_text"] = (wt / cf).read_text(errors="replace") if cf and (wt / cf).exists() else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    trace = json.loads((PRIV / "trace-14.json").read_text()) if (PRIV / "trace-14.json").exists() else {"items": []}
    pilot = json.loads((PRIV / "usage-14-p.json").read_text()) if (PRIV / "usage-14-p.json").exists() else []
    out = {"summary": {k: m[k] for k in ("D", "judge_gap", "criteria", "cost_session_mean", "efficiency", "per_order", "per_judge", "per_condition")},
           "cores": cores, "rows": rows, "trace_c": trace["items"], "pilot": pilot}
    (PRIV / "gallery-data-14.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({"rows": len(rows), "replay_failures": [(r["session"], r["k"]) for r in rows if not r["replay_ok"]], "cores": cores}))


if __name__ == "__main__":
    main()
