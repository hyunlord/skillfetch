#!/usr/bin/env python3
"""Run a Stage 11 job list with 4 workers (one "task cond tag" per line).

Stops launching new sessions after a usage-limit failure (harness_fail), a session without a result event (no_result),
an index hash or preflight failure (incl. leftover processes), a leftover process after a session, or when the cost
rule says so. Cost (DESIGN header: cap $115 for everything in Stage 11): session spend = all result events under stage11-private/runs; other spend (pre-run checks, grading) is read
from stage11-private/spend-other.json. Before each launch:
  stop if  other + sessions + 4 in flight x $1.5  >= $115                      (hard stop)
  stop if  other + sessions + remaining jobs x per-session estimate > $115     (projected overrun: "넘을 것 같으면 멈춘다")
Per-session estimate: mean cost of finished Stage 11 sessions of the same bundle and condition (>= 3 of them), else the
Stage 10 mean used in DESIGN §8. Jobs whose meta.json exists without harness_fail/no_result are skipped, so a list can be
re-run after a stop. usage: run_queue_s11.py <jobs.txt> [--dry-run]   (--dry-run: counts and projection only)"""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
PRIV = S11.parent / "stage11-private"
RUNS = PRIV / "runs"
CAP, IN_FLIGHT = 115.0, 4 * 1.5
S10_MEAN = {(1, "R0"): 0.708, (1, "R1"): 0.745, (2, "R0"): 0.708, (2, "R1"): 0.682, (3, "R0"): 0.371, (3, "R1"): 0.344,
            (4, "R0"): 0.383, (4, "R1"): 0.446, (4, "A"): 0.258}
sys.path.insert(0, str(S11 / "scripts"))
from run_s11 import load_tasks  # noqa: E402

BUNDLE = {k: t["bundle"] for k, t in load_tasks().items()}
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
    b = BUNDLE[task]
    xs = [m["cost_usd"] for m in metas() if m.get("bundle") == b and m.get("cond") == cond and m.get("cost_usd")
          and not m.get("harness_fail")]
    return sum(xs) / len(xs) if len(xs) >= 3 else S10_MEAN[(b, cond)]


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
    p = subprocess.run(["python3", str(S11 / "scripts" / "run_s11.py"), *j], capture_output=True, text=True)
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
                      "by_bundle_cond": {f"b{b} {c}": n for (b, c), n in sorted(Counter((BUNDLE[t], c) for t, c, _ in jobs).items())},
                      **projection()}, ensure_ascii=False))
    sys.exit(0)
with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, jobs))
print("stopped early" if stop.is_set() else "done")
