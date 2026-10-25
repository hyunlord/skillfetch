#!/usr/bin/env python3
"""Frozen objective checks for stage 2. usage: check_s2.py <task_id> <worktree> <out_dir> --base <commit>
Writes <out_dir>/check.json {task_id, pass, items[{name, pass, detail}], metrics{...}} and logs/. Never edits the
session's files except: s2-data reruns the script (out/ is regenerated; the session's own out/ is copied first)."""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sh(cmd, cwd, env=None, timeout=900):
    import os
    e = dict(os.environ)
    for k in list(e):
        if k in ("VIRTUAL_ENV", "UV", "CLAUDECODE") or k.startswith("CLAUDE_CODE"):
            e.pop(k)
    e.update(env or {})
    try:
        p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, f"timeout {timeout}s: {exc}"


def junit(path):
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    t = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    t["passed"] = t["tests"] - t["failures"] - t["errors"] - t["skipped"]
    return t


def log(out, name, text):
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / f"{name}.log").write_text(text)


def check_tests(wt, out, base):
    items, m = [], {}
    rc, txt = sh(["git", "status", "--porcelain", "--", "src/recur"], wt)
    rc2, _ = sh(["git", "diff", "--quiet", base, "--", "src/recur"], wt)
    untouched = rc2 == 0 and not txt.strip()
    m["module_modified"] = not untouched
    items.append({"name": "src/recur unchanged", "pass": untouched, "detail": txt.strip()[:300]})
    rc, txt = sh(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "--cov=recur", "--cov-branch",
                  f"--cov-report=json:{out / 'cov.json'}", f"--junitxml={out / 'junit.xml'}"], wt)
    log(out, "pytest", txt)
    j = junit(out / "junit.xml")
    m["junit"] = j
    if (out / "cov.json").exists():
        cov = json.loads((out / "cov.json").read_text())
        f = next((v for k, v in cov["files"].items() if k.endswith("recur/rules.py")), None)
        if f:
            s = f["summary"]
            m["rules_line_pct"] = round(100 * s["covered_lines"] / s["num_statements"], 2) if s["num_statements"] else None
            m["rules_branch_pct"] = round(100 * s["covered_branches"] / s["num_branches"], 2) if s.get("num_branches") else None
            m["rules_combined_pct"] = round(s["percent_covered"], 2)
    ok = j is not None and j["tests"] > 0 and j["failures"] == 0 and j["errors"] == 0
    items.append({"name": "session's tests run and pass", "pass": ok, "detail": json.dumps(j)})
    return items, m


def check_api(wt, out, base):
    items, m = [], {}
    with tempfile.TemporaryDirectory() as td:
        rc, txt = sh(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={out / 'junit.xml'}"], wt,
                     env={"BOOKMARKS_DB": str(Path(td) / "own-tests.db")})
    log(out, "pytest", txt)
    j = junit(out / "junit.xml")
    m["junit"] = j
    items.append({"name": "session's tests run and pass", "pass": j is not None and j["tests"] > 0 and j["failures"] == 0 and j["errors"] == 0,
                  "detail": json.dumps(j)})
    contract = []
    with tempfile.TemporaryDirectory() as td:
        db = str(Path(td) / "contract.db")
        for phase in ("phase1", "phase2"):
            rc, txt = sh(["uv", "run", "python", str(HERE / "api_contract.py"), str(wt), phase], wt, env={"BOOKMARKS_DB": db}, timeout=300)
            log(out, f"contract-{phase}", txt)
            for line in txt.splitlines():
                if line.startswith("{"):
                    try:
                        contract.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    m["contract"] = contract
    m["contract_pass"] = sum(1 for c in contract if c["pass"])
    m["contract_total"] = 27  # 26 calls in phase 1 + 1 in phase 2
    items.append({"name": f"contract script {m['contract_pass']}/{m['contract_total']}", "pass": m["contract_pass"] == m["contract_total"],
                  "detail": "; ".join(c["name"] for c in contract if not c["pass"])[:500]})
    return items, m


