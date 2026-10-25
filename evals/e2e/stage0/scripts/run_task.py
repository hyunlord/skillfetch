#!/usr/bin/env python3
"""Run one e2e task: isolated worktree -> deps -> one `claude -p` session -> diff + post-tests.

usage: run_task.py <task_id> [<cond>]
Writes <runs>/<id>.jsonl (full stream-json), .stderr, .diff, .meta.json; stage 0.5 conditions also
write <id>.ts (receive time of each stdout line, epoch ms) and <id>.debug.log (claude --debug-file).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WT_ROOT = Path.home() / "skillfetch-e2e-wt"
RUNS = ROOT / "runs"
# stage 0.5 conditions: baseline branch in each test repo + output dir. No cond = stage 0.
CONDS = {
    "R1": {"branch": "e2e-r1", "runs": ROOT / "runs-0.5" / "R1"},
    "R1R2": {"branch": "e2e-r1r2", "runs": ROOT / "runs-0.5" / "R1R2"},
}
PGBIN = "/opt/homebrew/opt/postgresql@16/bin"
PG_PORT = 55432
SESSION_TIMEOUT_S = 45 * 60
ALLOWED_TOOLS = "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*"
# Strip the parent Claude Code session's env so the child looks like a fresh terminal launch.
STRIP_ENV = [
    "CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_PID", "CLAUDE_CODE_ENTRYPOINT",
    "AI_AGENT", "CLAUDE_EFFORT", "CLAUDE_CODE_EXECPATH",
    "VIRTUAL_ENV", "UV", "UV_RUN_RECURSION_DEPTH",
]
# Paths that are environment noise, not the session's work.
DIFF_EXCLUDES = [":(exclude).omc", ":(exclude)**/.omc", ":(exclude)graft", ":(exclude)**/graft/.cache",
                 ":(exclude)**/__pycache__", ":(exclude).venv", ":(exclude)node_modules",
                 ":(exclude)tsconfig.tsbuildinfo", ":(exclude)**/htmlcov", ":(exclude)**/.coverage"]


def sh(cmd, cwd=None, env=None, timeout=None, check=False):
    p = subprocess.run(cmd, cwd=cwd, env=env, shell=isinstance(cmd, str), capture_output=True,
                       text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd} failed ({p.returncode}): {p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p


def child_env(extra=None):
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.update(extra or {})
    return env


def db_name(run_id):
    return "app_" + run_id.replace("-", "_").lower()


def db_url(run_id):
    return f"postgresql://postgres:changethis@localhost:{PG_PORT}/{db_name(run_id)}"


def prepare(task, repo, wt, base, run_id):
    if wt.exists():
        sh(["git", "-C", str(ROOT / repo["path"]), "worktree", "remove", "--force", str(wt)])
    sh(["git", "-C", str(ROOT / repo["path"]), "worktree", "add", "-q", "--detach", str(wt),
        base], check=True)
    extra = {}
    if task["repo"] == "fastapi":
        dbname = db_name(run_id)
        pg = child_env({"PGPASSWORD": "changethis"})
        sh([f"{PGBIN}/psql", "-h", "localhost", "-p", str(PG_PORT), "-U", "postgres", "-c",
            f"DROP DATABASE IF EXISTS {dbname};"], env=pg, check=True)
        sh([f"{PGBIN}/psql", "-h", "localhost", "-p", str(PG_PORT), "-U", "postgres", "-c",
            f"CREATE DATABASE {dbname};"], env=pg, check=True)
        extra = {"DATABASE_URL": db_url(run_id)}
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
        sh(["uv", "run", "alembic", "upgrade", "head"], cwd=wt / "backend", env=child_env(extra),
           check=True, timeout=300)
    else:
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    return extra


def run_session(task, wt, extra, runs, timed):
    out = runs / f"{task['id']}.jsonl"
    err = runs / f"{task['id']}.stderr"
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose",
           "--max-turns", "25", "--allowedTools", ALLOWED_TOOLS]
    if timed:  # instrumentation only: debug log carries the MCP connect timestamps
        cmd += ["--debug-file", str(runs / f"{task['id']}.debug.log")]
    t0 = time.time()
    timed_out = False
    with open(out, "w") as fo, open(err, "w") as fe, open(os.devnull) as fi:
        p = subprocess.Popen(cmd, cwd=wt, env=child_env(extra), stdin=fi,
                             stdout=subprocess.PIPE if timed else fo, stderr=fe)
        if timed:
            import threading
            ts = open(runs / f"{task['id']}.ts", "w")
            def pump():
                for line in p.stdout:
                    ts.write(f"{int(time.time() * 1000)}\n")
                    fo.write(line.decode("utf-8", "replace"))
                fo.flush()
                ts.close()
            th = threading.Thread(target=pump)
            th.start()
        try:
            rc = p.wait(timeout=SESSION_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            timed_out = True
        if timed:
            th.join()
    return {"cmd": cmd, "exit_code": rc, "timed_out": timed_out, "spawn_epoch_ms": int(t0 * 1000),
            "wall_s": round(time.time() - t0, 1)}


def collect_diff(task, wt, base, runs):
    sh(["git", "add", "-A", "--", ".", *DIFF_EXCLUDES], cwd=wt)
    numstat = sh(["git", "diff", "--cached", "--numstat", base, "--", ".", *DIFF_EXCLUDES], cwd=wt).stdout
    patch = sh(["git", "diff", "--cached", base, "--", ".", *DIFF_EXCLUDES], cwd=wt).stdout
    (runs / f"{task['id']}.diff").write_text(patch)
    files, added, deleted = [], 0, 0
    for line in numstat.splitlines():
        a, d, f = line.split("\t", 2)
        a = int(a) if a != "-" else 0
        d = int(d) if d != "-" else 0
        added += a
        deleted += d
        files.append({"file": f, "added": a, "deleted": d})
    return {"files": files, "added": added, "deleted": deleted}


def post_tests(task, wt, extra, runs):
    res = {}
    if task["repo"] == "fastapi":
        junit = runs / f"{task['id']}.junit.xml"
        p = sh(["uv", "run", "pytest", "tests/", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"],
               cwd=wt / "backend", env=child_env({**extra, "FASTAPI_ENV": "development"}), timeout=900)
        res["pytest_rc"] = p.returncode
        res["pytest_tail"] = (p.stdout + p.stderr)[-1500:]
        res["junit"] = str(junit)
    else:
        env = child_env({"CI": "1", "NEXT_TELEMETRY_DISABLED": "1"})
        p = sh(["npm", "run", "type-check"], cwd=wt, env=env, timeout=600)
        res["type_check_rc"] = p.returncode
        res["type_check_tail"] = (p.stdout + p.stderr)[-1500:]
        p = sh(["npx", "next", "build"], cwd=wt, env=env, timeout=900)
        res["build_rc"] = p.returncode
        res["build_tail"] = (p.stdout + p.stderr)[-1500:]
        pkg = json.loads((wt / "package.json").read_text())
        if "test" in pkg.get("scripts", {}):
            p = sh(["npm", "test", "--", *([] if "vitest" not in pkg["scripts"]["test"] else ["--run"])],
                   cwd=wt, env=env, timeout=900)
            res["npm_test_script"] = pkg["scripts"]["test"]
            res["npm_test_rc"] = p.returncode
            res["npm_test_tail"] = (p.stdout + p.stderr)[-2500:]
    return res


def main():
    task_id = sys.argv[1]
    cond = sys.argv[2] if len(sys.argv) > 2 else None
    cfg = yaml.safe_load((ROOT / "tasks.yaml").read_text())
    task = next(t for t in cfg["tasks"] if t["id"] == task_id)
    repo = cfg["repos"][task["repo"]]
    if cond:
        runs = CONDS[cond]["runs"]
        base = sh(["git", "-C", str(ROOT / repo["path"]), "rev-parse", CONDS[cond]["branch"]], check=True).stdout.strip()
        run_id = f"{task_id}-{cond}"
    else:
        runs, base, run_id = RUNS, repo["baseline_commit"], task_id
    wt = WT_ROOT / run_id
    runs.mkdir(parents=True, exist_ok=True)
    meta = {"task": task, "cond": cond, "base_commit": base, "worktree": str(wt),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    extra = prepare(task, repo, wt, base, run_id)
    meta["session"] = run_session(task, wt, extra, runs, timed=bool(cond))
    meta["diff"] = collect_diff(task, wt, base, runs)
    meta["tests"] = post_tests(task, wt, extra, runs)
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (runs / f"{task_id}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(task_id, "done", meta["session"], f"+{meta['diff']['added']}/-{meta['diff']['deleted']}")


if __name__ == "__main__":
    main()
