#!/usr/bin/env python3
"""Re-run the (revised) objective check of a finished stage 10 session from its saved diff and final reply:
fresh worktree at the session's base, `git apply <out>.diff`, graft-noise strip, check -> <out>.recheck.check/, summary <out>.recheck.json.
Also writes <out>.recheck.diff (the diff collected again after the strip). usage: recheck_s10.py <env> <cond> <task> <tag>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_s10 as r  # noqa: E402

env, cond, task_id, tag = sys.argv[1:5]
out = r.PRIV / "runs" / env / cond / f"{task_id}-{tag}"
meta = json.loads(Path(str(out) + ".meta.json").read_text())
task = r.load_task(task_id)
repo = r.E2E / "repos" / task["repo"]
wt = r.WT_ROOT / f"recheck-{env}-{cond}-{task_id}-{tag}"
r.prepare(task, repo, wt, meta["base"], f"recheck-{env}-{cond}-{task_id}-{tag}")
ap = r.sh(["git", "apply", "--whitespace=nowarn", str(out) + ".diff"], cwd=wt)
assert ap.returncode == 0, ap.stderr
reply = Path(str(out) + ".reply.txt")
if not reply.exists():
    reply.write_text(r.final_reply(str(out) + ".jsonl"))
graft = r.strip_graft_noise(wt, meta["base"])
rec = Path(str(out) + ".recheck")
Path(str(rec) + ".reply.txt").write_text(reply.read_text())
diff = r.rs.collect_diff(wt, meta["base"], rec)
res = r.run_check(task, wt, meta["base"], rec)
res["graft_removed"] = graft
res["diff_files"] = [f["file"] for f in diff["files"]]
Path(str(rec) + ".json").write_text(json.dumps(res, indent=1))
with r.repo_lock(repo):
    r.sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
print(json.dumps({"env": env, "cond": cond, "task": task_id, "pass": res.get("pass"),
                  "items": [(i["name"][:60], i["pass"], i["detail"][:160]) for i in res.get("items", [])],
                  "graft_removed": [g["path"] for g in graft], "diff_files": res["diff_files"]}, ensure_ascii=False))