def check_docs(wt, out, base):
    items, m = [], {}
    readme = next((p for p in wt.iterdir() if p.name.lower() == "readme.md"), None)
    m["readme_words"] = len(readme.read_text(errors="replace").split()) if readme else 0
    items.append({"name": "README.md at the repo root", "pass": readme is not None and m["readme_words"] > 0, "detail": str(m["readme_words"])})
    rc, txt = sh(["git", "ls-files", "--others", "--exclude-standard"], wt)
    rc2, txt2 = sh(["git", "diff", "--name-only", base], wt)
    changed = sorted(set(txt.split()) | set(txt2.split()))
    m["changed_files"] = changed
    m["doc_files"] = [p for p in changed if p.lower().endswith((".md", ".mdx", ".txt"))]
    m["non_doc_changes"] = [p for p in changed if p not in m["doc_files"]]
    scripts = set(json.loads((wt / "package.json").read_text()).get("scripts", {}))
    refs = set()
    for p in m["doc_files"]:
        t = (wt / p).read_text(errors="replace") if (wt / p).exists() else ""
        refs |= set(re.findall(r"\b(?:npm run|yarn|pnpm(?: run)?|bun run)\s+([A-Za-z][\w:-]*)", t))
    builtin = {"install", "add", "dlx", "create", "exec", "i", "ci", "start", "test"}
    m["scripts_referenced"] = sorted(refs)
    m["scripts_missing"] = sorted(r for r in refs if r not in scripts and r not in builtin)
    items.append({"name": "npm scripts named in the docs exist in package.json", "pass": not m["scripts_missing"], "detail": ", ".join(m["scripts_missing"])})
    rc, txt = sh(["npm", "run", "build"], wt, timeout=600)
    log(out, "build", txt)
    items.append({"name": "npm run build still passes", "pass": rc == 0, "detail": f"rc={rc}"})
    return items, m


def check_data(wt, out, base):
    items, m = [], {}
    script = wt / "scripts" / "clean_orders.py"
    items.append({"name": "scripts/clean_orders.py exists", "pass": script.exists(), "detail": ""})
    if (wt / "out").exists():
        shutil.copytree(wt / "out", out / "session_out")
        shutil.rmtree(wt / "out")
    rc, txt = sh(["uv", "run", "python", "scripts/clean_orders.py"], wt, timeout=600)
    log(out, "run", txt)
    m["run_rc"] = rc
    produced = sorted(str(p.relative_to(wt / "out")) for p in (wt / "out").rglob("*") if p.is_file()) if (wt / "out").exists() else []
    m["outputs"] = produced
    if (wt / "out").exists():
        shutil.copytree(wt / "out", out / "out")
    items.append({"name": "uv run python scripts/clean_orders.py exits 0", "pass": rc == 0, "detail": txt[-300:]})
    has_csv = any(p.endswith(".csv") for p in produced)
    has_report = any(p.endswith((".md", ".txt", ".json", ".html")) for p in produced)
    items.append({"name": "out/ has a cleaned CSV and a report", "pass": has_csv and has_report, "detail": ", ".join(produced)[:300]})
    rc2, txt2 = sh(["git", "diff", "--quiet", base, "--", "data/orders.csv"], wt)
    items.append({"name": "data/orders.csv unchanged", "pass": rc2 == 0, "detail": ""})
    tests = list(wt.glob("tests/**/*.py")) + list(wt.glob("test_*.py"))
    if tests:
        rc3, txt3 = sh(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={out / 'junit.xml'}"], wt)
        log(out, "pytest", txt3)
        m["junit"] = junit(out / "junit.xml")
    return items, m


CHECKS = {"s2-tests": check_tests, "s2-api": check_api, "s2-docs": check_docs, "s2-data": check_data}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id")
    ap.add_argument("worktree")
    ap.add_argument("out")
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, metrics = CHECKS[a.task_id](Path(a.worktree), out, a.base)
    res = {"task_id": a.task_id, "pass": all(i["pass"] for i in items), "items": items, "metrics": metrics}
    (out / "check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(a.task_id, res["pass"], [(i["name"], i["pass"]) for i in items])


if __name__ == "__main__":
    main()
