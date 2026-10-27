#!/usr/bin/env python3
"""Stage 14 runner (stage14/DESIGN.md §3). One session = six requests on repos/s14-mono: the first with `claude -p`, the
rest with `claude -p --resume <session id>` in the same working tree (Stage Q2 S way). Reuses the Stage Q / Stage 11 harness
(stageQ/scripts/run_q.py, stage11/scripts/run_s11.py): --no-local single-branch clone renamed to main with origin removed,
random session directory, preflight (index hashes, leftover processes), process cleanup, E1 flags, --max-turns 40 per
request.
Job: s14:<A|P|R>:<F|B>. Branches: A s14-a; P s14-p (s14-a + the 8 Stage 13 P skills, 143 files, hashes in
stage13-private/p-skills-manifest.json, message "chore: add project skills"); R s14-r (s14-a + the deployed router,
sha256 3efef1e0…, message "chore: add project skill"). MCP: R = skillfetch serve (server 3fef3f8 venv, index = Stage 10
staging-4 copy, equal to the release index); A, P = none.
Requests: stage14/requests.md; order F = 1 2 3 4 5 6, B = 6 5 4 2 3 1.
Before request 1 (all conditions alike): npm ci in web/, uv sync in api/ and data/, cargo build --all-targets in media/.
After every request: a snapshot of the tree (temporary index, no commit or ref in the session's repo) and the diff from the
previous snapshot. After the session: per request, its task's hidden check on a separate repository built from the
snapshots (commit 1 = the area's subtree before the request, commit 2 = after; the area is web/, api/, media/ or data/, the
whole tree for the README task), so the frozen checks run as in their source stage:
  1 landing   stage6/6b/checks/check_6b.py d1-landing        (web/)
  2 api       stage2/checks/check_s2.py s2-api                (api/)
  3 apitests  stage14-private/checks/check_apitests.py         (api/)
  4 rust      stage11-private/b4/checks/t266/check.py, --reply = that request's reply   (media/)
  5 docs      stage14-private/checks/check_docs14.py           (whole tree)
  6 data      stage2/checks/check_s2.py s2-data               (data/)
Output: stage14-private/runs/<A|P|R>-<F|B>-<tag>.p<k>.{jsonl,reply.txt,diff,new,stderr} (k = position in the session),
.p<k>.check/, <...>.meta.json (steps: task id, area, position, cost, turns, snapshot; checks per task).
usage: run_14.py s14:<cond>:<order> <tag> [--dry-run]"""
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
PRIV = E2E / "stage14-private"
os.environ["SQ_PRIV"] = str(PRIV)
sys.path.insert(0, str(E2E / "stageQ" / "scripts"))
import run_q as q  # noqa: E402

rs = q.rs
REPO = E2E / "repos" / "s14-mono"
BRANCH = {"A": "s14-a", "P": "s14-p", "R": "s14-r"}
ROUTER_SHA = "3efef1e0b7cf5181fa1911f4ebd075cb5d8b8865926d6353399221392bf8f040"
ORDER = {"F": [1, 2, 3, 4, 5, 6], "B": [6, 5, 4, 2, 3, 1]}
TASKS = {1: ("landing", "web"), 2: ("api", "api"), 3: ("apitests", "api"), 4: ("rust", "media"), 5: ("docs", ""), 6: ("data", "data")}
MAN = json.loads((E2E / "stage13-private" / "p-skills-manifest.json").read_text())
P_WANT = {f".claude/skills/{m['name']}/{rel}": sha for m in MAN for rel, sha in m["sha256"].items()}
CHK = E2E / "stage14-private" / "checks"
LOCK = PRIV / "runs" / "screenshot.lock"


def requests():
    text = (S14 / "requests.md").read_text()
    out = {}
    for m in re.finditer(r"^## (\d) \w+ \(\w+\)\n((?:> .*\n?)+)", text, re.M):
        out[int(m.group(1))] = "\n".join(l[2:] for l in m.group(2).strip().splitlines())
    assert sorted(out) == [1, 2, 3, 4, 5, 6], out.keys()
    return out


