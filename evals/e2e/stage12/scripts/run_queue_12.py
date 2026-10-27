#!/usr/bin/env python3
"""Run a Stage 12 job list (stage12/DESIGN.md §8, §9) with 4 workers (one "task cond tag" per line). Copied from
stage26/scripts/run_queue_26.py; only the paths, the cap and the per-session estimates differ.

Stops launching new sessions after a usage-limit failure (harness_fail), a session without a result event (no_result),
an index hash or preflight failure (incl. leftover processes), a leftover process after a session, or when the cost
rule says so. Cost (stage12/DESIGN.md §8: cap $75 API-price equivalent for everything in Stage 12): session spend = all
result events under stage12-private/runs; other spend (index-nw extraction, search-check queries) is read from
stage12-private/spend-other.json. Before each launch:
  stop if  other + sessions + 4 in flight x $1.5  >= $75                      (hard stop)
  stop if  other + sessions + remaining jobs x per-session estimate > $75     (projected overrun: "넘을 것 같으면 멈춘다")
Per-session estimate: mean cost of finished Stage 12 sessions of the same condition (>= 3 of them), else the DESIGN §8
estimate (A $0.50, R $0.68, O $0.58). Jobs whose meta.json exists without harness_fail/no_result are skipped, so a list can be
re-run after a stop. usage: run_queue_12.py <jobs.txt> [--dry-run] [--workers N]  (in-flight allowance = N × $1.5)   (--dry-run: counts and projection only)"""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
RUNS = PRIV / "runs"
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4  # added 2026-10-26 (DESIGN §10)
CAP, IN_FLIGHT = 75.0, WORKERS * 1.5
PLAN = {"A": 0.50, "R": 0.68, "O": 0.58}  # DESIGN §8
sys.path.insert(0, str(S12 / "scripts"))
from run_12 import load_tasks  # noqa: E402

TASKS = load_tasks()
jobs = [l.split() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
DRY = "--dry-run" in sys.argv
log = None if DRY else open(sys.argv[1] + ".log", "a")
stop = threading.Event()
lock = threading.Lock()


def other_spend():
    f = PRIV / "spend-other.json"
    return sum(json.loads(f.read_text()).values()) if f.exists() else 0.0


def metas():
    out = []
    for m in RUNS.glob("*/*.meta.json"):
        try:
            out.append(json.loads(m.read_text()))
        except ValueError:
            pass
    return out


def session_spend():
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
    task, cond, tag = j
    m = RUNS / cond / f"{task}-{tag}.meta.json"
    if not m.exists():
        return False
    d = json.loads(m.read_text())
    return not d.get("harness_fail") and not d.get("no_result")


def estimate(task, cond):
    xs = [m["cost_usd"] for m in metas() if m.get("cond") == cond and m.get("cost_usd") and not m.get("harness_fail")]
    return sum(xs) / len(xs) if len(xs) >= 3 else PLAN[cond]


def projection():
    remaining = [j for j in jobs if not done(j)]
    spent = other_spend() + session_spend()
    return {"spent_usd": round(spent, 2), "remaining_jobs": len(remaining),
            "remaining_est_usd": round(sum(estimate(t, c) for t, c, _ in remaining), 2), "cap_usd": CAP}


def one(j):
    if stop.is_set() or done(j):
        return
    with lock:
        pr = projection()
        why = ("cost_hard" if pr["spent_usd"] + IN_FLIGHT >= CAP else
               "cost_projected" if pr["spent_usd"] + pr["remaining_est_usd"] > CAP else None)
        if why:
            log.write(json.dumps({"stop": why, **pr}) + "\n")
            log.flush()
            stop.set()
            return
    p = subprocess.run(["python3", str(S12 / "scripts" / "run_12.py"), *j], capture_output=True, text=True)
    line = (p.stdout.strip().splitlines() or [""])[-1]
    with lock:
        log.write(json.dumps({"job": j, "rc": p.returncode, "out": line, "err": p.stderr[-800:]}) + "\n")
        log.flush()
    try:
        r = json.loads(line)
        if r.get("harness_fail") or r.get("no_result") or not r.get("index_ok_after", True) or r.get("leftover_procs"):
            stop.set()
    except json.JSONDecodeError:
        stop.set()  # preflight / clone / index failure: the runner exited before printing its result line


if DRY:
    from collections import Counter
    print(json.dumps({"jobs": len(jobs), "unique": len({tuple(j) for j in jobs}),
                      "by_cond": dict(sorted(Counter(c for _, c, _ in jobs).items())),
                      "unknown_tasks": sorted({t for t, _, _ in jobs} - set(TASKS)),
                      **projection()}, ensure_ascii=False))
    sys.exit(0)
with ThreadPoolExecutor(WORKERS) as ex:
    list(ex.map(one, jobs))
print("stopped early" if stop.is_set() else "done")
