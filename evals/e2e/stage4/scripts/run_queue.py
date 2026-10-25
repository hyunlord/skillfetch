#!/usr/bin/env python3
"""Main run: 40 tasks x E1/E2 x reps 1-3 = 240 sessions, 4 at a time, in a seeded order (runs/_queue.txt).
Resumable: a session whose meta.json exists is skipped. Each session is scripts/run_session.py <task> <env> r<n>."""
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S4 = Path(__file__).resolve().parents[1]
tasks = [json.loads(l)["id"] for l in (S4 / "tasks.jsonl").open()]
queue_file = S4 / "runs" / "_queue.txt"
if queue_file.exists():
    queue = [tuple(l.split()) for l in queue_file.read_text().splitlines()]
else:
    queue = [(t, e, f"r{n}") for t in tasks for e in ("E1", "E2") for n in (1, 2, 3)]
    random.Random("stage4-queue").shuffle(queue)
    queue_file.write_text("".join(" ".join(q) + "\n" for q in queue))
log = S4 / "runs" / "_runner.log"


def one(q):
    task, env, tag = q
    if (S4 / "runs" / env / f"{task}-{tag}.meta.json").exists():
        return
    t0 = time.time()
    p = subprocess.run([sys.executable, str(S4 / "scripts" / "run_session.py"), task, env, tag],
                       capture_output=True, text=True)
    with open(log, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {task} {env} {tag} rc={p.returncode} {round(time.time() - t0)}s "
                f"{p.stdout.strip()[-200:]} {p.stderr.strip()[-300:]}\n")


with ThreadPoolExecutor(4) as ex:
    list(ex.map(one, queue))
print("done", len(queue))
