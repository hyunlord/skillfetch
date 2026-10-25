#!/usr/bin/env python3
"""Stage 5: one session = (task, variant, rep) -> fresh worktree of the variant's branch, deps (stage 1 prepare),
`claude -p` in the stage-4 E1 environment (clean): --setting-sources project --strict-mcp-config --mcp-config <file>,
--include-hook-events, --max-turns 16, the stage 1-4 allowed tools.

usage: run_session.py <task_id> <V0|V1|V2|V3> <tag>
  V0  branch s5     (router skill = skillfetch 14d2020 SKILL.md)   server mcp-main.json (local worktree @14d2020)
  V1  branch s5-v1  (router description rewritten)                server mcp-main.json
  V2  branch s5-v2  (s5 + project CLAUDE.md line)                 server mcp-main.json
  V3  branch s5     (same as V0)                                  server mcp-v3.json (14d2020 + INSTRUCTIONS, local)
Outputs: stage5/runs/<variant>/<task>-<tag>.{jsonl,ts,debug.log,stderr,meta.json}
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
S5 = E2E / "stage5"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
from run_stage1 import prepare  # noqa: E402
from run_task import ALLOWED_TOOLS, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s5"
MAX_TURNS = "16"
VARIANTS = {"V0": ("s5", "mcp-main.json"), "V1": ("s5-v1", "mcp-main.json"),
            "V2": ("s5-v2", "mcp-main.json"), "V3": ("s5", "mcp-v3.json")}


def load_task(task_id):
    for line in (S5 / "tasks.jsonl").open():
        t = json.loads(line)
        if t["id"] == task_id:
            return t
    for line in (E2E / "stage4" / "tasks.jsonl").open():  # check sessions may use a stage-4 task
        t = json.loads(line)
        if t["id"] == task_id:
            return t
    raise SystemExit(f"unknown task {task_id}")


def main():
    task_id, variant, tag = sys.argv[1:4]
    branch, mcp = VARIANTS[variant]
    task = load_task(task_id)
    repo = E2E / "repos" / task["repo"]
    run_id = f"s5-{variant}-{task_id}-{tag}"
    wt = WT_ROOT / run_id
    out_dir = S5 / "runs" / variant
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{task_id}-{tag}"
    t_prep = time.time()
    extra = prepare(task, repo, wt, branch, run_id)
    prep_s = round(time.time() - t_prep, 1)
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--max-turns", MAX_TURNS, "--allowedTools", ALLOWED_TOOLS,
           "--debug-file", str(out) + ".debug.log",
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(S5 / mcp)]
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
    meta = {"task": task_id, "variant": variant, "env": "E1", "tag": tag, "repo": task["repo"], "branch": branch,
            "base": sh(["git", "rev-parse", branch], cwd=repo).stdout.strip(), "mcp_config": mcp, "cmd": cmd,
            "exit_code": rc, "timed_out": timed_out, "prep_s": prep_s,
            "wall_s": round(time.time() - t0, 1), "spawn_epoch_ms": int(t0 * 1000)}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1))
    sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    print(json.dumps({k: meta[k] for k in ("task", "variant", "exit_code", "prep_s", "wall_s")}))


if __name__ == "__main__":
    main()
