"""Independent verification of the new bundle (3) checks through the harness path (run_s10.prepare / run_check):
fresh worktree at s10-a -> check must FAIL; with stage10-private/b3new/ref/<t>.patch applied -> must PASS."""
import json, sys
from pathlib import Path
sys.path.insert(0, "<e2e>/stage10/scripts")
import run_s10 as r
OUT = r.PRIV / "b3new" / "verify"
res = {}
for tid in ("s10-t001", "s10-t033", "s10-t114"):
    t = r.load_task(tid)
    repo = r.E2E / "repos" / t["repo"]
    base = r.sh(["git", "-C", str(repo), "rev-parse", "s10-a"], check=True).stdout.strip()
    for mode in ("start", "ref"):
        wt = r.WT_ROOT / f"verify-{tid}-{mode}"
        r.prepare(t, repo, wt, base, f"verify-{tid}-{mode}")
        if mode == "ref":
            ap = r.sh(["git", "apply", str(r.PRIV / "b3new" / "ref" / f"{t['src']}.patch")], cwd=wt)
            assert ap.returncode == 0, ap.stderr
        out = OUT / f"{tid}-{mode}"
        out.parent.mkdir(parents=True, exist_ok=True)
        c = r.run_check(t, wt, base, out)
        st = r.sh(["git", "status", "--porcelain"], cwd=wt).stdout
        res[f"{tid} {mode}"] = {"pass": c.get("pass"), "failed": [i["name"] for i in c.get("items", []) if not i["pass"]], "error": c.get("error"), "status_after": st.splitlines()[:5]}
        with r.repo_lock(repo):
            r.sh(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
        print(json.dumps({f"{tid} {mode}": res[f"{tid} {mode}"]}), flush=True)
(OUT / "verify.json").write_text(json.dumps(res, indent=1))
