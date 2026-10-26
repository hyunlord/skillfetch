#!/usr/bin/env python3
"""Stage 11: one session = (task, condition, tag), E1 only. Stage 10 harness (run_s10.py) with the DESIGN §6 changes:

- isolation: per session `git clone --no-local --single-branch --branch <branch>` into ~/skillfetch-e2e-wt/s11/<random id>,
  branch renamed to `main`, `origin` removed (no other branches, no remote-tracking refs, no source path; --no-local copies only objects reachable from that branch, while --local would hardlink every object, unreachable ones from earlier work included). The clone is
  deleted after the check. Condition names appear only in the private output paths, never in the session directory.
- branches: A = the task's base branch; R0 / R1 = `s11-r` (base + one commit "chore: add project skill" adding
  .claude/skills/skillfetch-router/SKILL.md = 3fef3f8 assets/router-skill/SKILL.md).
- preflight before every session: index hashes (stage10/scripts/verify_index.py), the repo's `s11-r` is exactly base +
  the router file (blob checked), the base has no router file, the main checkout's working tree has no router file,
  toolchains present, Postgres up for fastapi / 6b checks.
- limits: harness_fail = the final result event is an error whose text is a usage/spend-limit message (any turn count);
  no_result = the stream has no result event and the session did not time out. Both are re-run by the queue.
- PATH: /opt/homebrew/opt/openjdk/bin is put first only in the session and check environments (keg-only JDK).
- processes (DESIGN §6.1, 2026-10-25): preflight blocks the session if any process (listening or not) has the e2e
  workspace, ~/skillfetch-e2e-wt or a stage name (s1b/s6b/s10/…) in its cwd or arguments, except the harness Postgres
  (cwd e2e/infra/pgdata), descendants of the operator process (the nearest `claude` ancestor, else the outermost
  run_queue_s11/run_s11 ancestor — this covers concurrent queue sessions), and processes in a session directory that
  still exists (a concurrent session's detached check server; added 2026-10-26 during the main run, DESIGN §11). `claude -p` runs in its own process group;
  after the session and again after the check, every process in that group or with the session directory in its cwd or
  arguments gets SIGTERM, then SIGKILL after 5 s, and the scan is repeated; anything left is recorded
  (meta.leftover_procs) and stops the queue.

usage: run_s11.py <task_id> <A|R0|R1> <tag>                       run one session
       run_s11.py --dry-run [--no-prep] [--fake-server] <task_id> <A|R0|R1> <tag>  everything except `claude -p` (clone, refs, router
                                                                    file, deps, command line); writes
                                                                    stage11-private/dryrun/<cond>/<task>-<tag>.json
MCP: E1 = --setting-sources project --strict-mcp-config --mcp-config stage11/mcp/mcp-{none,r0,r1}.json (server 3fef3f8).
"""
import hashlib
import json
import os
import re
import signal
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
E2E = S11.parent
S10 = E2E / "stage10"
PRIV = E2E / "stage11-private"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
sys.path.insert(0, str(S10 / "scripts"))
import run_stage1 as rs  # noqa: E402
from run_s10 import final_reply, strip_graft_noise  # noqa: E402
from run_task import ALLOWED_TOOLS, PG_PORT, PGBIN, SESSION_TIMEOUT_S, child_env, sh  # noqa: E402

WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s11"
SERVER = Path.home() / "skillfetch-e2e-wt" / "s10-server" / "3fef3f8"
JDK_BIN = "/opt/homebrew/opt/openjdk/bin"
MAX_TURNS = "40"
MCP = {"A": S11 / "mcp" / "mcp-none.json", "R0": S11 / "mcp" / "mcp-r0.json", "R1": S11 / "mcp" / "mcp-r1.json"}
COND_BRANCH = "s11-r"
ROUTER_PATH = ".claude/skills/skillfetch-router/SKILL.md"
ROUTER_SHA256 = "3efef1e0b7cf5181fa1911f4ebd075cb5d8b8865926d6353399221392bf8f040"
ROUTER_MSG = "chore: add project skill"
PG = f"postgresql://postgres:changethis@localhost:{PG_PORT}"
LOCK = PRIV / "runs" / "screenshot.lock"
WT_BASE = str(Path.home() / "skillfetch-e2e-wt")
STAGE_RE = re.compile(r"(?:^|[\s/=])(?:s1b|s1|s2|s4|s5|s6b|s10|s11)-\w")
LIMIT_MARKERS = ("hit your", "usage limit", "spend limit", "session limit", "limit resets", "usage-credits")


