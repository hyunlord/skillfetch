#!/usr/bin/env python3
"""Stage 10: one session = (task, condition, environment, tag). Fresh worktree of the condition branch, dependency
prep, index hash check, `claude -p`, diff, objective check. Raw output goes to stage10-private/runs/<env>/<cond>/.

usage: run_s10.py <task_id> <A|R0|R1|R1s> <E1|E2> <tag>
  A        branch <base>      no MCP
  R0 / R1  branch s10-r       MCP skillfetch serve --index stage10/index/{release|staging-4} (server 3fef3f8)
  R1s      branch s10-rs      router = 3fef3f8 assets/router-skill/variants/fast.md, MCP as R1 (E1 only)
  E1       --setting-sources project --strict-mcp-config --mcp-config <file>   (clean)
  E2       user settings (default setting sources); R1 adds --mcp-config <file> on top of the user's MCP servers
Both: --output-format stream-json --verbose --include-hook-events --max-turns 40 --allowedTools <6b list>.
E2 also hashes ~/.claude/skills, ~/.claude/settings.json and ~/.claude/CLAUDE.md before and after the session.
Before the diff, files the user's graft SessionStart hook writes into the worktree (.gitignore block, .ignore, graft/)
are removed and recorded (all conditions; nothing to remove in E1). The final reply is saved to <out>.reply.txt.
"""
import contextlib
import fcntl
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
E2E = S10.parent
PRIV = E2E / "stage10-private"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
import run_stage1 as rs  # noqa: E402
from run_task import ALLOWED_TOOLS, PG_PORT, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s10"
MAX_TURNS = "40"
MCP = {"A": S10 / "mcp" / "mcp-none.json", "R0": S10 / "mcp" / "mcp-r0.json", "R1": S10 / "mcp" / "mcp-r1.json",
       "R1s": S10 / "mcp" / "mcp-r1s.json"}
BRANCH = {"R0": "s10-r", "R1": "s10-r", "R1s": "s10-rs"}
GRAFT_GITIGNORE = re.compile(r"\n?# graft's local graph cache[^\n]*\n/graft/\n?")
GRAFT_IGNORE_LINES = {"!graft/", "graft/.cache/", "graft/.graph/"}
PG = f"postgresql://postgres:changethis@localhost:{PG_PORT}"
LOCK = PRIV / "runs" / "screenshot.lock"
LIMIT_MARKERS = ("hit your", "usage limit", "spend limit", "session limit")


@contextlib.contextmanager
def repo_lock(repo):
    """Serialize `git worktree add/remove` per repo: concurrent calls race on .git/worktrees (seen in the pilot)."""
    (PRIV / "runs").mkdir(parents=True, exist_ok=True)
    with open(PRIV / "runs" / f".lock-{Path(repo).name}", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_task(task_id):
    for f in ("tasks.jsonl", "tasks-b3new.jsonl"):  # tasks-b3new: DESIGN §11 re-measurement of bundle (3)
        for line in (S10 / f).open():
            t = json.loads(line)
            if t["id"] == task_id:
                return t
    raise SystemExit(f"unknown task {task_id}")


def tree_hash(path):
    p = Path(path).expanduser()
    if not p.exists():
        return None
    h = hashlib.sha256()
    files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]
    for f in files:
        h.update(str(f.relative_to(p.parent)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def user_state():
    return {k: tree_hash(k) for k in ("~/.claude/skills", "~/.claude/settings.json", "~/.claude/CLAUDE.md")}


def prepare(task, repo, wt, base, run_id):
    if task["repo"] in ("fastapi", "nextjs"):
        with repo_lock(repo):
            return rs.prepare(task, repo, wt, base, run_id)
    with repo_lock(repo):
        if wt.exists():
            sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
        wt.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt), base], check=True)
    if task.get("stack") == "rust":  # warm build so the session does not wait on the first compile (all conditions)
        sh(["cargo", "build", "--all-targets", "-q"], cwd=wt, env=child_env(), timeout=1800)
    elif task.get("stack") == "swift":
        sh(["swift", "build", "--build-tests"], cwd=wt, env=child_env(), timeout=1800)
    elif (wt / "package.json").exists():
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    elif (wt / "pyproject.toml").exists():
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
    return {}


def in_base(wt, base, path):
    return sh(["git", "cat-file", "-e", f"{base}:{path}"], cwd=wt).returncode == 0


def strip_graft_noise(wt, base):
    """Remove what the user's graft SessionStart hook writes into a worktree (E2): the block it appends to .gitignore,
    its .ignore lines and its graft/ cache dir. Only those exact lines/paths; returns what was removed."""
    removed = []
    gi = wt / ".gitignore"
    if gi.exists():
        s = gi.read_text()
        m = GRAFT_GITIGNORE.search(s)
        if m:
            s2 = GRAFT_GITIGNORE.sub("", s, count=1)
            if not s2.strip() and not in_base(wt, base, ".gitignore"):
                gi.unlink()
            else:
                gi.write_text(s2)
            removed.append({"path": ".gitignore", "text": m.group(0)})
    ig = wt / ".ignore"
    if ig.exists():
        lines = ig.read_text().splitlines(keepends=True)
        drop = [l for l in lines if l.strip() in GRAFT_IGNORE_LINES or l.startswith(("# graft's cards", "# .ignore before .gitignore"))]
        if drop:
            keep = [l for l in lines if l not in drop]
            if not "".join(keep).strip() and not in_base(wt, base, ".ignore"):
                ig.unlink()
            else:
                ig.write_text("".join(keep))
            removed.append({"path": ".ignore", "text": "".join(drop)})
    gd = wt / "graft"
    if gd.is_dir() and not in_base(wt, base, "graft"):
        n = sum(1 for x in gd.rglob("*") if x.is_file())
        shutil.rmtree(gd, ignore_errors=True)
        removed.append({"path": "graft/", "text": f"{n} files"})
    return removed


