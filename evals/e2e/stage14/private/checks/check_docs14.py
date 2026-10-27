#!/usr/bin/env python3
"""Stage 14 task 5 check (monorepo README). Runs on the whole snapshot tree after the request (git base = the tree before it).
usage: check_docs14.py <worktree> <outdir> --base <commit>
Items (pass = all):
  a  README.md at the repo root, non-empty
  b  the doc files changed by this request name all four areas: web/, api/, media/, data/ (as path text)
  c  npm scripts named in those docs (npm run X, yarn X, pnpm [run] X, bun run X) exist in web/package.json (or npm built-ins)
  d  repository paths written in backticks in those docs that start with web/, api/, media/ or data/ exist in the tree
     (from the root, or relative to one of the four area folders)
Metrics: doc files, non-doc files changed by the request, README words."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def git(wt, *a):
    return subprocess.run(["git", "-C", str(wt), *a], capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("out")
    ap.add_argument("--base", required=True)
    a = ap.parse_args()
    wt, out = Path(a.worktree), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, m = [], {}
    readme = next((p for p in wt.iterdir() if p.name.lower() == "readme.md"), None)
    m["readme_words"] = len(readme.read_text(errors="replace").split()) if readme else 0
    items.append({"name": "a README.md at the repo root", "pass": readme is not None and m["readme_words"] > 0, "detail": str(m["readme_words"])})
    changed = sorted(set(git(wt, "diff", "--name-only", a.base).split()) | set(git(wt, "ls-files", "--others", "--exclude-standard").split()))
    docs = [p for p in changed if p.lower().endswith((".md", ".mdx", ".txt")) and (wt / p).exists()]
    m["doc_files"], m["non_doc_changes"] = docs, [p for p in changed if p not in docs]
    text = "\n".join((wt / p).read_text(errors="replace") for p in docs)
    missing_area = [x for x in ("web/", "api/", "media/", "data/") if x not in text]
    items.append({"name": "b docs name all four areas (web/, api/, media/, data/)", "pass": bool(docs) and not missing_area,
                  "detail": ", ".join(missing_area)})
    scripts = set(json.loads((wt / "web" / "package.json").read_text()).get("scripts", {}))
    refs = set(re.findall(r"\b(?:npm run|yarn|pnpm(?: run)?|bun run)\s+([A-Za-z][\w:-]*)", text))
    builtin = {"install", "add", "dlx", "create", "exec", "i", "ci", "start", "test"}
    miss = sorted(r for r in refs if r not in scripts and r not in builtin)
    items.append({"name": "c npm scripts named in the docs exist in web/package.json", "pass": not miss, "detail": ", ".join(miss)})
    paths = set(re.findall(r"`((?:web|api|media|data)/[^`\s]*)`", text))
    def exists(p):  # from the root, or relative to one of the four area folders (fixed after the pilot, DESIGN §9)
        q = p.rstrip("/").split("#")[0].split(":")[0]
        return (wt / q).exists() or any((wt / a / q).exists() for a in ("web", "api", "media", "data"))
    bad = sorted(p for p in paths if not exists(p) and not any(ch in p for ch in "*<>{}$"))
    m["paths_referenced"] = sorted(paths)
    items.append({"name": "d repository paths in backticks exist", "pass": not bad, "detail": ", ".join(bad)[:300]})
    res = {"task_id": "s14-docs", "pass": all(i["pass"] for i in items), "items": items, "metrics": m}
    (out / "check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({"pass": res["pass"], "items": [(i["name"][:1], i["pass"]) for i in items]}))


if __name__ == "__main__":
    main()
