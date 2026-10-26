#!/usr/bin/env python3
"""Re-fire check queue (stageRF/DESIGN.md §2–§4): pilot (rf:a, rf:b × p1) → main (rf:cur/a/b × m1–m5, shuffled with
seed "rf", 4 workers) → verdict (metrics_rf.py) → if a winner: rfc:<winner> × m1–m5 (canary).
Stops launching after harness_fail / no_result / leftover process / index failure, and before each launch when
spent + remaining estimates > $50 (spent = result events under stageRF-private/runs). Done jobs are skipped on rerun.
usage: run_queue_rf.py [--dry-run]"""
import json
import os
import random
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RF = Path(__file__).resolve().parents[1]
E2E = RF.parent
PRIV = E2E / "stageRF-private"
RUNS = PRIV / "runs"
CAP, EST = 50.0, 1.8
ENV = dict(os.environ, SQ_PRIV=str(PRIV))


def meta(job, tag):
    m = RUNS / f"{job.replace(':', '-')}-{tag}.meta.json"
    return json.loads(m.read_text()) if m.exists() else None


def done(job, tag):
    m = meta(job, tag)
    return bool(m) and not m.get("harness_fail") and not m.get("no_result")


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


def est():
    xs = [m["cost_usd"] for m in (json.loads(p.read_text()) for p in RUNS.glob("*.meta.json")) if m.get("cost_usd")]
    return sum(xs) / len(xs) if len(xs) >= 3 else EST


PILOT = [("rf:a", "p1"), ("rf:b", "p1")]
MAIN = [(f"rf:{a}", f"m{i}") for a in ("cur", "a", "b") for i in range(1, 6)]
random.Random("rf").shuffle(MAIN)


def run_phase(jobs, log, stop, later):
    lock = threading.Lock()

    def one(j):
        if stop.is_set() or done(*j):
            return
        with lock:
            proj = spent() + est() * (sum(not done(*x) for x in jobs) + later)
            if proj > CAP:
                log.write(json.dumps({"stop": "cost_projected", "spent": round(spent(), 2), "projected": round(proj, 2)}) + "\n")
                log.flush()
                stop.set()
                return
        p = subprocess.run(["python3", str(E2E / "stageQ" / "scripts" / "run_q.py"), *j], capture_output=True, text=True, env=ENV)
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
        print(json.dumps({"pilot": len(PILOT), "main": len(MAIN), "rerun": 5, "spent": round(spent(), 2),
                          "estimate": round(EST * (len(PILOT) + len(MAIN) + 5), 2), "cap": CAP, "order": MAIN}))
        return
    RUNS.mkdir(parents=True, exist_ok=True)
    log = open(PRIV / "queue.log", "a")
    stop = threading.Event()
    for name, jobs, later in (("pilot", PILOT, len(MAIN) + 5), ("main", MAIN, 5)):
        run_phase(jobs, log, stop, later)
        if stop.is_set():
            print(f"stopped in {name}")
            return
    tags = [t for t in (f"m{i}" for i in range(1, 6))]
    subprocess.run(["python3", str(E2E / "stageQ" / "scripts" / "extract_q.py"), *tags, "p1"], env=ENV, check=True)
    v = subprocess.run(["python3", str(RF / "scripts" / "metrics_rf.py"), str(PRIV / f"requests-{'-'.join(sorted(tags + ['p1']))}.jsonl")],
                       capture_output=True, text=True, check=True)
    log.write(json.dumps({"verdict": v.stdout.strip().splitlines()[-1]}) + "\n")
    log.flush()
    w = json.loads(v.stdout.strip().splitlines()[-1])["winner"]
    if not w:
        print("no winner; canary rerun not run")
        return
    run_phase([(f"rfc:{w}", t) for t in tags], log, stop, 0)
    print("stopped early in rerun" if stop.is_set() else f"done (winner {w})")


if __name__ == "__main__":
    main()