def load_tasks():
    """Bundles (1), (2), (4): Stage 10 tasks (same prompts and start commits); bundle (3): stage11/tasks-b3.jsonl;
    bundle (4) addition s11-t266: stage11/tasks-b4add.jsonl (DESIGN §3.2.2)."""
    out = {}
    for line in (S10 / "tasks.jsonl").open():
        t = json.loads(line)
        if t["bundle"] in (1, 2, 4):
            out[t["id"]] = t
    for f in ("tasks-b3.jsonl", "tasks-b4add.jsonl"):
        for line in (S11 / f).open():
            t = json.loads(line)
            out[t["id"]] = t
    return out


def env_s11(extra=None):
    e = child_env(extra)
    e["PATH"] = f"{JDK_BIN}:{e.get('PATH', '')}"
    return e


def git(repo, *args, check=True):
    return sh(["git", "-C", str(repo), *args], check=check).stdout.strip()


def proc_table():
    """{pid: {ppid, pgid, cmd, cwd}} for all processes (ps + lsof cwd)."""
    procs = {}
    for line in subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,command="], capture_output=True, text=True).stdout.splitlines():
        f = line.split(None, 3)
        if len(f) >= 4 and f[0].isdigit():
            procs[int(f[0])] = {"ppid": int(f[1]), "pgid": int(f[2]), "cmd": f[3], "cwd": ""}
    pid = None
    for line in subprocess.run(["lsof", "-d", "cwd", "-Fpn"], capture_output=True, text=True).stdout.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and pid in procs:
            procs[pid]["cwd"] = line[1:]
    return procs


def ancestors(procs, pid):
    out = []
    while pid in procs and pid not in out and pid > 1:
        out.append(pid)
        pid = procs[pid]["ppid"]
    return out


def descendants(procs, root):
    kids, out, stack = {}, set(), [root]
    for p, v in procs.items():
        kids.setdefault(v["ppid"], []).append(p)
    while stack:
        p = stack.pop()
        if p not in out:
            out.add(p)
            stack += kids.get(p, [])
    return out


def leftover_processes(procs=None):
    """Processes tied to the e2e work that are not part of the running harness (see module doc)."""
    procs = procs or proc_table()
    anc = ancestors(procs, os.getpid())
    root = next((a for a in anc if os.path.basename(procs[a]["cmd"].split()[0]) == "claude"), None)
    if root is None:
        root = next((a for a in reversed(anc) if re.search(r"run_queue_s11\.py|run_s11\.py", procs[a]["cmd"])), os.getpid())
    allowed = descendants(procs, root) | set(anc)
    # session directories that still exist belong to sessions still running (a session's directory is removed only after
    # its own cleanup); processes there — e.g. a design check's detached `next start` — are that session's to clean up
    active = [str(d) for d in WT_ROOT.iterdir()] if WT_ROOT.is_dir() else []
    out = []
    for pid, p in procs.items():
        if pid in allowed:
            continue
        if any(p["cwd"] == d or p["cwd"].startswith(d + "/") or d in p["cmd"] for d in active):
            continue
        text = p["cmd"] + " " + p["cwd"]
        if not (str(E2E) in text or WT_BASE in text or STAGE_RE.search(text)):
            continue
        if "postgres" in p["cmd"] and p["cwd"].startswith(str(E2E / "infra" / "pgdata")):
            continue
        out.append({"pid": pid, "ppid": p["ppid"], "pgid": p["pgid"], "cwd": p["cwd"][:200], "cmd": p["cmd"][:200]})
    return out


def cleanup_session_procs(wt, pgid=None):
    """SIGTERM (then SIGKILL after 5 s) every process in the session's process group or with the session directory in
    its cwd or arguments; returns {"killed": [...], "remaining": [...]} after a fresh scan."""
    me = set(ancestors(proc_table(), os.getpid()))

    def targets():
        return {pid: p for pid, p in proc_table().items() if pid not in me
                and ((pgid and p["pgid"] == pgid) or str(wt) in p["cmd"] or p["cwd"].startswith(str(wt)))}
    first = targets()
    for sig, wait in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 2.0)):
        t = targets()
        for pid in t:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        t0 = time.time()
        while targets() and time.time() - t0 < wait:
            time.sleep(0.2)
    left = targets()
    return {"killed": [{"pid": k, "cmd": v["cmd"][:120]} for k, v in first.items() if k not in left],
            "remaining": [{"pid": k, "cwd": v["cwd"][:120], "cmd": v["cmd"][:120]} for k, v in left.items()]}


