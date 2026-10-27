#!/usr/bin/env python3
"""Stage 14 task 3 check (API tests). Runs on the api/ subtree of the snapshot after the request (worktree = that tree,
git history: base commit = the api/ subtree before the request).
usage: check_apitests.py <worktree> <outdir> --base <commit>
Items (pass = a and b):
  a  the session's tests run and pass in api/ (pytest, own BOOKMARKS_DB per run)
  b  this request added tests: collected test count after > before (before = the base commit's tree, collected the same way)
Metrics (reported, not part of pass):
  c  mutants killed (0-8): for each mutant in mut_plugin.py the suite is run again with that mutant; killed = the suite
     fails under the mutant (the unmutated run passed)."""
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MUTANTS = ["not_found_200", "dup_allowed", "validation_off", "create_200", "delete_200", "limit_ignored", "tag_ignored",
           "offset_ignored"]


def sh(cmd, cwd, env=None, timeout=900):
    e = dict(os.environ, **(env or {}))
    try:
        p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, f"timeout: {exc}"


def collected(wt):
    with tempfile.TemporaryDirectory() as td:
        rc, out = sh(["uv", "run", "pytest", "-q", "--collect-only", "-p", "no:cacheprovider"], wt,
                     env={"BOOKMARKS_DB": str(Path(td) / "c.db")})
    m = re.search(r"(\d+) tests? collected", out) or re.search(r"collected (\d+) items?", out)
    if m:
        return int(m.group(1)), out
    return (0, out) if "no tests ran" in out or rc == 5 else (None, out)


def run(wt, mut=None):
    env = {"PYTHONPATH": str(HERE) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    args = ["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider"]
    if mut:
        env["S14_MUT"] = mut
        args += ["-p", "mut_plugin"]
    with tempfile.TemporaryDirectory() as td:
        env["BOOKMARKS_DB"] = str(Path(td) / "t.db")
        return sh(args, wt, env=env, timeout=600)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("out")
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    wt, out = Path(a.worktree), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, m = [], {}
    rc, txt = run(wt)
    (out / "pytest.log").write_text(txt[-20000:])
    n_after, ctxt = collected(wt)
    m["tests_after"] = n_after
    ok_a = rc == 0 and bool(n_after)
    items.append({"name": "a session's tests run and pass in api/", "pass": ok_a, "detail": f"rc={rc} collected={n_after}"})
    with tempfile.TemporaryDirectory() as td:
        base_wt = Path(td) / "base"
        subprocess.run(["git", "-C", str(wt), "worktree", "add", "-q", "--detach", str(base_wt), a.base], check=True,
                       capture_output=True)
        n_before, _ = collected(base_wt)
        subprocess.run(["git", "-C", str(wt), "worktree", "remove", "--force", str(base_wt)], capture_output=True)
    m["tests_before"] = n_before
    items.append({"name": "b this request added tests (collected after > before)",
                  "pass": n_after is not None and (n_before or 0) < n_after, "detail": f"before={n_before} after={n_after}"})
    kills = {}
    if ok_a:
        for k in MUTANTS:
            rck, tk = run(wt, k)
            kills[k] = rck != 0
            (out / f"mut-{k}.log").write_text(tk[-6000:])
    m["mutants"] = kills
    m["mutants_killed"] = sum(kills.values()) if ok_a else None
    res = {"task_id": "s14-apitests", "pass": all(i["pass"] for i in items), "items": items, "metrics": m}
    (out / "check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({"pass": res["pass"], "killed": m["mutants_killed"], "before": n_before, "after": n_after}))


if __name__ == "__main__":
    main()
