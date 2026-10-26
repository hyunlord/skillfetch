#!/usr/bin/env python3
"""Stage Q runner (DESIGN §0–§6). Reuses the Stage 11 harness (stage11/scripts/run_s11.py): single-branch --no-local
clone, branch renamed to main, origin removed, random session directory, preflight (index hashes, leftover processes),
process-group cleanup, prepare() and run_check(); E1 flags, JDK on PATH in the session env only.

Jobs (one "job tag" per queue line):
  q1:<task>:on|off      Q1, task in d1-landing d4-email s10-t016 s11-t266 s2-api s2-data; on = router S-b′ (s11-r) +
                        MCP staging-4; off = start commit, no MCP (= A)
  q2:S | q2:SB | q2:C   Q2 on sq-mono: S = tasks 1–4 in one session (claude -p, then --resume); SB = S on sq-rb (S-B
                        router variant); C = a new session per task on the same working tree. Task 1 names the canary
                        skill, placed at a random path outside the repo.
  q5:<id>               Q5 trivial (T1–T5) or named-skill (named-<task>) task, on
  q6:<task>             Q6 body fetch blocked, on: MCP server from a fixed venv (3fef3f8) with an empty temporary HOME
                        and HTTP(S)_PROXY on a closed port; task in s10-t016 s2-api s2-data
  rf:<arm>              re-fire check (stageRF/DESIGN.md, added 2026-10-26): Q2 S without the canary (task 1 without its
                        last sentence), one session, `--resume`; arm cur = sq-r (S-b′), a = sq-rfa (variants/refire.md),
                        b = sq-rfb (refire.md + repo-root CLAUDE.md, variants/refire-CLAUDE.md)
  rfc:<arm>             the Q2 residue rerun with the winning arm: exactly q2:S (canary) on that arm's branch
  lq:<task>             Q1 extension local-skill case (DESIGN-Q1x.md §2.1, added 2026-10-26): on, one session, request 1 =
                        tasks-lq.jsonl "first" (names the canary skill at a random path), request 2 = the task's own
                        prompt via `--resume`; the task's check runs on the final tree
Output root: stageQ-private, or $SQ_PRIV when set (the re-fire check uses stageRF-private).
Per request: <out>.pK.jsonl / .reply.txt / .snap (tree after the request, via a temporary git index; no commit or ref in
the session's repo) / .diff (vs the previous snapshot) / .new (files added by this request). Meta in <out>.meta.json.
usage: run_q.py <job> <tag> [--dry-run | --check-test]
  --dry-run: everything except `claude -p`, prepare() and the check
  --check-test (added after the pilot): everything except `claude -p`, with prepare() and the check on the unchanged tree"""
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = Path(os.environ.get("SQ_PRIV") or E2E / "stageQ-private")
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
import run_s11 as rs  # noqa: E402

Q_ROOT = Path.home() / "skillfetch-e2e-wt" / "sq"
rs.WT_ROOT = Q_ROOT  # leftover check: session directories that still exist = sessions still running
INDEX = E2E / "stage10" / "index" / "staging-4"
SERVER = Path.home() / "skillfetch-e2e-wt" / "s10-server" / "3fef3f8"
BLOCKED_VENV = Path.home() / "skillfetch-e2e-wt" / "q-blocked-venv"
CANARY_SRC = E2E / "stageQ-private" / "canary" / "canary"
RF_BRANCH = {"cur": "sq-r", "a": "sq-rfa", "b": "sq-rfb"}
RF_FILES = {"sq-rfb": ["CLAUDE.md"]}  # files besides the router a re-fire branch may add
MAX_TURNS = "40"


def mcp_on():
    return {"mcpServers": {"skillfetch": {"type": "stdio", "command": "uvx",
                                          "args": ["--from", str(SERVER), "skillfetch", "serve", "--index", str(INDEX)], "env": {}}}}


def mcp_blocked(home):
    px = "http://127.0.0.1:9"
    return {"mcpServers": {"skillfetch": {"type": "stdio", "command": str(BLOCKED_VENV / "bin" / "skillfetch"),
                                          "args": ["serve", "--index", str(INDEX)],
                                          "env": {"HOME": str(home), "HTTPS_PROXY": px, "HTTP_PROXY": px, "https_proxy": px, "http_proxy": px}}}}


def jl(p):
    return [json.loads(l) for l in Path(p).open() if l.strip()]


def requests_md():
    return (SQ / "requests.md").read_text()


