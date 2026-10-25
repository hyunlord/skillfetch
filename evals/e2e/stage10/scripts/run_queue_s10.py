#!/usr/bin/env python3
"""Run a list of stage 10 sessions with 4 workers; stop launching new ones after a usage-limit (harness) failure, an
index hash failure, or once the cumulative stage 10 session cost (all result events under stage10-private/runs, pilot
included) reaches COST_STOP (= $300 cap - 4 in-flight x $1.5). Jobs whose meta.json exists without a harness failure are
skipped, so the same job list can be re-run after a stop. usage: run_queue_s10.py <jobs.txt>   (one "task cond env tag"
per line). Log: <jobs>.log"""
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
RUNS = S10.parent / "stage10-private" / "runs"
COST_CAP, COST_STOP = 300.0, 294.0
if os.environ.get("S10_COST_STOP"):  # per-run cap (e.g. DESIGN §11.1 re-measurement: spent before + $18)
    COST_STOP = float(os.environ["S10_COST_STOP"])
jobs = [l.split() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
log = open(sys.argv[1] + ".log", "a")
stop = threading.Event()
lock = threading.Lock()


def spent():
    total = 0.0
    for f in RUNS.glob("**/*.jsonl"):
        for line in f.open(errors="replace"):
            if '"type":"result"' in line.replace(" ", ""):
                try:
                    total += json.loads(line).get("total_cost_usd") or 0
                except ValueError:
                    pass
    return total


def done(j):
    task, cond, env, tag = j
    m = RUNS / env / cond / f"{task}-{tag}.meta.json"
    return m.exists() and not json.loads(m.read_text()).get("harness_fail")


def one(j):
    if stop.is_set() or done(j):
        return
    with lock:
        cost = spent()
        if cost >= COST_STOP:
            log.write(json.dumps({"stop": "cost", "spent_usd": round(cost, 2), "cap": COST_CAP}) + "\n")
            log.flush()
            stop.set()
            return
    p = subprocess.run(["python3", str(S10 / "scripts" / "run_s10.py"), *j], capture_output=True, text=True)
    line = (p.stdout.strip().splitlines() or [""])[-1]
    with lock:
        log.write(json.dumps({"job": j, "rc": p.returncode, "out": line, "err": p.stderr[-800:]}) + "\n")
        log.flush()
    try:
        r = json.loads(line)
        if r.get("harness_fail"):
            stop.set()
    except json.JSONDecodeError:
        if "index hash" in p.stderr + p.stdout:
            stop.set()


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, jobs))
print("stopped early" if stop.is_set() else "done")
