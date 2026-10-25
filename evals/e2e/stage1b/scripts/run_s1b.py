#!/usr/bin/env python3
"""Stage 1b: one session = (task, condition, rep). Same harness as stage 1 (stage1/scripts/run_stage1.py) with
--max-turns 40, stage1b tasks/checks, and blind PNG copies (desktop + 375px) for UI tasks.

usage: run_s1b.py <task_id> <A|B|C|C2> <rep>
C2 (rerun): C with the router skill and server from skillfetch main@e2a1b65 (search_skills k=50, compact results),
branch s1b-c2; no blind copy here (a fresh blind set over A/B/C/C2 is built afterwards).
Outputs: stage1b/runs/<cond>/<id>-r<rep>.{jsonl,ts,debug.log,stderr,diff,meta.json} + .check/ dir.
"""
import fcntl
import json
import secrets
import shutil
import sys
import time
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S1B = E2E / "stage1b"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
import run_stage1 as rs  # noqa: E402
from run_task import PG_PORT, child_env, sh  # noqa: E402

MAX_TURNS = "40"
rs.WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s1b"
rs.BRANCH["C2"] = "s1b-c2"
LOCK = S1B / "runs" / ".screenshot.lock"
BLIND = S1B / "screens-blind"
KEY = S1B / "screens-key.jsonl"


def run_session(task, cond, wt, extra, out):
    return rs.run_session(task, cond, wt, extra, out, max_turns=MAX_TURNS, expert_dir=S1B / "expert-content")


def run_check(task, wt, base, out):
    noise = rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    if cdir.exists():
        shutil.rmtree(cdir)
    p = sh(["python3", str(S1B / "checks" / "run_check_1b.py"), task["id"], str(wt), str(cdir),
            "--pg", f"postgresql://postgres:changethis@localhost:{PG_PORT}", "--lock", str(LOCK), "--base", base],
           env=child_env(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text(p.stdout + p.stderr)
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"run_check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def blind_copy(task, cond, rep, out):
    pngs = sorted(Path(str(out) + ".check").glob("screens*/*.png"))
    if cond == "C2" or not task.get("ui") or not pngs:
        return None
    code = secrets.token_hex(4)
    dest = BLIND / task["id"] / code
    dest.mkdir(parents=True, exist_ok=True)
    for png in pngs:
        shutil.copyfile(png, dest / f"{png.parent.name}__{png.name}")  # copyfile: no source mtime
    with open(KEY, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps({"code": code, "task": task["id"], "cond": cond, "rep": rep}) + "\n")
    return code


def main():
    task_id, cond, rep = sys.argv[1], sys.argv[2], int(sys.argv[3])
    task = next(t for t in yaml.safe_load((S1B / "tasks-1b.yaml").read_text())["tasks"] if t["id"] == task_id)
    repo_path = E2E / "repos" / task["repo"]
    base = sh(["git", "-C", str(repo_path), "rev-parse", rs.BRANCH[cond]], check=True).stdout.strip()
    run_id = f"{task_id}-{cond}-r{rep}"
    runs = S1B / "runs" / cond
    runs.mkdir(parents=True, exist_ok=True)
    out = runs / f"{task_id}-r{rep}"
    wt = rs.WT_ROOT / run_id
    meta = {"task": task, "cond": cond, "rep": rep, "base_commit": base, "worktree": str(wt), "max_turns": int(MAX_TURNS),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "index_built_at": json.loads((Path.home() / ".skillfetch/index/manifest.json").read_text())["built_at"]}
    t2 = dict(task, ui=task.get("ui") or task.get("frontend"))  # bun install for frontend tasks too
    extra = rs.prepare(t2, repo_path, wt, base, run_id)
    meta["session"] = run_session(task, cond, wt, extra, out)
    meta["diff"] = rs.collect_diff(wt, base, out)
    meta["check"] = run_check(task, wt, base, out)
    meta["blind_code"] = blind_copy(task, cond, rep, out)
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(run_id, "done", meta["session"]["exit_code"], meta["session"]["wall_s"], "check", meta["check"].get("pass"))


if __name__ == "__main__":
    main()
