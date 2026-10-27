#!/usr/bin/env python3
"""Stage 13 runner (stage13/DESIGN.md §2): the Stage Q harness (stageQ/scripts/run_q.py) unchanged, with one job added:
  p:<task>   condition P: branch s13-p-<start branch> = the task's start commit + one commit "chore: add project skills"
             adding the 8 popular skills under .claude/skills/<name>/ (stage13-private/p-skills, hashes in
             p-skills-manifest.json); no router, no MCP (mcp-none); prompt, prepare() and check as the task's q1 job
Output root: stage13-private (SQ_PRIV). Preflight for p: the generic run_q checks (index hashes, leftover processes,
router file not in the main checkout), plus: branch parent = start commit, the branch adds exactly the 143 skill files,
each blob's sha256 equals the manifest, commit message "chore: add project skills".
A·R m3 for the six Q1 tasks run with run_q.py itself (q1:<task>:on|off m3, output stageQ-private).
usage: run_13.py p:<task> <tag> [--dry-run | --check-test]"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
E2E = S13.parent
os.environ["SQ_PRIV"] = str(E2E / "stage13-private")
sys.path.insert(0, str(E2E / "stageQ" / "scripts"))
import run_q as q  # noqa: E402

MAN = json.loads((E2E / "stage13-private" / "p-skills-manifest.json").read_text())
WANT = {f".claude/skills/{m['name']}/{rel}": sha for m in MAN for rel, sha in m["sha256"].items()}
_spec, _pre = q.job_spec, q.preflight_q


def job_spec(job):
    parts = job.split(":")
    if parts[0] == "p":
        t = q.all_tasks()[parts[1]]
        return {"kind": "p", "task": t, "branch": f"s13-p-{t['base_branch']}", "mcp": "off", "prompts": [t["prompt"]],
                "fresh": False}
    return _spec(job)


def preflight_q(spec):
    if spec["kind"] != "p":
        return _pre(spec)
    probs = _pre({**spec, "branch": spec["task"]["base_branch"]})  # generic checks; the router-branch check does not apply
    repo = E2E / "repos" / spec["task"]["repo"]
    base = q.git(repo, "rev-parse", spec["task"]["base_branch"])
    br = spec["branch"]
    if q.git(repo, "rev-parse", f"{br}^", check=False) != base:
        probs.append(f"{br} parent is not the start commit")
    changed = sorted(q.git(repo, "diff", "--name-only", base, br, check=False).splitlines())
    if changed != sorted(WANT):
        probs.append(f"{br} changes {len(changed)} files, expected the {len(WANT)} skill files")
    else:
        for path, sha in WANT.items():
            blob = subprocess.run(["git", "-C", str(repo), "show", f"{br}:{path}"], capture_output=True).stdout
            if hashlib.sha256(blob).hexdigest() != sha:
                probs.append(f"{br}:{path} sha256 mismatch")
                break
    if q.git(repo, "log", "-1", "--format=%s", br, check=False) != "chore: add project skills":
        probs.append(f"{br} commit message")
    return probs


q.job_spec, q.preflight_q = job_spec, preflight_q
q.PRIV = Path(os.environ["SQ_PRIV"])

if __name__ == "__main__":
    q.main()
