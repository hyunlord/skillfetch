#!/usr/bin/env python3
"""Pre-release check for V1: the 10 trivial stage-4 tasks x reps 1-3 x {V0, V1} = 60 sessions (E1, same harness:
scripts/run_session.py, 16 turns, 14d2020, isolated). Tags t1-t3 (the main run uses r1-r3), so outputs are
runs/V{0,1}/<task>-t<n>.* and stay out of sessions.jsonl. Blocks of (task, rep) in a seeded shuffle, the two variants
adjacent; 4 at a time; resumable (runs/_queue-trivial.txt, runs/_runner-trivial.log)."""
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
tasks = [json.loads(l)["id"] for l in (S5.parent / "stage4" / "tasks.jsonl").open() if json.loads(l)["task_type"] == "trivial"]
assert len(tasks) == 10
qf = S5 / "runs" / "_queue-trivial.txt"
if qf.exists():
    queue = [tuple(l.split()) for l in qf.read_text().splitlines()]
else:
    rng = random.Random("stage5-trivial")
    blocks = [(t, f"t{n}") for t in tasks for n in (1, 2, 3)]
    rng.shuffle(blocks)
    queue = []
    for t, tag in blocks:
        vs = ["V0", "V1"]
        rng.shuffle(vs)
        queue += [(t, v, tag) for v in vs]
    qf.write_text("".join(" ".join(q) + "\n" for q in queue))
log = S5 / "runs" / "_runner-trivial.log"


def one(q):
    task, variant, tag = q
    if (S5 / "runs" / variant / f"{task}-{tag}.meta.json").exists():
        return
    t0 = time.time()
    p = subprocess.run([sys.executable, str(S5 / "scripts" / "run_session.py"), task, variant, tag], capture_output=True, text=True)
    with open(log, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {task} {variant} {tag} rc={p.returncode} {round(time.time() - t0)}s "
                f"{p.stdout.strip()[-200:]} {p.stderr.strip()[-300:]}\n")


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, queue))
print("done", len(queue))