def preflight(task, cond):
    """Problems that must stop the session (empty list = ok) and facts to record."""
    probs, facts = [], {}
    v = sh(["python3", str(S10 / "scripts" / "verify_index.py")])
    facts["index"] = v.stdout.strip()
    if v.returncode != 0:
        probs.append("index hash check failed: " + v.stdout.strip())
    repo = E2E / "repos" / task["repo"]
    base = git(repo, "rev-parse", task["base_branch"])
    r = git(repo, "rev-parse", COND_BRANCH, check=False)
    facts.update({"base": base, "s11_r": r})
    if git(repo, "rev-parse", f"{COND_BRANCH}^", check=False) != base:
        probs.append(f"{COND_BRANCH} parent is not {task['base_branch']}")
    if git(repo, "diff", "--name-only", base, COND_BRANCH, check=False).splitlines() != [ROUTER_PATH]:
        probs.append(f"{COND_BRANCH} changes more than the router file")
    blob = subprocess.run(["git", "-C", str(repo), "show", f"{COND_BRANCH}:{ROUTER_PATH}"], capture_output=True).stdout
    if hashlib.sha256(blob).hexdigest() != ROUTER_SHA256:
        probs.append("router file sha256 mismatch on s11-r")
    if git(repo, "log", "-1", "--format=%s", COND_BRANCH, check=False) != ROUTER_MSG:
        probs.append("router commit message is not neutral")
    if sh(["git", "-C", str(repo), "cat-file", "-e", f"{base}:{ROUTER_PATH}"]).returncode == 0:
        probs.append("base already has the router file")
    if (repo / ROUTER_PATH).exists():
        probs.append("main checkout working tree has the router file")
    facts["main_checkout"] = {"branch": git(repo, "branch", "--show-current", check=False),
                              "head": git(repo, "rev-parse", "HEAD", check=False)[:12]}
    for tool, path in (("claude", None), ("uvx", None), ("go", None), ("goreleaser", None), ("java", JDK_BIN + "/java")):
        if not (Path(path).exists() if path else shutil.which(tool)):
            probs.append(f"missing tool {tool}")
    if not SERVER.exists():
        probs.append("server worktree missing")
    left = leftover_processes()
    facts["leftover_processes"] = left
    if left:
        probs.append(f"{len(left)} leftover process(es): " + "; ".join(f"{x['pid']} cwd={x['cwd'][:60]} {x['cmd'][:60]}" for x in left[:5]))
    if task["repo"] == "fastapi" or task["check"] == "6b":
        pg = sh([f"{PGBIN}/pg_isready", "-h", "localhost", "-p", str(PG_PORT)])
        if pg.returncode != 0:
            probs.append("postgres not ready")
    return probs, facts


def clone(task, cond, wt):
    """Single-branch clone of the condition branch, renamed to main, origin removed. Returns the clone facts."""
    repo = E2E / "repos" / task["repo"]
    branch = task["base_branch"] if cond == "A" else COND_BRANCH
    wt.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", branch, str(repo), str(wt)], check=True)
    sh(["git", "-C", str(wt), "branch", "-m", branch, "main"], check=True)
    sh(["git", "-C", str(wt), "remote", "remove", "origin"], check=True)
    refs = sh(["git", "-C", str(wt), "for-each-ref", "--format=%(refname)"]).stdout.split()
    head = git(wt, "rev-parse", "HEAD")
    router = wt / ROUTER_PATH
    # tracked entries (files and symlinks); the clean-status requirement below rules out untracked ones
    skills = sorted(sh(["git", "-C", str(wt), "ls-tree", "-r", "--name-only", "HEAD", ".claude/skills"]).stdout.split())
    facts = {"branch": branch, "head": head, "refs": refs, "remotes": sh(["git", "-C", str(wt), "remote"]).stdout.split(),
             "status": sh(["git", "-C", str(wt), "status", "--porcelain", "--ignored"]).stdout.splitlines(),
             "skills_files": skills,
             "router_sha256": hashlib.sha256(router.read_bytes()).hexdigest() if router.exists() else None,
             "commits": sh(["git", "-C", str(wt), "log", "--format=%h %s"]).stdout.splitlines()[:5]}
    # project skills already in the start commit (fastapi template: .claude/skills/library-skills) are in every condition
    base_skills = sorted(p for p in sh(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", task["base_branch"],
                                        ".claude/skills"]).stdout.split())
    facts["base_skills_files"] = base_skills
    want_router = None if cond == "A" else ROUTER_SHA256
    want_skills = base_skills if cond == "A" else sorted(base_skills + [ROUTER_PATH])
    facts["unreachable_objects"] = len(sh(["git", "-C", str(wt), "fsck", "--unreachable", "--no-reflogs"]).stdout.split("\n")) - 1
    facts["ok"] = (refs == ["refs/heads/main"] and not facts["remotes"] and not facts["status"] and facts["unreachable_objects"] == 0
                   and facts["router_sha256"] == want_router and skills == want_skills)
    return facts


