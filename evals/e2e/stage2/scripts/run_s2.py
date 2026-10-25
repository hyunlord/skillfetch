#!/usr/bin/env python3
"""Stage 2: one session = (task, condition, rep). Same harness as 1b (stage1/scripts/run_stage1.py: claude -p,
stream-json, --max-turns 40, same allowed tools, env stripping, diff), stage-2 repos/tasks/checks.

usage: run_s2.py <task_id> <A|B|C2> <rep>
  A   repo at s2-a
  B   repo at s2-a + --append-system-prompt-file expert-content/<task>.md (load_skills output of the B skill)
  C2  repo at s2-c2 (router SKILL.md + .mcp.json, skillfetch pinned at e2a1b65)
Outputs: stage2/runs/<cond>/<task>-r<rep>.{jsonl,ts,debug.log,stderr,diff,meta.json} + .check/
"""
import json
import sys
import time
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S2 = E2E / "stage2"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
import run_stage1 as rs  # noqa: E402
from run_task import child_env, sh  # noqa: E402

MAX_TURNS = "40"
WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s2"
BRANCH = {"A": "s2-a", "B": "s2-a", "C2": "s2-c2"}


def prepare(task, wt, base):
    repo = E2E / "repos" / task["repo"]
    if wt.exists():
        sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    wt.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt), base], check=True)
    if (wt / "package.json").exists():
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    else:
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)


def run_check(task, wt, base, out):
    noise = rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    p = sh(["python3", str(S2 / "checks" / "check_s2.py"), task["id"], str(wt), str(cdir), "--base", base],
           env=child_env(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text(p.stdout + p.stderr)
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def main():
    task_id, cond, rep = sys.argv[1], sys.argv[2], int(sys.argv[3])
    task = next(t for t in yaml.safe_load((S2 / "tasks-stage2.yaml").read_text())["tasks"] if t["id"] == task_id)
    repo = E2E / "repos" / task["repo"]
    base = sh(["git", "-C", str(repo), "rev-parse", BRANCH[cond]], check=True).stdout.strip()
    run_id = f"{task_id}-{cond}-r{rep}"
    runs = S2 / "runs" / cond
    runs.mkdir(parents=True, exist_ok=True)
    out = runs / f"{task_id}-r{rep}"
    wt = WT_ROOT / run_id
    meta = {"task": task, "cond": cond, "rep": rep, "base_commit": base, "worktree": str(wt), "max_turns": int(MAX_TURNS),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "index_built_at": json.loads((Path.home() / ".skillfetch/index/manifest.json").read_text())["built_at"]}
    prepare(task, wt, base)
    meta["session"] = rs.run_session(task, "B" if cond == "B" else cond, wt, {}, out, max_turns=MAX_TURNS,
                                     expert_dir=S2 / "expert-content")
    meta["diff"] = rs.collect_diff(wt, base, out)
    meta["check"] = run_check(task, wt, base, out)
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(run_id, "done", meta["session"]["exit_code"], meta["session"]["wall_s"], "check", meta["check"].get("pass"))


if __name__ == "__main__":
    main()