def all_tasks():
    """run_s11's tasks plus, for the Q1 extension (DESIGN-Q1x.md), Stage 10 bundle (3): the first set (s6b-t133/t179/t354,
    check 6b) and the re-measurement (tasks-b3new.jsonl, check b3new)."""
    t = rs.load_tasks()
    for f in ("tasks.jsonl", "tasks-b3new.jsonl"):
        for line in (E2E / "stage10" / f).open():
            x = json.loads(line)
            if x["bundle"] == 3:
                t.setdefault(x["id"], x)
    return t


def run_check_q(task, wt, base, out):
    """run_s11.run_check, plus Stage 10's b3new checks (as stage26/scripts/run_26.py)."""
    if task.get("check") != "b3new":
        return rs.run_check(task, wt, base, out)
    noise = rs.rs.strip_env_noise(wt)
    cdir = Path(str(out) + ".check")
    cmd = ["python3", str(E2E / "stage10-private" / "b3new" / "checks" / task["src"] / "check.py"), str(wt), str(cdir),
           "--reply", str(out) + ".reply.txt", "--base", base]
    p = rs.sh(cmd, env=rs.env_s11(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text((p.stdout + p.stderr).replace(str(wt), "<wt>"))
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def job_spec(job):
    """-> dict(kind, task (run_s11-style task dict or None), branch, mcp ('on'|'off'|'blocked'), prompts[list], fresh)"""
    t11 = all_tasks()
    parts = job.split(":")
    if parts[0] == "q1":
        t = t11[parts[1]]
        on = parts[2] == "on"
        return {"kind": "q1", "task": t, "branch": "s11-r" if on else t["base_branch"], "mcp": "on" if on else "off",
                "prompts": [t["prompt"]], "fresh": False}
    if parts[0] == "q2":
        req = requests_md().split("## Q2")[1].split("## Q5")[0]
        prompts = [l.strip()[2:] for l in req.splitlines() if l.strip().startswith("> ")]
        assert len(prompts) == 4
        t = {"id": "sq-mono", "repo": "sq-mono", "base_branch": "sq-a", "check": "none", "bundle": 0}
        return {"kind": "q2", "task": t, "branch": {"S": "sq-r", "SB": "sq-rb", "C": "sq-r"}[parts[1]], "mcp": "on",
                "prompts": prompts, "fresh": parts[1] == "C"}
    if parts[0] in ("rf", "rfc"):
        req = requests_md().split("## Q2")[1].split("## Q5")[0]
        prompts = [l.strip()[2:] for l in req.splitlines() if l.strip().startswith("> ")]
        assert len(prompts) == 4
        if parts[0] == "rf":
            tail = " For this task, use my local skill at `{CANARY_PATH}`."
            assert prompts[0].endswith(tail)
            prompts[0] = prompts[0][: -len(tail)]
        t = {"id": "sq-mono", "repo": "sq-mono", "base_branch": "sq-a", "check": "none", "bundle": 0}
        return {"kind": "q2" if parts[0] == "rfc" else "rf", "task": t, "branch": RF_BRANCH[parts[1]], "mcp": "on",
                "prompts": prompts, "fresh": False}
    if parts[0] == "lq":
        r = next(x for x in jl(SQ / "tasks-lq.jsonl") if x["id"] == f"lq-{parts[1]}")
        t = dict(t11[r["base_task"]])
        return {"kind": "lq", "task": t, "branch": "s11-r", "mcp": "on", "prompts": [r["first"], t["prompt"]], "fresh": False}
    if parts[0] == "q5":
        if parts[1].startswith("named-"):
            r = next(x for x in jl(SQ / "tasks-q5-named.jsonl") if x["id"] == f"q5-{parts[1]}")
            t = dict(t11[r["base_task"]])
            return {"kind": "q5n", "task": t, "branch": "s11-r", "mcp": "on", "prompts": [r["prompt"]], "fresh": False,
                    "named": r}
        import re
        row = next(l for l in requests_md().split("## Q5")[1].splitlines() if l.startswith(f"| {parts[1]} "))
        c = [x.strip() for x in re.split(r"(?<!\\)\|", row.strip().strip("|"))]
        repo = c[1].split()[0]
        base = c[1].split("`")[1]
        t = {"id": f"q5-{parts[1]}", "repo": repo, "base_branch": base, "check": "none", "bundle": 0, "stack": None,
             "ui": False}
        return {"kind": "q5t", "task": t, "branch": "s11-r", "mcp": "on", "prompts": [c[2].replace("\\|", "|")], "fresh": False}
    if parts[0] == "q6":
        t = t11[parts[1]]
        return {"kind": "q6", "task": t, "branch": "s11-r", "mcp": "blocked", "prompts": [t["prompt"]], "fresh": False}
    raise SystemExit(f"unknown job {job}")


def git(wt, *a, env=None, check=True):
    return subprocess.run(["git", "-C", str(wt), *a], capture_output=True, text=True, env=env, check=check).stdout.strip()


def snapshot(wt, idx):
    """Tree of the working tree (tracked + untracked, .gitignore respected) through a temporary index."""
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    git(wt, "read-tree", "HEAD", env=env)
    git(wt, "add", "-A", env=env)
    return git(wt, "write-tree", env=env)


def preflight_q(spec):
    probs = []
    v = rs.sh(["python3", str(E2E / "stage10" / "scripts" / "verify_index.py")])
    if v.returncode != 0:
        probs.append("index hash check failed")
    repo = E2E / "repos" / spec["task"]["repo"]
    if spec["branch"] != spec["task"]["base_branch"]:
        base = git(repo, "rev-parse", spec["task"]["base_branch"])
        if git(repo, "rev-parse", f"{spec['branch']}^", check=False) != base:
            probs.append(f"{spec['branch']} parent is not the start commit")
        if sorted(git(repo, "diff", "--name-only", base, spec["branch"], check=False).splitlines()) != \
                sorted([rs.ROUTER_PATH] + RF_FILES.get(spec["branch"], [])):
            probs.append(f"{spec['branch']} changes more than the router file")
    if (repo / rs.ROUTER_PATH).exists():
        probs.append("main checkout working tree has the router file")
    left = rs.leftover_processes()
    if left:
        probs.append(f"{len(left)} leftover process(es)")
    if spec["mcp"] == "blocked" and not (BLOCKED_VENV / "bin" / "skillfetch").exists():
        probs.append("blocked-server venv missing")
    return probs


def clone_q(repo, branch, wt):
    rs.sh(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", branch, str(repo), str(wt)], check=True)
    rs.sh(["git", "-C", str(wt), "branch", "-m", branch, "main"], check=True)
    rs.sh(["git", "-C", str(wt), "remote", "remove", "origin"], check=True)
    return {"refs": git(wt, "for-each-ref", "--format=%(refname)").split(), "head": git(wt, "rev-parse", "HEAD"),
            "router": (wt / rs.ROUTER_PATH).exists(), "status": git(wt, "status", "--porcelain", "--ignored"),
            "unreachable": len([l for l in git(wt, "fsck", "--unreachable", "--no-reflogs", check=False).splitlines() if l])}


def run_claude(cmd, wt, env, out):
    t0 = time.time()
    timed_out = False
    with open(str(out) + ".jsonl", "w") as fo, open(str(out) + ".stderr", "w") as fe, open("/dev/null") as fi:
        p = subprocess.Popen(cmd, cwd=wt, env=env, stdin=fi, stdout=subprocess.PIPE, stderr=fe, start_new_session=True)

        def pump():
            for line in p.stdout:
                fo.write(line.decode("utf-8", "replace"))
        th = threading.Thread(target=pump)
        th.start()
        try:
            rc = p.wait(timeout=rs.SESSION_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            timed_out = True
        th.join()
    procs = rs.cleanup_session_procs(wt, pgid=p.pid)
    ev = rs.result_event(str(out) + ".jsonl")
    sid = None
    for line in open(str(out) + ".jsonl", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            sid = d.get("session_id")
            break
    reply = (ev or {}).get("result") or ""
    Path(str(out) + ".reply.txt").write_text(rs.final_reply(str(out) + ".jsonl"))  # as run_s11 (fixed after the pilot)
    return {"exit_code": rc, "timed_out": timed_out, "wall_s": round(time.time() - t0, 1), "session_id": sid,
            "cost_usd": (ev or {}).get("total_cost_usd"), "num_turns": (ev or {}).get("num_turns"),
            "harness_fail": bool(ev) and bool(ev.get("is_error")) and any(m in reply.lower() for m in rs.LIMIT_MARKERS),
            "no_result": ev is None and not timed_out, "procs": procs}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    ctest = "--check-test" in sys.argv
    job, tag = args
    spec = job_spec(job)
    probs = preflight_q(spec)
    if probs:
        sys.exit("preflight failed: " + "; ".join(probs))
    sid = secrets.token_hex(6)
    wt = Q_ROOT / sid
    side = Q_ROOT / secrets.token_hex(6)  # canary skill and blocked-server HOME live here, outside the repo
    key = job.replace(":", "-")
    out_dir = PRIV / ("dryrun" if dry or ctest else "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{key}-{tag}"
    idx = Path(tempfile.mkdtemp(prefix="sqidx-")) / "index"
    task = spec["task"]
    try:
        Q_ROOT.mkdir(parents=True, exist_ok=True)
        cl = clone_q(E2E / "repos" / task["repo"], spec["branch"], wt)
        assert cl["refs"] == ["refs/heads/main"] and not cl["status"] and cl["unreachable"] == 0 and \
            cl["router"] == (spec["mcp"] != "off"), cl
        side.mkdir(parents=True)
        prompts = list(spec["prompts"])
        canary = None
        if "{CANARY_PATH}" in prompts[0]:  # q2, rfc, lq
            canary = side / "canary"
            shutil.copytree(CANARY_SRC, canary)
            prompts[0] = prompts[0].replace("{CANARY_PATH}", str(canary))
        if spec["mcp"] == "on":
            mcp = mcp_on()
        elif spec["mcp"] == "blocked":
            (side / "home").mkdir()
            mcp = mcp_blocked(side / "home")
        else:
            mcp = {"mcpServers": {}}
        mcp_file = Path(str(out) + ".mcp.json")
        mcp_file.write_text(json.dumps(mcp, indent=1))
        extra, prep_s = ({}, 0.0) if dry or task["repo"] == "sq-mono" else rs.prepare(task, wt, sid)
        env = rs.env_s11(extra)
        base_cmd = ["--output-format", "stream-json", "--verbose", "--include-hook-events", "--max-turns", MAX_TURNS,
                    "--allowedTools", rs.ALLOWED_TOOLS, "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(mcp_file)]
        snaps = [snapshot(wt, idx)]
        steps, session_id = [], None
        for k, prompt in enumerate(prompts, 1):
            pout = Path(f"{out}.p{k}") if len(prompts) > 1 else out
            cmd = ["claude", "-p", prompt] + base_cmd
            if k > 1 and not spec["fresh"]:
                cmd[3:3] = ["--resume", session_id or "<session-id-of-request-1>"]
            if dry or ctest:
                steps.append({"k": k, "cmd": [c if len(c) < 200 else c[:60] + "…" for c in cmd]})
                continue
            r = run_claude(cmd, wt, env, pout)
            if session_id is None or spec["fresh"]:
                session_id = r["session_id"]
            snaps.append(snapshot(wt, idx))
            Path(str(pout) + ".diff").write_text(git(wt, "diff", snaps[-2], snaps[-1]))
            new = git(wt, "diff", "--name-only", "--diff-filter=A", snaps[-2], snaps[-1]).splitlines()
            Path(str(pout) + ".new").write_text("\n".join(new))
            steps.append({"k": k, **{x: r[x] for x in r if x != "procs"}, "procs_killed": len(r["procs"]["killed"]),
                          "procs_remaining": len(r["procs"]["remaining"]), "snapshot": snaps[-1], "new_files": new})
            if r["harness_fail"] or r["no_result"]:
                break
        if len(prompts) > 1 and steps and not dry:  # the check reads <out>.reply.txt: the last request's reply
            last = Path(f"{out}.p{len(steps)}.reply.txt")
            if last.exists():
                Path(str(out) + ".reply.txt").write_text(last.read_text())
        check = None
        if not dry and task.get("check") not in (None, "none"):
            # base = the start commit at clone time; same steps as run_s11 (fixed after the pilot: collect_diff lives in
            # run_stage1, imported by run_s11 as rs; graft noise is stripped first)
            graft_removed = rs.strip_graft_noise(wt, cl["head"])
            diff = rs.rs.collect_diff(wt, cl["head"], out)
            check = run_check_q(task, wt, cl["head"], out)
            check["diff"] = diff
            check["graft_removed"] = graft_removed
        rs.cleanup_session_procs(wt)
        meta = {"job": job, "tag": tag, "kind": spec["kind"], "task": task.get("id"), "branch": spec["branch"], "mcp": spec["mcp"],
                "session_dir": str(wt), "side_dir": str(side), "canary": str(canary) if canary else None, "clone": cl,
                "prep_s": prep_s, "steps": steps, "check": check, "named": spec.get("named"),
                "harness_fail": any(s.get("harness_fail") for s in steps), "no_result": any(s.get("no_result") for s in steps),
                "cost_usd": round(sum(s.get("cost_usd") or 0 for s in steps), 4), "leftover_procs": rs.leftover_processes(),
                "index_ok_after": rs.sh(["python3", str(E2E / "stage10" / "scripts" / "verify_index.py")]).returncode == 0}
        Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(json.dumps({"job": job, "tag": tag, "dry_run": dry, "steps": len(steps), "cost_usd": meta["cost_usd"],
                          "harness_fail": meta["harness_fail"], "no_result": meta["no_result"],
                          "check": (check or {}).get("pass"), "leftover_procs": len(meta["leftover_procs"]),
                          "index_ok_after": meta["index_ok_after"]}))
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(side, ignore_errors=True)
        shutil.rmtree(idx.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
