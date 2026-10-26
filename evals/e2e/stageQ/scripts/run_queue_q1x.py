#!/usr/bin/env python3
"""Q1 extension queue (stageQ/DESIGN-Q1x.md): pilot (s10-t033, s6b-t179 × on/off × p1) → main (12 tasks × on/off × m1–m3 + the 2 local-skill
tasks lq:* on × m1–m3, shuffled per tag with seed "q1x-<tag>", 4 workers). Runs stageQ/scripts/run_q.py q1 jobs with
SQ_PRIV=stageQ1x-private. Stops launching after harness_fail / no_result / leftover process / index failure, and before
each launch when spent + remaining estimates > $45 (spent = result events under stageQ1x-private/runs; estimate per job
= the task's Stage 10/11 E1 mean, DESIGN-Q1x §4). Done jobs are skipped on rerun. usage: run_queue_q1x.py [--dry-run]"""
import json
import os
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = E2E / "stageQ1x-private"
RUNS = PRIV / "runs"
CAP = 45.0
EST = {"d2-redesign": (0.647, 0.301), "d3-dashboard": (0.761, 0.678), "s10-t263": (0.406, 0.22), "s10-t115": (0.557, 0.369),
       "s10-t198": (0.555, 0.344), "s11-t160": (0.351, 0.21), "s11-t118": (0.382, 0.23), "s2-docs": (0.508, 0.393),
       "s10-t033": (0.288, 0.17), "s2-tests": (0.834, 0.657), "s10-t001": (0.403, 0.24), "s6b-t179": (0.527, 0.399)}
ENV = dict(os.environ, SQ_PRIV=str(PRIV))
PILOT = [(f"q1:{t}:{c}", "p1") for t in ("s10-t033", "s6b-t179") for c in ("on", "off")]
LQ = {"s2-api": 1.2, "s10-t016": 1.0}  # local-skill case (DESIGN-Q1x §2.1): on only, 2 requests in one session
MAIN = []
for tag in ("m1", "m2", "m3"):
    b = [(f"q1:{t}:{c}", tag) for t in EST for c in ("on", "off")] + [(f"lq:{t}", tag) for t in LQ]
    random.Random(f"q1x-{tag}").shuffle(b)
    MAIN += b


def est(job):
    if job.startswith("lq:"):
        return LQ[job.split(":")[1]]
    _, t, c = job.split(":")
    return EST[t][0 if c == "on" else 1]


def done(job, tag):
    m = RUNS / f"{job.replace(':', '-')}-{tag}.meta.json"
    if not m.exists():
        return False
    d = json.loads(m.read_text())
    return not d.get("harness_fail") and not d.get("no_result")


def spent():
    tot = 0.0
    for f in RUNS.glob("*.jsonl"):
        for line in f.open(errors="replace"):
            if '"type":"result"' in line.replace(" ", ""):
                try:
                    tot += json.loads(line).get("total_cost_usd") or 0
                except ValueError:
                    pass
    return tot


def run_phase(jobs, log, stop, later):
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
        p = subprocess.run(["python3", str(SQ / "scripts" / "run_q.py"), *j], capture_output=True, text=True, env=ENV)
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
    if "--dry-run" in sys.argv:
        print(json.dumps({"pilot": len(PILOT), "main": len(MAIN), "spent": round(spent(), 2),
                          "estimate": round(sum(est(j) for j, _ in PILOT + MAIN), 2), "cap": CAP}))
        return
    RUNS.mkdir(parents=True, exist_ok=True)
    log = open(PRIV / "queue.log", "a")
    stop = threading.Event()
    for name, jobs, later in (("pilot", PILOT, MAIN), ("main", MAIN, [])):
        run_phase(jobs, log, stop, later)
        if stop.is_set():
            print(f"stopped in {name}")
            return
    print("done")


if __name__ == "__main__":
    main()
