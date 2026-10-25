#!/usr/bin/env python3
"""Main run: 19 tasks x V0-V3 x reps 1-3 = 228 sessions (E1), 4 at a time. Order: blocks of (task, rep) in a seeded
shuffle; inside a block the 4 variants in a seeded shuffle, so one task's 4 variants run at about the same time
(runs/_queue.txt). Resumable: a session whose meta.json exists is skipped."""
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S5 = Path(__file__).resolve().parents[1]
tasks = [json.loads(l)["id"] for l in (S5 / "tasks.jsonl").open()]
queue_file = S5 / "runs" / "_queue.txt"
if queue_file.exists():
    queue = [tuple(l.split()) for l in queue_file.read_text().splitlines()]
else:
    rng = random.Random("stage5-queue")
    blocks = [(t, f"r{n}") for t in tasks for n in (1, 2, 3)]
    rng.shuffle(blocks)
    queue = []
    for t, tag in blocks:
        vs = ["V0", "V1", "V2", "V3"]
        rng.shuffle(vs)
        queue += [(t, v, tag) for v in vs]
    queue_file.write_text("".join(" ".join(q) + "\n" for q in queue))
log = S5 / "runs" / "_runner.log"


def one(q):
    task, variant, tag = q
    if (S5 / "runs" / variant / f"{task}-{tag}.meta.json").exists():
        return
    t0 = time.time()
    p = subprocess.run([sys.executable, str(S5 / "scripts" / "run_session.py"), task, variant, tag],
                       capture_output=True, text=True)
    with open(log, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {task} {variant} {tag} rc={p.returncode} {round(time.time() - t0)}s "
                f"{p.stdout.strip()[-200:]} {p.stderr.strip()[-300:]}\n")


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, queue))
print("done", len(queue))