def final_reply(jsonl):
    r = ""
    for line in Path(jsonl).open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "result":
            r = d.get("result") or ""
    return r


def run_check(task, wt, base, out):
    noise = rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    if task["check"] == "b4":
        cmd = ["python3", str(PRIV / "b4" / "checks" / "check_b4.py"), task["id"].removeprefix("s10-"), str(wt), str(cdir),
               "--reply", str(out) + ".reply.txt"]
    elif task["check"] == "b3new":
        cmd = ["python3", str(PRIV / "b3new" / "checks" / task["src"] / "check.py"), str(wt), str(cdir),
               "--reply", str(out) + ".reply.txt", "--base", base]
    elif task["check"] == "s2":
        cmd = ["python3", str(E2E / "stage2" / "checks" / "check_s2.py"), task["id"], str(wt), str(cdir), "--base", base]
    else:
        cmd = ["python3", str(E2E / "stage6" / "6b" / "checks" / "check_6b.py"), task["id"], str(wt), str(cdir), "--pg", PG, "--lock", str(LOCK), "--base", base]
    p = sh(cmd, env=child_env(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text(p.stdout + p.stderr)
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def main():
    task_id, cond, env, tag = sys.argv[1:5]
    assert cond in MCP and env in ("E1", "E2") and not (env == "E2" and cond in ("R0", "R1s")), (cond, env)
    v = sh(["python3", str(S10 / "scripts" / "verify_index.py")])
    if v.returncode != 0:
        sys.exit("index hash check failed before the session: " + v.stdout)
    task = load_task(task_id)
    repo = E2E / "repos" / task["repo"]
    branch = task["base_branch"] if cond == "A" else BRANCH[cond]
    base = sh(["git", "-C", str(repo), "rev-parse", branch], check=True).stdout.strip()
    run_id = f"s10-{env}-{cond}-{task_id}-{tag}"
    wt = WT_ROOT / run_id
    out_dir = PRIV / "runs" / env / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{task_id}-{tag}"
    t_prep = time.time()
    extra = prepare(task, repo, wt, base, run_id)
    prep_s = round(time.time() - t_prep, 1)
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose", "--include-hook-events",
           "--max-turns", MAX_TURNS, "--allowedTools", ALLOWED_TOOLS, "--debug-file", str(out) + ".debug.log"]
    if env == "E1":
        cmd += ["--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(MCP[cond])]
    elif cond != "A":
        cmd += ["--mcp-config", str(MCP[cond])]
    before = user_state() if env == "E2" else None
    t0 = time.time()
    timed_out = False
    with open(str(out) + ".jsonl", "w") as fo, open(str(out) + ".stderr", "w") as fe, open(str(out) + ".ts", "w") as ts, open("/dev/null") as fi:
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
    after = user_state() if env == "E2" else None
    # usage/spend limit: the final result text is the limit message (any turn count; such sessions are cut off mid-work)
    harness_fail = any(m in final_reply(str(out) + ".jsonl").lower() for m in LIMIT_MARKERS)
    Path(str(out) + ".reply.txt").write_text(final_reply(str(out) + ".jsonl"))
    status_before = sh(["git", "status", "--porcelain", "--ignored"], cwd=wt).stdout.splitlines()  # env-trace audit
    graft_removed = strip_graft_noise(wt, base)
    diff = rs.collect_diff(wt, base, out)
    check = run_check(task, wt, base, out)
    v2 = sh(["python3", str(S10 / "scripts" / "verify_index.py")])
    meta = {"task": task_id, "bundle": task["bundle"], "cond": cond, "env": env, "tag": tag, "repo": task["repo"], "branch": branch,
            "base": base, "cmd": cmd, "exit_code": rc, "timed_out": timed_out, "prep_s": prep_s, "wall_s": wall,
            "spawn_epoch_ms": int(t0 * 1000), "diff": diff, "graft_removed": graft_removed, "status_before_strip": status_before, "check": check, "harness_fail": harness_fail,
            "index_ok_after": v2.returncode == 0, "user_state_before": before, "user_state_after": after,
            "user_state_unchanged": (before == after) if env == "E2" else None}
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    with repo_lock(repo):
        sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
    print(json.dumps({"task": task_id, "cond": cond, "env": env, "tag": tag, "exit_code": rc, "wall_s": wall,
                      "check": check.get("pass"), "harness_fail": harness_fail, "index_ok_after": meta["index_ok_after"],
                      "user_state_unchanged": meta["user_state_unchanged"]}))
    if not meta["index_ok_after"]:
        sys.exit("index hash check failed after the session")


if __name__ == "__main__":
    main()
