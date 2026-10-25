#!/usr/bin/env python3
"""6b main run: 12 tasks x {A, C0, Cb} x r1-r3 = 108 sessions, 4 at a time. Order: (task, rep) blocks in a seeded shuffle,
the three conditions in a seeded order inside each block (runs/_queue.txt). Resumable: a session whose meta.json
exists is skipped."""
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
tasks = [json.loads(l)["id"] for l in (S6B / "tasks.jsonl").open()]
qf = S6B / "runs" / "_queue.txt"
if qf.exists():
    queue = [tuple(l.split()) for l in qf.read_text().splitlines()]
else:
    rng = random.Random("stage6b-queue")
    blocks = [(t, f"r{n}") for t in tasks for n in (1, 2, 3)]
    rng.shuffle(blocks)
    queue = []
    for t, tag in blocks:
        cs = ["A", "C0", "Cb"]
        rng.shuffle(cs)
        queue += [(t, c, tag) for c in cs]
    qf.write_text("".join(" ".join(q) + "\n" for q in queue))
log = S6B / "runs" / "_runner.log"


def one(q):
    task, cond, tag = q
    if (S6B / "runs" / cond / f"{task}-{tag}.meta.json").exists():
        return
    t0 = time.time()
    p = subprocess.run([sys.executable, str(S6B / "scripts" / "run_6b.py"), task, cond, tag], capture_output=True, text=True)
    with open(log, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {task} {cond} {tag} rc={p.returncode} {round(time.time() - t0)}s "
                f"{p.stdout.strip()[-200:]} {p.stderr.strip()[-300:]}\n")


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, queue))
print("done", len(queue))