def preflight(cond):
    probs = []
    if rs.sh(["python3", str(E2E / "stage10" / "scripts" / "verify_index.py")]).returncode != 0:
        probs.append("index hash check failed")
    base = q.git(REPO, "rev-parse", "s14-a")
    if cond != "A":
        br = BRANCH[cond]
        if q.git(REPO, "rev-parse", f"{br}^", check=False) != base:
            probs.append(f"{br} parent is not s14-a")
        changed = sorted(q.git(REPO, "diff", "--name-only", base, br, check=False).splitlines())
        want = sorted(P_WANT) if cond == "P" else [rs.ROUTER_PATH]
        if changed != want:
            probs.append(f"{br} changes {len(changed)} files, expected {len(want)}")
        else:
            shas = P_WANT if cond == "P" else {rs.ROUTER_PATH: ROUTER_SHA}
            for path, sha in shas.items():
                blob = subprocess.run(["git", "-C", str(REPO), "show", f"{br}:{path}"], capture_output=True).stdout
                if hashlib.sha256(blob).hexdigest() != sha:
                    probs.append(f"{br}:{path} sha256 mismatch")
                    break
        msg = "chore: add project skills" if cond == "P" else "chore: add project skill"
        if q.git(REPO, "log", "-1", "--format=%s", br, check=False) != msg:
            probs.append(f"{br} commit message")
    if (REPO / ".claude").exists():
        probs.append("main checkout working tree has .claude/")
    left = rs.leftover_processes()
    if left:
        probs.append(f"{len(left)} leftover process(es)")
    return probs


def prepare_mono(wt):
    env = rs.child_env()
    rs.sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=wt / "web", env=env, check=True, timeout=900)
    for d in ("api", "data"):
        rs.sh(["uv", "sync", "-q"], cwd=wt / d, env=env, check=True, timeout=900)
    rs.sh(["cargo", "build", "--all-targets", "-q"], cwd=wt / "media", env=env, timeout=1800)


def check_repo(wt, trees, area, dest):
    """dest: a git repo with commit 1 = <area> of trees[0], commit 2 = <area> of trees[1] (checked out). -> base sha"""
    dest.mkdir(parents=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="e2e", GIT_AUTHOR_EMAIL="e2e@local", GIT_COMMITTER_NAME="e2e",
               GIT_COMMITTER_EMAIL="e2e@local", GIT_AUTHOR_DATE="2026-10-27T12:00:00+0900", GIT_COMMITTER_DATE="2026-10-27T12:00:00+0900")
    subprocess.run(["git", "init", "-q", "-b", "main", str(dest)], check=True)
    shas = []
    for i, tree in enumerate(trees):
        for p in dest.iterdir():
            if p.name != ".git":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        spec = f"{tree}:{area}" if area else tree
        arch = subprocess.run(["git", "-C", str(wt), "archive", spec], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(dest)], input=arch, check=True)
        subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(dest), "commit", "-q", "--allow-empty", "-m", ["before", "after"][i]], check=True, env=env)
        shas.append(q.git(dest, "rev-parse", "HEAD"))
    return shas[0]


