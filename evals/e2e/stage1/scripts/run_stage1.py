#!/usr/bin/env python3
"""Stage 1: one session = (task, condition, rep) -> worktree, deps, `claude -p`, diff, frozen check, blind screens.

usage: run_stage1.py <task_id> <A|B|C> <rep>
  A  upstream tree (repo-bundled fastapi/sqlmodel skills stay), no skillfetch
  B  same tree as A + the task's expert skills (load_skills output of the pinned ids,
     stage1/expert-content/<id>.md) via --append-system-prompt-file; no skillfetch MCP/router
  C  upstream tree + merged router skill + project .mcp.json (skillfetch); local path: pins allowed
Outputs: stage1/runs/<cond>/<id>-r<rep>.{jsonl,ts,debug.log,stderr,diff,meta.json} + check/ dir.
"""
import fcntl
import json
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S1 = E2E / "stage1"
sys.path.insert(0, str(E2E / "scripts"))
from run_task import ALLOWED_TOOLS, DIFF_EXCLUDES, PG_PORT, PGBIN, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s1"
BRANCH = {"A": "s1-a", "B": "s1-a", "C": "s1-c"}
LOCK = S1 / "runs" / ".screenshot.lock"
BLIND = S1 / "screens-blind"
KEY = S1 / "screens-key.jsonl"


def prepare(task, repo_path, wt, base, run_id):
    if wt.exists():
        sh(["git", "-C", str(repo_path), "worktree", "remove", "--force", str(wt)])
    wt.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "-C", str(repo_path), "worktree", "add", "-q", "--detach", str(wt), base], check=True)
    extra = {}
    if task["repo"] == "fastapi":
        db = "s1_" + run_id.replace("-", "_").lower()
        pg = child_env({"PGPASSWORD": "changethis"})
        for q in (f"DROP DATABASE IF EXISTS {db};", f"CREATE DATABASE {db};"):
            sh([f"{PGBIN}/psql", "-h", "localhost", "-p", str(PG_PORT), "-U", "postgres", "-c", q], env=pg, check=True)
        extra = {"DATABASE_URL": f"postgresql://postgres:changethis@localhost:{PG_PORT}/{db}"}
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
        sh(["uv", "run", "alembic", "upgrade", "head"], cwd=wt / "backend", env=child_env(extra), check=True, timeout=300)
        if task.get("ui"):  # frontend task: a developer would have the frontend deps installed
            sh(["bun", "install", "--frozen-lockfile"], cwd=wt, env=child_env(), check=True, timeout=900)
    else:
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    return extra


def run_session(task, cond, wt, extra, out, max_turns="25", expert_dir=None):
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose",
           "--max-turns", str(max_turns), "--allowedTools", ALLOWED_TOOLS, "--debug-file", str(out) + ".debug.log"]
    if cond == "B":
        cmd += ["--append-system-prompt-file", str((expert_dir or S1 / "expert-content") / f"{task['id']}.md")]
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
    return {"cmd": cmd, "exit_code": rc, "timed_out": timed_out, "spawn_epoch_ms": int(t0 * 1000),
            "wall_s": round(time.time() - t0, 1)}


def collect_diff(wt, base, out):
    sh(["git", "add", "-A", "--", ".", *DIFF_EXCLUDES], cwd=wt)
    numstat = sh(["git", "diff", "--cached", "--numstat", base, "--", ".", *DIFF_EXCLUDES], cwd=wt).stdout
    Path(str(out) + ".diff").write_text(sh(["git", "diff", "--cached", base, "--", ".", *DIFF_EXCLUDES], cwd=wt).stdout)
    sh(["git", "reset", "-q"], cwd=wt)  # leave the index as the session left it for the check
    files = []
    for line in numstat.splitlines():
        a, d, f = line.split("\t", 2)
        files.append({"file": f, "added": int(a) if a != "-" else 0, "deleted": int(d) if d != "-" else 0})
    return {"files": files, "added": sum(x["added"] for x in files), "deleted": sum(x["deleted"] for x in files)}


def strip_env_noise(wt):
    """Remove .omc/ dirs written by the user's global <E2 plugin> hooks (not session work) so
    linters in the frozen checks do not see them. Applied before every check, all conditions."""
    removed = []
    for d in sorted(Path(wt).rglob(".omc")):
        if d.is_dir() and "node_modules" not in d.parts and ".venv" not in d.parts:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(str(d.relative_to(wt)))
    return removed


def run_check(task, wt, base, out, recheck=False):
    noise = strip_env_noise(wt)
    cdir = Path(str(out) + (".recheck" if recheck else ".check"))
    if cdir.exists():
        shutil.rmtree(cdir)
    p = sh(["python3", str(S1 / "checks" / "run_check.py"), task["id"], str(wt), str(cdir),
            "--pg", f"postgresql://postgres:changethis@localhost:{PG_PORT}", "--lock", str(LOCK), "--base", base],
           env=child_env(), timeout=3600)
    (cdir / "run_check.log").parent.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text(p.stdout + p.stderr)
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"run_check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def blind_copy(task, cond, rep, out):
    """UI tasks: copy PNGs (nothing else) to screens-blind/<code>/; mapping goes to screens-key.jsonl."""
    pngs = sorted(Path(str(out) + ".check").glob("**/*.png"))
    if not task.get("ui") or not pngs:
        return None
    code = secrets.token_hex(4)
    dest = BLIND / task["id"] / code
    dest.mkdir(parents=True, exist_ok=True)
    for png in pngs:
        rel = png.relative_to(Path(str(out) + ".check"))
        shutil.copy2(png, dest / "__".join(rel.parts))
    with open(KEY, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps({"code": code, "task": task["id"], "cond": cond, "rep": rep}) + "\n")
    return code


def main():
    task_id, cond, rep = sys.argv[1], sys.argv[2], int(sys.argv[3])
    cfg = yaml.safe_load((S1 / "tasks-stage1.yaml").read_text())
    task = next(t for t in cfg["tasks"] if t["id"] == task_id)
    repo_path = E2E / cfg["repos"][task["repo"]]["path"]
    base = sh(["git", "-C", str(repo_path), "rev-parse", BRANCH[cond]], check=True).stdout.strip()
    run_id = f"{task_id}-{cond}-r{rep}"
    runs = S1 / "runs" / cond
    runs.mkdir(parents=True, exist_ok=True)
    out = runs / f"{task_id}-r{rep}"
    wt = WT_ROOT / run_id
    meta = {"task": task, "cond": cond, "rep": rep, "base_commit": base, "worktree": str(wt),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "index_built_at": json.loads((Path.home() / ".skillfetch/index/manifest.json").read_text())["built_at"]}
    extra = prepare(task, repo_path, wt, base, run_id)
    meta["session"] = run_session(task, cond, wt, extra, out)
    meta["diff"] = collect_diff(wt, base, out)
    meta["check"] = run_check(task, wt, base, out)
    meta["blind_code"] = blind_copy(task, cond, rep, out)
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(run_id, "done", meta["session"]["exit_code"], meta["session"]["wall_s"], "check", meta["check"].get("pass"))


if __name__ == "__main__":
    main()
