#!/usr/bin/env python3
"""Stage 11 job lists (DESIGN §3, §7). One line per session: "task cond tag".
  pilot: new tasks x 1 (tag p1): bundle (3) x {R0, R1}, s11-t266 x {A, R0, R1}; the first line (s11-t118 R1) is the
         one-session smoke test, run alone.
  main:  bundles (1)(2) x {R0, R1} x 3 (m1-m3), (3) x {R0, R1} x 6 (m1-m6), (4) (Stage 10's 4 + s11-t266, DESIGN
         §3.2.2) x {A, R0, R1} x 6 (m1-m6).
Within each repetition tag the order is shuffled (seed "s11-<tag>"), so conditions and tasks interleave in time.
Writes stage11-private/runs/jobs-pilot.txt and jobs-main.txt. usage: make_jobs_s11.py"""
import json
import random
from collections import Counter
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
RUNS = S11.parent / "stage11-private" / "runs"
RUNS.mkdir(parents=True, exist_ok=True)
tasks = [json.loads(l) for l in (S11.parent / "stage10" / "tasks.jsonl").open() if json.loads(l)["bundle"] in (1, 2, 4)]
tasks += [json.loads(l) for l in (S11 / "tasks-b3.jsonl").open()]
tasks += [json.loads(l) for l in (S11 / "tasks-b4add.jsonl").open()]
REPS = {1: 3, 2: 3, 3: 6, 4: 6}
CONDS = {1: ("R0", "R1"), 2: ("R0", "R1"), 3: ("R0", "R1"), 4: ("A", "R0", "R1")}

b3 = [t["id"] for t in tasks if t["bundle"] == 3]
pilot = [("s11-t118", "R1", "p1")] + [(t, c, "p1") for t in b3 for c in ("R0", "R1") if (t, c) != ("s11-t118", "R1")]
pilot += [("s11-t266", c, "p1") for c in ("A", "R0", "R1")]
main = []
for rep in range(1, 7):
    tag = f"m{rep}"
    batch = [(t["id"], c, tag) for t in tasks if rep <= REPS[t["bundle"]] for c in CONDS[t["bundle"]]]
    random.Random(f"s11-{tag}").shuffle(batch)
    main += batch
assert len(set(main)) == len(main) == 174, len(main)
(RUNS / "jobs-pilot.txt").write_text("".join(" ".join(j) + "\n" for j in pilot))
(RUNS / "jobs-main.txt").write_text("".join(" ".join(j) + "\n" for j in main))
bundle = {t["id"]: t["bundle"] for t in tasks}
print(json.dumps({"pilot": len(pilot), "main": len(main),
                  "main_by_bundle_cond": {f"b{b} {c}": n for (b, c), n in sorted(Counter((bundle[t], c) for t, c, _ in main).items())}}))