def prepare(task, wt, sid):
    """Dependencies a developer would already have (all conditions alike)."""
    extra = {}
    t0 = time.time()
    if task["repo"] == "fastapi":
        db = "s11_" + sid
        pg = child_env({"PGPASSWORD": "changethis"})
        for q in (f"DROP DATABASE IF EXISTS {db};", f"CREATE DATABASE {db};"):
            sh([f"{PGBIN}/psql", "-h", "localhost", "-p", str(PG_PORT), "-U", "postgres", "-c", q], env=pg, check=True)
        extra = {"DATABASE_URL": f"{PG}/{db}"}
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
        sh(["uv", "run", "alembic", "upgrade", "head"], cwd=wt / "backend", env=child_env(extra), check=True, timeout=300)
        if task.get("ui"):
            sh(["bun", "install", "--frozen-lockfile"], cwd=wt, env=child_env(), check=True, timeout=900)
    elif task.get("stack") == "rust":
        sh(["cargo", "build", "--all-targets", "-q"], cwd=wt, env=child_env(), timeout=1800)
    elif task.get("stack") == "swift":
        sh(["swift", "build", "--build-tests"], cwd=wt, env=child_env(), timeout=1800)
    elif task.get("stack") == "go":
        sh(["go", "build", "./..."], cwd=wt, env=env_s11(), timeout=900)
    elif (wt / "package.json").exists():
        sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt, env=child_env(), check=True, timeout=900)
    elif (wt / "pyproject.toml").exists():
        sh(["uv", "sync", "-q"], cwd=wt, env=child_env(), check=True, timeout=900)
    return extra, round(time.time() - t0, 1)


def build_cmd(task, cond, out):
    return ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose", "--include-hook-events",
            "--max-turns", MAX_TURNS, "--allowedTools", ALLOWED_TOOLS, "--debug-file", str(out) + ".debug.log",
            "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(MCP[cond])]


def result_event(jsonl):
    ev = None
    for line in Path(jsonl).open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "result":
            ev = d
    return ev


