"""Independent verification of the Stage 11 bundle (3) checks along the planned harness path (DESIGN §6): per run a
fresh `git clone --no-local --single-branch --branch s11-r`, branch renamed to `main`, `origin` removed, check called with --base <s11-r sha>.
Start state -> check must FAIL; with stage11-private/b3/ref/<t>.patch applied -> must PASS. Clones are removed after."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
PRIV = E2E / "stage11-private" / "b3"
OUT = PRIV / "verify"
OUT.mkdir(parents=True, exist_ok=True)
tasks = [json.loads(l) for l in (E2E / "stage11" / "tasks-b3.jsonl").open()]
res = {}
for t in tasks:
    repo = E2E / "repos" / t["repo"]
    base = subprocess.run(["git", "-C", str(repo), "rev-parse", t["cond_branch"]], capture_output=True, text=True, check=True).stdout.strip()
    for mode in ("start", "ref"):
        tmp = Path(tempfile.mkdtemp(prefix="s11v-"))
        wt = tmp / "w"
        subprocess.run(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", t["cond_branch"], str(repo), str(wt)], check=True)
        subprocess.run(["git", "-C", str(wt), "branch", "-m", t["cond_branch"], "main"], check=True)
        subprocess.run(["git", "-C", str(wt), "remote", "remove", "origin"], check=True)
        refs = subprocess.run(["git", "-C", str(wt), "for-each-ref", "--format=%(refname)"], capture_output=True, text=True).stdout.split()
        if mode == "ref":
            subprocess.run(["git", "-C", str(wt), "apply", str(PRIV / "ref" / f"{t['src']}.patch")], check=True)
        out = OUT / f"{t['id']}-{mode}"
        p = subprocess.run([sys.executable, str(PRIV / "checks" / t["src"] / "check.py"), str(wt), str(out), "--base", base],
                           capture_output=True, text=True)
        c = json.loads((out / "check.json").read_text())
        st = subprocess.run(["git", "-C", str(wt), "status", "--porcelain"], capture_output=True, text=True).stdout
        res[f"{t['id']} {mode}"] = {"pass": c["pass"], "failed": [i["name"] for i in c["items"] if not i["pass"]],
                                    "refs": refs, "status_after": st.splitlines()[:5], "stderr": p.stderr.strip()[-200:]}
        print(json.dumps({f"{t['id']} {mode}": res[f"{t['id']} {mode}"]}), flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
(OUT / "verify.json").write_text(json.dumps(res, indent=1))
ok = all(v["pass"] is (k.endswith(" ref")) and v["refs"] == ["refs/heads/main"] for k, v in res.items())
print("verify:", "OK" if ok else "PROBLEM")
