#!/usr/bin/env python3
"""Stage 14 queue (stage14/DESIGN.md §3, §6, §9 approval 2026-10-27: 2 runs, cap $140). Phases:
  pilot  s14:A:F, s14:P:B, s14:R:F  tag p1 (not in the main tallies)
  main   s14:<A|P|R>:<F|B> × m1 (6 sessions; was m1, m2 — cut to 1 run by the user after the pilot), shuffled per tag with seed "s14-<tag>"
Workers: 3. Stops launching after harness_fail / no_result / leftover process / index failure, and before each launch
when spent + remaining estimates > $140 (all phases, pilot included). Spent = result events under stage14-private/runs.
Estimates per session (DESIGN §6): A $5.0, P:F $11.0, P:B $9.5, R $9.0 (updated after the pilot, recorded in DESIGN §9).
Done sessions (meta present, no harness_fail / no_result) are skipped on rerun.
usage: run_queue_14.py pilot|main [--dry-run]"""
import json
import os
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
PRIV = E2E / "stage14-private"
CAP = 140.0
EST_FILE = PRIV / "est-session.json"
EST = json.loads(EST_FILE.read_text()) if EST_FILE.exists() else {"A:F": 9.3, "A:B": 9.3, "P:F": 16.0, "P:B": 14.8, "R:F": 18.9, "R:B": 18.9}
PILOT = [("s14:A:F", "p1"), ("s14:P:B", "p1"), ("s14:R:F", "p1")]
MAIN = []
for tag in ("m1",):  # 1 run (user, 2026-10-27, after the pilot cost 2x the estimate)
    b = [(f"s14:{c}:{o}", tag) for c in "APR" for o in "FB"]
    random.Random(f"s14-{tag}").shuffle(b)
    MAIN += b


def meta(job, tag):
    return PRIV / "runs" / f"{job.split(':', 1)[1].replace(':', '-')}-{tag}.meta.json"


def est(job):
    return EST[job.split(":", 1)[1]]


def done(job, tag):
    m = meta(job, tag)
    if not m.exists():
        return False
    d = json.loads(m.read_text())
    return not d.get("harness_fail") and not d.get("no_result")


def spent():
    tot = 0.0
    for f in (PRIV / "runs").glob("*.jsonl"):
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
                log.write(json.dumps({"stop": "cost_projected", "spent": round(spent(), 2), "projected": round(proj, 2), "next": j}) + "\n")
                log.flush()
                stop.set()
                return
        p = subprocess.run(["python3", str(S14 / "scripts" / "run_14.py"), *j], capture_output=True, text=True, env=dict(os.environ))
        line = (p.stdout.strip().splitlines() or [""])[-1]
        with lock:
            log.write(json.dumps({"job": j, "rc": p.returncode, "out": line, "err": p.stderr[-800:]}) + "\n")
            log.flush()
        try:
            r = json.loads(line)
            if r.get("harness_fail") or r.get("no_result") or r.get("leftover_procs") or not r.get("index_ok_after", True):
                stop.set()
        except json.JSONDecodeError:
            stop.set()

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, jobs))


def main():
    phase = sys.argv[1]
    jobs, later = (PILOT, MAIN) if phase == "pilot" else (MAIN, [])
    if "--dry-run" in sys.argv:
        print(json.dumps({"phase": phase, "jobs": len(jobs), "remaining": sum(not done(*j) for j in jobs), "spent": round(spent(), 2),
                          "estimate_remaining": round(sum(est(j) for j, t in jobs + later if not done(j, t)), 2), "cap": CAP}))
        return
    (PRIV / "runs").mkdir(parents=True, exist_ok=True)
    log = open(PRIV / f"queue-{phase}.log", "a")
    stop = threading.Event()
    run_phase(jobs, later, log, stop)
    print("stopped early" if stop.is_set() else "done")


if __name__ == "__main__":
    main()
