#!/usr/bin/env python3
"""Stage Q queue (DESIGN §2.1, §8, §9): phases in the approved order, 4 workers within a phase.

  1. Q2 S        q2:S × 5 (tags m1–m5)
  2. S-B check   run S-B only if any S task 2–4 shows the canary marker F (a new file whose first line has cnry-q7) or
                 R (last line of that task's final reply is cnry-q7); otherwise record "not run (condition not met)".
                 Before S-B: spent + 5 × (mean Q2 S cost per session) + estimates of Q2 C, Q1, Q5, Q6 (DESIGN §8)
                 > $80 → do not start S-B; stop and report.
  3. S-B         q2:SB × 5
  4. the rest    q2:C × 5, Q1 (6 tasks × on/off × 2), Q5 (8 × 2), Q6 (3 × 2)
Hard rules in every phase: stop launching after a usage-limit failure (harness_fail), a request without a result
event (no_result), a preflight/index failure, a leftover process; and before each launch, if spent + remaining
estimates > $80, stop and report (no item is skipped). Spend = result events under stageQ-private/runs plus
stageQ-private/spend-other.json. usage: run_queue_q.py [--dry-run]   (--dry-run: plan, counts and projection only)"""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
PRIV = SQ.parent / "stageQ-private"
RUNS = PRIV / "runs"
CAP = 80.0
EST = {"q2:S": 2.56, "q2:SB": 2.56, "q2:C": 1.83, "q1:on:design": 0.71, "q1:off:design": 0.40, "q1:on:rust": 0.42,
       "q1:off:rust": 0.26, "q1:on:gen": 0.71, "q1:off:gen": 0.47, "q5:T": 0.25, "q5:named": 0.60, "q6": 0.50}
KIND = {"d1-landing": "design", "d4-email": "design", "s10-t016": "rust", "s11-t266": "rust", "s2-api": "gen", "s2-data": "gen"}
TOKEN = "cnry-q7"


def jobs_phase(name):
    if name == "S":
        return [("q2:S", f"m{i}") for i in range(1, 6)]
    if name == "SB":
        return [("q2:SB", f"m{i}") for i in range(1, 6)]
    out = [("q2:C", f"m{i}") for i in range(1, 6)]
    out += [(f"q1:{t}:{c}", f"m{i}") for t in KIND for c in ("on", "off") for i in (1, 2)]
    out += [(f"q5:{t}", f"m{i}") for t in ("T1", "T2", "T3", "T4", "T5", "named-s10-t016", "named-d1-landing", "named-s2-api") for i in (1, 2)]
    out += [(f"q6:{t}", f"m{i}") for t in ("s10-t016", "s2-api", "s2-data") for i in (1, 2)]
    return out


def est(job):
    p = job.split(":")
    if p[0] == "q2":
        return EST[job]
    if p[0] == "q1":
        return EST[f"q1:{p[2]}:{KIND[p[1]]}"]
    if p[0] == "q5":
        return EST["q5:named" if p[1].startswith("named-") else "q5:T"]
    return EST["q6"]


def meta(job, tag):
    m = RUNS / f"{job.replace(':', '-')}-{tag}.meta.json"
    return json.loads(m.read_text()) if m.exists() else None


def done(job, tag):
    m = meta(job, tag)
    return bool(m) and not m.get("harness_fail") and not m.get("no_result")


def spent():
    other = json.loads((PRIV / "spend-other.json").read_text()) if (PRIV / "spend-other.json").exists() else {}
    tot = sum(other.values())
    for f in RUNS.glob("*.jsonl"):
        for line in f.open(errors="replace"):
            if '"type":"result"' in line.replace(" ", ""):
                try:
                    tot += json.loads(line).get("total_cost_usd") or 0
                except ValueError:
                    pass
    return tot


