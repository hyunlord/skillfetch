#!/usr/bin/env python3
"""Stage 6b: one session = (task, condition, tag) -> fresh worktree of the condition's branch, dependency install,
`claude -p` in the E1 environment, diff, outcome check.

usage: run_6b.py <task_id> <A|C0|Cb> <tag>        (tags: r1-r3 main run, p0 pilot)
  A   branch s6b-a  (upstream, no router skill, no .mcp.json)          --mcp-config mcp-none.json (no servers)
  C0  branch s6b-c0 (router = skillfetch main 6b50ae6 SKILL.md)        --mcp-config mcp-main.json (local worktree @6b50ae6)
  Cb  branch s6b-cb (router = stage6/select-cands/S-bp/SKILL.md)       --mcp-config mcp-main.json
E1 flags for all: --setting-sources project --strict-mcp-config, --include-hook-events, --max-turns 40, allowed tools
Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*. Checks: bundles 1 and 3 checks/check_6b.py, bundle 2
stage2/checks/check_s2.py (frozen). Outputs: runs/<cond>/<task>-<tag>.{jsonl,ts,debug.log,stderr,diff,meta.json} + .check/
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
E2E = S6B.parents[1]
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
import run_stage1 as rs  # noqa: E402
from run_task import ALLOWED_TOOLS, PG_PORT, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s6b"
MAX_TURNS = "40"
COND = {"A": ("s6b-a", "mcp-none.json"), "C0": ("s6b-c0", "mcp-main.json"), "Cb": ("s6b-cb", "mcp-main.json")}
PG = f"postgresql://postgres:changethis@localhost:{PG_PORT}"
LOCK = S6B / "runs" / "screenshot.lock"


def load_task(task_id):
    for line in (S6B / "tasks.jsonl").open():
        t = json.loads(line)
        if t["id"] == task_id:
            return t
    raise SystemExit(f"unknown task {task_id}")


def prepare(task, repo, wt, base, run_id):
    if task["repo"] in ("fastapi", "nextjs"):
        return rs.prepare(task, repo, wt, base, run_id)  # fastapi: per-session DB + uv sync + alembic (+ bun if ui)
    if wt.exists():
        sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    wt.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt), base], check=True)
    if (wt / "package.json").exists():  # stage-2 prepare
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    else:
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
    return {}


def run_check(task, wt, base, out):
    noise = rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    if task["check"] == "s2":
        cmd = ["python3", str(E2E / "stage2" / "checks" / "check_s2.py"), task["id"], str(wt), str(cdir), "--base", base]
    else:
        cmd = ["python3", str(S6B / "checks" / "check_6b.py"), task["id"], str(wt), str(cdir), "--pg", PG, "--lock", str(LOCK), "--base", base]
    p = sh(cmd, env=child_env(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text(p.stdout + p.stderr)
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def main():
    task_id, cond, tag = sys.argv[1:4]
    branch, mcp = COND[cond]
    task = load_task(task_id)
    repo = E2E / "repos" / task["repo"]
    base = sh(["git", "-C", str(repo), "rev-parse", branch], check=True).stdout.strip()
    run_id = f"s6b-{cond}-{task_id}-{tag}"
    wt = WT_ROOT / run_id
    out_dir = S6B / "runs" / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{task_id}-{tag}"
    t_prep = time.time()
    extra = prepare(task, repo, wt, base, run_id)
    prep_s = round(time.time() - t_prep, 1)
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose", "--include-hook-events",
           "--max-turns", MAX_TURNS, "--allowedTools", ALLOWED_TOOLS, "--debug-file", str(out) + ".debug.log",
           "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(S6B / mcp)]
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
    wall = round(time.time() - t0, 1)
    diff = rs.collect_diff(wt, base, out)
    check = run_check(task, wt, base, out)
    meta = {"task": task_id, "bundle": task["bundle"], "cond": cond, "tag": tag, "repo": task["repo"], "branch": branch,
            "base": base, "mcp_config": mcp, "cmd": cmd, "exit_code": rc, "timed_out": timed_out, "prep_s": prep_s,
            "wall_s": wall, "spawn_epoch_ms": int(t0 * 1000), "diff": diff, "check": check}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    print(json.dumps({"task": task_id, "cond": cond, "tag": tag, "exit_code": rc, "wall_s": wall, "check": check.get("pass")}))


if __name__ == "__main__":
    main()