def run_check(task, wt, base, out):
    noise = rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    if task["check"] == "b4":
        cmd = ["python3", str(E2E / "stage10-private" / "b4" / "checks" / "check_b4.py"), task["id"].removeprefix("s10-"),
               str(wt), str(cdir), "--reply", str(out) + ".reply.txt"]
    elif task["check"] in ("b3", "b4add"):
        sub = "b3" if task["check"] == "b3" else "b4"
        cmd = ["python3", str(PRIV / sub / "checks" / task["src"] / "check.py"), str(wt), str(cdir),
               "--reply", str(out) + ".reply.txt", "--base", base]
    elif task["check"] == "s2":
        cmd = ["python3", str(E2E / "stage2" / "checks" / "check_s2.py"), task["id"], str(wt), str(cdir), "--base", base]
    else:
        cmd = ["python3", str(E2E / "stage6" / "6b" / "checks" / "check_6b.py"), task["id"], str(wt), str(cdir), "--pg", PG,
               "--lock", str(LOCK), "--base", base]
    p = sh(cmd, env=env_s11(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text((p.stdout + p.stderr).replace(str(wt), "<wt>"))
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    no_prep = "--no-prep" in args
    task_id, cond, tag = [a for a in args if not a.startswith("--")]
    tasks = load_tasks()
    assert task_id in tasks and cond in MCP, (task_id, cond)
    task = tasks[task_id]
    assert cond != "A" or task["bundle"] == 4, "A runs only in bundle (4) (DESIGN §2)"
    probs, pre = preflight(task, cond)
    if probs:
        sys.exit("preflight failed: " + "; ".join(probs))
    sid = secrets.token_hex(6)
    wt = WT_ROOT / sid
    out_dir = PRIV / ("dryrun" if dry else "runs") / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{task_id}-{tag}"
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        cl = clone(task, cond, wt)
        if not cl["ok"]:
            sys.exit("clone state check failed: " + json.dumps(cl))
        base = cl["head"]
        extra, prep_s = ({}, 0.0) if (dry and no_prep) else prepare(task, wt, sid)
        cmd = build_cmd(task, cond, out)
        if dry:
            fake = None
            if "--fake-server" in args:  # a detached process in the session dir, as a session-started server would be
                fake = subprocess.Popen(["python3", "-c", "import time; time.sleep(600)", str(wt)], cwd=wt, start_new_session=True,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
            cleanup = cleanup_session_procs(wt)
            v2 = sh(["python3", str(S10 / "scripts" / "verify_index.py")])
            rec = {"task": task_id, "bundle": task["bundle"], "cond": cond, "tag": tag, "session_dir": str(wt), "preflight": pre,
                   "clone": cl, "prep_s": prep_s, "prep_status": sh(["git", "status", "--porcelain"], cwd=wt).stdout.splitlines(),
                   "cmd": cmd, "path_head": env_s11(extra)["PATH"].split(":")[0], "index_ok_after": v2.returncode == 0,
                   "fake_server_pid": fake, "cleanup": cleanup, "leftover_after": leftover_processes()}
            Path(str(out) + ".json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            print(json.dumps({"dry_run": True, "task": task_id, "cond": cond, "tag": tag, "clone_ok": cl["ok"],
                              "refs": cl["refs"], "router": bool(cl["router_sha256"]), "prep_s": prep_s,
                              "index_ok_after": rec["index_ok_after"], "fake_server_pid": fake,
                              "cleanup_killed": [x["pid"] for x in cleanup["killed"]], "cleanup_remaining": len(cleanup["remaining"]),
                              "leftover_after": len(rec["leftover_after"])}))
            return
        t0 = time.time()
        timed_out = False
        with open(str(out) + ".jsonl", "w") as fo, open(str(out) + ".stderr", "w") as fe, open(str(out) + ".ts", "w") as ts, \
                open("/dev/null") as fi:
            p = subprocess.Popen(cmd, cwd=wt, env=env_s11(extra), stdin=fi, stdout=subprocess.PIPE, stderr=fe,
                                 start_new_session=True)  # own process group, cleaned up below

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
        procs_after_session = cleanup_session_procs(wt, pgid=p.pid)
        ev = result_event(str(out) + ".jsonl")
        reply = (ev or {}).get("result") or ""
        Path(str(out) + ".reply.txt").write_text(final_reply(str(out) + ".jsonl"))
        harness_fail = bool(ev) and bool(ev.get("is_error")) and any(m in reply.lower() for m in LIMIT_MARKERS)
        no_result = ev is None and not timed_out
        status_before = sh(["git", "status", "--porcelain", "--ignored"], cwd=wt).stdout.splitlines()
        graft_removed = strip_graft_noise(wt, base)
        diff = rs.collect_diff(wt, base, out)
        check = run_check(task, wt, base, out)
        procs_after_check = cleanup_session_procs(wt)
        leftover = leftover_processes()
        v2 = sh(["python3", str(S10 / "scripts" / "verify_index.py")])
        meta = {"task": task_id, "bundle": task["bundle"], "cond": cond, "env": "E1", "tag": tag, "repo": task["repo"],
                "branch": cl["branch"], "base": base, "session_dir": str(wt), "preflight": pre, "clone": cl, "cmd": cmd,
                "exit_code": rc, "timed_out": timed_out, "prep_s": prep_s, "wall_s": wall, "spawn_epoch_ms": int(t0 * 1000),
                "cost_usd": (ev or {}).get("total_cost_usd"), "num_turns": (ev or {}).get("num_turns"), "diff": diff,
                "graft_removed": graft_removed, "status_before_strip": status_before, "check": check,
                "harness_fail": harness_fail, "no_result": no_result, "index_ok_after": v2.returncode == 0,
                "procs_after_session": procs_after_session, "procs_after_check": procs_after_check, "leftover_procs": leftover}
        Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(json.dumps({"task": task_id, "cond": cond, "tag": tag, "exit_code": rc, "wall_s": wall, "cost_usd": meta["cost_usd"],
                          "check": check.get("pass"), "harness_fail": harness_fail, "no_result": no_result,
                          "index_ok_after": meta["index_ok_after"], "leftover_procs": len(leftover)}))
        if not meta["index_ok_after"]:
            sys.exit("index hash check failed after the session")
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        if dry and task["repo"] == "fastapi":  # a dry run leaves no database behind
            sh([f"{PGBIN}/psql", "-h", "localhost", "-p", str(PG_PORT), "-U", "postgres", "-c", f"DROP DATABASE IF EXISTS s11_{sid};"],
               env=child_env({"PGPASSWORD": "changethis"}))


if __name__ == "__main__":
    main()