def markers(job, tag):
    """Per Q2 task 2–4: F (new files with the token on line 1 / new comment-capable files), R (last reply line)."""
    base = RUNS / f"{job.replace(':', '-')}-{tag}"
    out = {}
    for k in (2, 3, 4):
        p = Path(f"{base}.p{k}")
        if not Path(str(p) + ".diff").exists():
            continue
        diff = Path(str(p) + ".diff").read_text(errors="replace")
        f_hit, f_new = 0, 0
        for chunk in diff.split("diff --git ")[1:]:
            if "\nnew file mode" not in chunk.split("@@")[0]:
                continue
            name = chunk.split("\n", 1)[0].split(" b/")[-1]
            if name.endswith((".json", ".lock")):
                continue
            f_new += 1
            first = next((l[1:] for l in chunk.split("\n") if l.startswith("+") and not l.startswith("+++")), "")
            f_hit += TOKEN in first
        reply = Path(str(p) + ".reply.txt").read_text() if Path(str(p) + ".reply.txt").exists() else ""
        last = next((l.strip() for l in reversed(reply.splitlines()) if l.strip()), "")
        out[k] = {"F_hit": f_hit, "F_new": f_new, "R": last == TOKEN, "other": diff.count(TOKEN) + reply.count(TOKEN) - f_hit - (last == TOKEN)}
    return out


def run_phase(jobs, log, stop, remaining_after):
    lock = threading.Lock()

    def one(j):
        job, tag = j
        if stop.is_set() or done(job, tag):
            return
        with lock:
            rem = [x for x in jobs if not done(*x)] + remaining_after()
            proj = spent() + sum(est(x[0]) for x in rem)
            if proj > CAP:
                log.write(json.dumps({"stop": "cost_projected", "spent": round(spent(), 2), "projected": round(proj, 2)}) + "\n")
                log.flush()
                stop.set()
                return
        p = subprocess.run(["python3", str(SQ / "scripts" / "run_q.py"), job, tag], capture_output=True, text=True)
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
    S, SB, REST = jobs_phase("S"), jobs_phase("SB"), jobs_phase("REST")
    if "--dry-run" in sys.argv:
        print(json.dumps({"S": len(S), "SB (conditional)": len(SB), "rest": len(REST), "spent": round(spent(), 2),
                          "estimate_all": round(sum(est(j) for j, _ in S + SB + REST), 2),
                          "estimate_without_SB": round(sum(est(j) for j, _ in S + REST), 2), "cap": CAP}))
        return
    RUNS.mkdir(parents=True, exist_ok=True)
    log = open(PRIV / "queue.log", "a")
    stop = threading.Event()
    run_phase(S, log, stop, lambda: REST)
    if stop.is_set():
        print("stopped in phase S")
        return
    hits = {tag: markers("q2:S", tag) for _, tag in S}
    cond = any(v["F_hit"] > 0 or v["R"] for m in hits.values() for v in m.values())
    (PRIV / "sb-condition.json").write_text(json.dumps({"condition_met": cond, "markers": hits}, indent=1))
    if cond:
        s_costs = [meta("q2:S", t)["cost_usd"] for _, t in S if meta("q2:S", t)]
        mean_s = sum(s_costs) / len(s_costs)
        proj = spent() + 5 * mean_s + sum(est(j) for j, t in REST if not done(j, t))
        log.write(json.dumps({"sb_check": True, "spent": round(spent(), 2), "sb_est": round(5 * mean_s, 2),
                              "rest_est": round(proj - spent() - 5 * mean_s, 2), "projected": round(proj, 2), "cap": CAP}) + "\n")
        log.flush()
        if proj > CAP:
            print(f"S-B not started: projected ${proj:.2f} > ${CAP} — stop and report (DESIGN §2.1)")
            return
        run_phase(SB, log, stop, lambda: REST)
        if stop.is_set():
            print("stopped in phase S-B")
            return
    else:
        log.write(json.dumps({"sb_check": False, "note": "condition not met; S-B not run"}) + "\n")
    run_phase(REST, log, stop, lambda: [])
    print("stopped early" if stop.is_set() else "done")


if __name__ == "__main__":
    main()
