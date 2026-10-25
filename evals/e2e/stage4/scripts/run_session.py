#!/usr/bin/env python3
"""Stage 4: one session = (task, env, rep) -> fresh worktree of branch s4, deps (stage 1 prepare),
`claude -p` with --max-turns 16 and --include-hook-events.

usage: run_session.py <task_id> <E1|E2> <tag>
  E1  clean: --setting-sources project --strict-mcp-config --mcp-config stage4/mcp-e1.json
      (skillfetch @a1cbcd5 only; the repo's router skill comes from the project)
  E2  user: the user's global ~/.claude as in stages 1-3 (project .mcp.json, same pin)
Outputs: stage4/runs/<env>/<task>-<tag>.{jsonl,ts,debug.log,stderr,meta.json}
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S4 = E2E / "stage4"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
from run_stage1 import prepare  # noqa: E402
from run_task import ALLOWED_TOOLS, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s4"
MAX_TURNS = "16"
ENV_FLAGS = {
    "E1": ["--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(S4 / "mcp-e1.json")],
    "E2": [],
}


def load_task(task_id):
    path = S4 / "tasks.jsonl"
    if path.is_file():
        for line in path.open():
            t = json.loads(line)
            if t["id"] == task_id:
                return t
    for t in yaml.safe_load((E2E / "stage1" / "tasks-stage1.yaml").read_text())["tasks"]:  # P0 pilot tasks
        if t["id"] == task_id:
            return t
    raise SystemExit(f"unknown task {task_id}")


def main():
    task_id, env_name, tag = sys.argv[1:4]
    task = load_task(task_id)
    repo = E2E / "repos" / task["repo"]
    run_id = f"s4-{env_name}-{task_id}-{tag}"
    wt = WT_ROOT / run_id
    out_dir = S4 / "runs" / env_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{task_id}-{tag}"
    t_prep = time.time()
    extra = prepare(task, repo, wt, "s4", run_id)
    prep_s = round(time.time() - t_prep, 1)
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--max-turns", MAX_TURNS, "--allowedTools", ALLOWED_TOOLS,
           "--debug-file", str(out) + ".debug.log", *ENV_FLAGS[env_name]]
    t0 = time.time()
    timed_out = False
    with open(str(out) + ".jsonl", "w") as fo, open(str(out) + ".stderr", "w") as fe, \
            open(str(out) + ".ts", "w") as ts, open("/dev/null") as fi:
        p = subprocess.Popen(cmd, cwd=wt, env=child_env(extra), stdin=fi, stdout=subprocess.PIPE, stderr=fe)

        def pump():
            for line in p.stdout:
                ts.write(f"{int(time.time() * 1000)}\n")
                fo.write(line.decode("utf-8", "replace"))
        th = threading.Thread(target=pump)
        th.start()
        try:
            rc = p.wait(timeout=SESSION_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            timed_out = True
        th.join()
    meta = {"task": task_id, "env": env_name, "tag": tag, "repo": task["repo"],
            "base": sh(["git", "rev-parse", "s4"], cwd=repo).stdout.strip(), "cmd": cmd,
            "exit_code": rc, "timed_out": timed_out, "prep_s": prep_s,
            "wall_s": round(time.time() - t0, 1), "spawn_epoch_ms": int(t0 * 1000)}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1))
    sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    print(json.dumps({k: meta[k] for k in ("task", "env", "exit_code", "prep_s", "wall_s")}))


if __name__ == "__main__":
    main()
