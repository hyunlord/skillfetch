#!/usr/bin/env python3
"""Stage 13 queue (stage13/DESIGN.md §2, §4). Phases:
  pilot  p:<d2-redesign|s10-t263|s2-api> p1                                  (run_13.py, stage13-private)
  main   p:<18 tasks> × m1–m3, shuffled per tag with seed "s13-<tag>"         (run_13.py, stage13-private)
         + q1:<6 Q1 tasks>:on|off m3 (A·R third run)                         (stageQ/scripts/run_q.py, stageQ-private)
4 workers. Stops launching after harness_fail / no_result / leftover process / index failure, and before each launch
when spent + remaining estimates > $42 (cap, user approval 2026-10-27). Spent = result events under stage13-private/runs
plus the q1-<Q1 task>-<on|off>-m3 runs under stageQ-private/runs. Estimate per job: P = the task's off mean + $0.05 ($0.90 for the 4 design tasks; set after the pilot);
q1 on/off = the task's mean (est-per-task.json, from Stage Q / Q1x runs). Done jobs are skipped on rerun.
usage: run_queue_13.py pilot|main [--dry-run]"""
import json
import os
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
E2E = S13.parent
PRIV = E2E / "stage13-private"
QPRIV = E2E / "stageQ-private"
CAP = 48.0  # raised from $42 by the user, 2026-10-27, after the first 12 main jobs
EST = json.loads((PRIV / "est-per-task.json").read_text())
TASKS = json.loads((PRIV / "tasks13.json").read_text())["tasks"]
Q1 = ["d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data"]
PILOT = [(f"p:{t}", "p1") for t in ("d2-redesign", "s10-t263", "s2-api")]
MAIN = []
for tag in ("m1", "m2", "m3"):
    b = [(f"p:{t}", tag) for t in TASKS]
    random.Random(f"s13-{tag}").shuffle(b)
    MAIN += b
AR = [(f"q1:{t}:{c}", "m3") for t in Q1 for c in ("on", "off")]
random.Random("s13-ar").shuffle(AR)
MAIN += AR


def out_meta(job, tag):
    root = QPRIV if job.startswith("q1:") else PRIV
    return root / "runs" / f"{job.replace(':', '-')}-{tag}.meta.json"


def est(job):
    if job.startswith("p:"):  # after the pilot (2026-10-27): design tasks off + $0.90 (d2-redesign P $1.30 vs off $0.29),
        t = job.split(":")[1]  # other tasks off + $0.05 (s10-t263 $0.288 vs $0.249, s2-api $0.530 vs $0.476)
        if t == "d1-landing":  # P m1 cost $3.23 (41 turns); 2026-10-27
            return 3.2
        return EST[t]["off"] + (0.90 if t in ("d1-landing", "d2-redesign", "d3-dashboard", "d4-email") else 0.05)
    _, t, c = job.split(":")
    return EST[t][c]


def done(job, tag):
    m = out_meta(job, tag)
    if not m.exists():
        return False
    d = json.loads(m.read_text())
    return not d.get("harness_fail") and not d.get("no_result")


def spent():
    files = list((PRIV / "runs").glob("*.jsonl")) + [f for t in Q1 for c in ("on", "off")
                                                    for f in (QPRIV / "runs").glob(f"q1-{t}-{c}-m3*.jsonl")]
    tot = 0.0
    for f in files:
        for line in f.open(errors="replace"):
            if '"type":"result"' in line.replace(" ", ""):
                try:
                    tot += json.loads(line).get("total_cost_usd") or 0
                except ValueError:
                    pass
    return tot


def run_phase(jobs, later, log, stop):
    lock = threading.Lock()

    def one(j):
        if stop.is_set() or done(*j):
            return
        with lock:
            proj = spent() + sum(est(x[0]) for x in jobs + later if not done(*x))
            if proj > CAP:
                log.write(json.dumps({"stop": "cost_projected", "spent": round(spent(), 2), "projected": round(proj, 2)}) + "\n")
                log.flush()
                stop.set()
                return
        if j[0].startswith("p:"):
            cmd, env = ["python3", str(S13 / "scripts" / "run_13.py"), *j], dict(os.environ)
        else:
            cmd, env = ["python3", str(E2E / "stageQ" / "scripts" / "run_q.py"), *j], {k: v for k, v in os.environ.items() if k != "SQ_PRIV"}
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        line = (p.stdout.strip().splitlines() or [""])[-1]
        with lock:
            log.write(json.dumps({"job": j, "rc": p.returncode, "out": line, "err": p.stderr[-600:]}) + "\n")
            log.flush()
        try:
            r = json.loads(line)
            if r.get("harness_fail") or r.get("no_result") or r.get("leftover_procs") or not r.get("index_ok_after", True):
                stop.set()
        except json.JSONDecodeError:
            stop.set()

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, jobs))


def main():
    phase = sys.argv[1]
    jobs, later = (PILOT, MAIN) if phase == "pilot" else (MAIN, [])
    if "--dry-run" in sys.argv:
        print(json.dumps({"phase": phase, "jobs": len(jobs), "remaining": sum(not done(*j) for j in jobs),
                          "spent": round(spent(), 2), "estimate_remaining": round(sum(est(j) for j, t in jobs + later if not done(j, t)), 2),
                          "cap": CAP}))
        return
    (PRIV / "runs").mkdir(parents=True, exist_ok=True)
    log = open(PRIV / f"queue-{phase}.log", "a")
    stop = threading.Event()
    run_phase(jobs, later, log, stop)
    print("stopped early" if stop.is_set() else "done")


if __name__ == "__main__":
    main()