def run_task_check(task_no, chk, base, cdir, reply):
    name = TASKS[task_no][0]
    if name == "landing":
        cmd = ["python3", str(E2E / "stage6" / "6b" / "checks" / "check_6b.py"), "d1-landing", str(chk), str(cdir), "--pg", rs.PG,
               "--lock", str(LOCK), "--base", base]
    elif name in ("api", "data"):
        cmd = ["python3", str(E2E / "stage2" / "checks" / "check_s2.py"), f"s2-{name}", str(chk), str(cdir), "--base", base]
    elif name == "apitests":
        cmd = ["python3", str(CHK / "check_apitests.py"), str(chk), str(cdir), "--base", base]
    elif name == "rust":
        cmd = ["python3", str(E2E / "stage11-private" / "b4" / "checks" / "t266" / "check.py"), str(chk), str(cdir),
               "--reply", str(reply), "--base", base]
    else:
        cmd = ["python3", str(CHK / "check_docs14.py"), str(chk), str(cdir), "--base", base]
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    noise = rs.rs.strip_env_noise(chk)
    p = rs.sh(cmd, env=rs.env_s11(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text((p.stdout + p.stderr).replace(str(chk), "<chk>"))
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    job, tag = args
    _, cond, order = job.split(":")
    assert cond in BRANCH and order in ORDER, job
    probs = preflight(cond)
    if probs:
        sys.exit("preflight failed: " + "; ".join(probs))
    reqs = requests()
    sid = secrets.token_hex(6)
    wt = q.Q_ROOT / sid
    out_dir = PRIV / ("dryrun" if dry else "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{cond}-{order}-{tag}"
    tmp = Path(tempfile.mkdtemp(prefix="s14-"))
    idx = tmp / "index"
    try:
        q.Q_ROOT.mkdir(parents=True, exist_ok=True)
        cl = q.clone_q(REPO, BRANCH[cond], wt)
        assert cl["refs"] == ["refs/heads/main"] and not cl["status"] and cl["unreachable"] == 0 and cl["router"] == (cond == "R"), cl
        mcp = q.mcp_on() if cond == "R" else {"mcpServers": {}}
        mcp_file = Path(str(out) + ".mcp.json")
        mcp_file.write_text(json.dumps(mcp, indent=1))
        prep_s = 0.0
        if not dry:
            import time
            t0 = time.time()
            prepare_mono(wt)
            prep_s = round(time.time() - t0, 1)
        env = rs.env_s11({})
        base_cmd = ["--output-format", "stream-json", "--verbose", "--include-hook-events", "--max-turns", q.MAX_TURNS,
                    "--allowedTools", rs.ALLOWED_TOOLS, "--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(mcp_file)]
        snaps = [q.snapshot(wt, idx)]
        steps, session_id = [], None
        for k, tno in enumerate(ORDER[order], 1):
            pout = Path(f"{out}.p{k}")
            cmd = ["claude", "-p", reqs[tno]] + base_cmd
            if k > 1:
                cmd[3:3] = ["--resume", session_id or "<session-id-of-request-1>"]
            if dry:
                steps.append({"k": k, "task": TASKS[tno][0], "cmd": [c if len(c) < 200 else c[:60] + "…" for c in cmd]})
                continue
            r = q.run_claude(cmd, wt, env, pout)
            if session_id is None:
                session_id = r["session_id"]
            snaps.append(q.snapshot(wt, idx))
            Path(str(pout) + ".diff").write_text((lambda d: d + "\n" if d else d)(q.git(wt, "diff", snaps[-2], snaps[-1])))
            new = q.git(wt, "diff", "--name-only", "--diff-filter=A", snaps[-2], snaps[-1]).splitlines()
            Path(str(pout) + ".new").write_text("\n".join(new))
            steps.append({"k": k, "task_no": tno, "task": TASKS[tno][0], "area": TASKS[tno][1] or "(root)",
                          **{x: r[x] for x in r if x != "procs"}, "procs_killed": len(r["procs"]["killed"]),
                          "procs_remaining": len(r["procs"]["remaining"]), "snapshot": snaps[-1], "new_files": new})
            if r["harness_fail"] or r["no_result"]:
                break
        rs.cleanup_session_procs(wt)
        checks = {}
        if not dry:
            for s in steps:
                k, tno = s["k"], s["task_no"]
                chk = tmp / f"chk{k}"
                base = check_repo(wt, [snaps[k - 1], snaps[k]], TASKS[tno][1], chk)
                res = run_task_check(tno, chk, base, Path(f"{out}.p{k}.check"), Path(f"{out}.p{k}.reply.txt"))
                checks[TASKS[tno][0]] = {"k": k, "pass": res.get("pass"), "items": res.get("items"), "metrics": res.get("metrics"),
                                         "undecidable": res.get("undecidable"), "error": res.get("error")}
                rs.cleanup_session_procs(chk)
                shutil.rmtree(chk, ignore_errors=True)
        meta = {"job": job, "tag": tag, "cond": cond, "order": order, "branch": BRANCH[cond], "session_dir": str(wt), "clone": cl,
                "prep_s": prep_s, "steps": steps, "checks": checks, "session_id": session_id,
                "harness_fail": any(s.get("harness_fail") for s in steps), "no_result": any(s.get("no_result") for s in steps),
                "complete": len(steps) == 6, "cost_usd": round(sum(s.get("cost_usd") or 0 for s in steps), 4),
                "leftover_procs": rs.leftover_processes(),
                "index_ok_after": rs.sh(["python3", str(E2E / "stage10" / "scripts" / "verify_index.py")]).returncode == 0}
        Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(json.dumps({"job": job, "tag": tag, "dry_run": dry, "steps": len(steps), "cost_usd": meta["cost_usd"],
                          "harness_fail": meta["harness_fail"], "no_result": meta["no_result"],
                          "checks": {t: c["pass"] for t, c in checks.items()}, "leftover_procs": len(meta["leftover_procs"]),
                          "index_ok_after": meta["index_ok_after"]}))
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
