#!/usr/bin/env python3
"""stage2/blind-p<N>/<task>/: one blind set per domain and judging pass, new random codes per pass.
  <code>/diff.patch   the session's diff (lockfiles, env noise excluded), condition-revealing words redacted
  <code>/check.txt    the frozen check's objective results (no condition, no timing)
  <code>/out/         s2-data only: files the check produced by running the script in the worktree
  _context/           shared by the whole set: module source (tests), repo sources (docs), raw CSV (data)
Mapping: stage2/blind-key-p<N>.jsonl (outside the blind folders). Uniform mtimes. Prints counts only.
usage: build_blind_s2.py <pass number>"""
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path

S2 = Path(__file__).resolve().parents[1]
E2E = S2.parent
LEAK = re.compile(r"(?i)skillfetch|search_skills|resolve_set|load_skills|profile_repo|python-testing-patterns|"
                  r"fastapi-templates|data-analyst-engine|\bquill\b|\bradar\b|<E2 plugin>|router skill|"
                  r"precedence header|\bskills?\b")
SKIP = re.compile(r"(^|/)(package-lock\.json|uv\.lock|bun\.lock|\.ignore)$|(^|/)\.omc/|(^|/)graft/|\.db$|(^|/)out/")
GRAFT = {"+", "+# graft's local graph cache — regenerable, not committed (run `graft build`).", "+/graft/"}
CONTEXT = {"s2-tests": ["src/recur/rules.py", "src/recur/__init__.py", "pyproject.toml"],
           "s2-api": [],
           "s2-docs": ["package.json", "tsconfig.json", ".gitignore", "components/Layout.tsx", "components/List.tsx",
                       "components/ListDetail.tsx", "components/ListItem.tsx", "interfaces/index.ts", "pages/about.tsx",
                       "pages/api/users/index.ts", "pages/index.tsx", "pages/users/[id].tsx", "pages/users/index.tsx",
                       "utils/sample-data.ts"],
           "s2-data": ["data/orders.csv", "pyproject.toml"]}


def redact(text):
    n = len(LEAK.findall(text))
    return LEAK.sub("[redacted]", text), n


def clean_diff(path):
    out = []
    for ch in re.split(r"(?=^diff --git )", path.read_text(errors="replace"), flags=re.M):
        if not ch.startswith("diff --git"):
            continue
        p = re.match(r"diff --git a/(.*?) b/(.*)$", ch.split("\n", 1)[0]).group(2)
        if SKIP.search(p):
            continue
        lines = [ln for ln in ch.split("\n") if not ln.startswith("index ")]
        if p == ".gitignore":
            lines = [ln for ln in lines if ln not in GRAFT]
            if not any(ln[:1] in "+-" and not ln.startswith(("+++", "---")) for ln in lines):
                continue
        out.append("\n".join(lines))
    return "".join(out)


def check_text(task, check):
    m = check.get("metrics", {})
    L = [f"objective check ({task}), frozen before the runs", ""]
    for i in check.get("items", []):
        L.append(f"- {'PASS' if i['pass'] else 'FAIL'}: {i['name']}" + (f" — {i['detail']}" if i.get("detail") and not i["pass"] else ""))
    if m.get("junit"):
        j = m["junit"]
        L.append(f"- the session's own tests: {j['passed']} passed, {j['failures']} failed, {j['errors']} errors, {j['skipped']} skipped (of {j['tests']})")
    if task == "s2-tests":
        L.append(f"- coverage of src/recur/rules.py: lines {m.get('rules_line_pct')}%, branches {m.get('rules_branch_pct')}%")
        L.append(f"- rules.py modified by the session: {m.get('module_modified')}")
    if task == "s2-api":
        L.append(f"- contract script (spec from the prompt): {m.get('contract_pass')}/{m.get('contract_total')} calls as specified")
        for c in m.get("contract", []):
            L.append(f"  - {'ok  ' if c['pass'] else 'FAIL'} {c['name']}" + ("" if c["pass"] else f" — got {c['detail'][:120]}"))
    if task == "s2-docs":
        L.append(f"- README words: {m.get('readme_words')}; doc files added/changed: {', '.join(m.get('doc_files', []))}")
        L.append(f"- non-doc files changed: {', '.join(m.get('non_doc_changes', [])) or 'none'}")
        L.append(f"- npm scripts named in the docs: {', '.join(m.get('scripts_referenced', [])) or 'none'}; missing from package.json: {', '.join(m.get('scripts_missing', [])) or 'none'}")
    if task == "s2-data":
        L.append(f"- `uv run python scripts/clean_orders.py` exit code {m.get('run_rc')}; files written to out/: {', '.join(m.get('outputs', []))}")
    return redact("\n".join(L) + "\n")[0]


def main():
    n = int(sys.argv[1])
    root, keyf = S2 / f"blind-p{n}", S2 / f"blind-key-p{n}.jsonl"
    assert not root.exists() and not keyf.exists(), "already built"
    rows = json.loads((S2 / "runs" / "_extract.json").read_text())
    rng = random.SystemRandom()
    keys, red = [], 0
    for task in ("s2-tests", "s2-api", "s2-docs", "s2-data"):
        sel = [r for r in rows if r["task_id"] == task]
        rng.shuffle(sel)
        tdir = root / task
        ctx = tdir / "_context"
        ctx.mkdir(parents=True)
        repo = E2E / "repos" / task
        for rel in CONTEXT[task]:
            (ctx / rel).parent.mkdir(parents=True, exist_ok=True)
            data = os.popen(f"git -C '{repo}' show s2-a:'{rel}'").read()
            (ctx / rel).write_text(data)
        for r in sel:
            code = secrets.token_hex(4)
            d = tdir / code
            d.mkdir()
            runs = S2 / "runs" / r["cond"]
            diff, k = redact(clean_diff(runs / f"{r['name']}.diff"))
            red += k
            (d / "diff.patch").write_text(diff)
            (d / "check.txt").write_text(check_text(task, r["check"]))
            outdir = runs / f"{r['name']}.check" / "out"
            if task == "s2-data" and outdir.exists():
                for f in sorted(outdir.rglob("*")):
                    if f.is_file():
                        dst = d / "out" / f.relative_to(outdir)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if f.stat().st_size > 400_000:  # keep the head of very large outputs
                            dst.write_bytes(f.read_bytes()[:400_000])
                        else:
                            txt = f.read_text(errors="replace") if f.suffix in (".md", ".txt", ".json", ".html", ".csv") else None
                            if txt is not None:
                                txt, k = redact(txt)
                                red += k
                                dst.write_text(txt)
                            else:
                                shutil.copyfile(f, dst)
            keys.append({"code": code, "task": task, "cond": r["cond"], "rep": r["rep"], "name": r["name"]})
    keyf.write_text("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["task"], k["code"]))))
    t = 1792656000
    for p in sorted(root.rglob("*"), reverse=True):
        os.utime(p, (t, t))
    os.utime(root, (t, t))
    print(f"blind-p{n}: {len(keys)} items, redactions {red}")


if __name__ == "__main__":
    main()
