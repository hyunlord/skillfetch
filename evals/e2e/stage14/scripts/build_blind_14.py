#!/usr/bin/env python3
"""Stage 14 blind sets (stage14/DESIGN.md §4 item 1): stage14-private/judge-package/<pass>/<set>/, one set per task and pass
(p1, p2), new random codes per pass; each set = the 6 main outputs of that task (A, P, R × order F, B × m1; 1 run after the pilot, DESIGN §9), each
the output of that one request (diff = the request's snapshot diff). Material per set (as in Stage 13 / Stage 2 / 11):
  s14-landing   <code>/wide.png, narrow.png (the check's 1280 / 375 screenshots of /landing)      rubric-design.md
  s14-api       diff.patch, check.txt (session tests, contract script)                            rubrics-s2.md (s2-api)
  s14-apitests  diff.patch, check.txt (suite passes, tests before/after, mutants caught)          rubrics-14.md
  s14-rust      diff.patch, check.md, reply.md (that request's final reply, redacted)               rubric-b4-add.md (t266)
  s14-docs      diff.patch, check.txt; _context/ = the start tree's files (s14-a)                 rubrics-14.md
  s14-data      diff.patch, check.txt, out/ (the check's run); _context/data/orders.csv           rubrics-s2.md (s2-data)
Diffs: build_blind_s2.clean_diff + redact (one rule for all conditions); worktree paths replaced. reply.md: Stage 10 §4.6
rule (redact_s11.process) with the trace terms of every skill loaded or used in any Stage 14 session, the 8 P skill names
and the router tool names; task-content audit of s11-t266. Keys: stage14-private/keys/blind-key-<pass>.jsonl.
After the build every text file is scanned for condition tokens (skillfetch tool names, MCP, P skill names, taste-skill,
.claude/skills, session names); any hit stops (key not printed). Uniform mtimes.
usage: build_blind_14.py <pass>"""
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
PRIV = E2E / "stage14-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
sys.path.insert(0, str(E2E / "stage13" / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402
from build_blind_s11 import check_md  # noqa: E402
from redact_s11 import process, task_patterns, trace_patterns  # noqa: E402
import usage_13 as u13  # noqa: E402

SETS = {"landing": "s14-landing", "api": "s14-api", "apitests": "s14-apitests", "rust": "s14-rust", "docs": "s14-docs", "data": "s14-data"}
RUBRIC = {"rubric-design.md": E2E / "stage10/judge-package/rubrics/rubric-design.md",
          "rubrics-s2.md": E2E / "stage10/judge-package/rubrics/rubrics-s2.md",
          "rubric-b4-add.md": E2E / "stage11/rubric-b4-add.md",
          "rubrics-14.md": S14 / "rubrics-14.md"}
WT = re.compile(r"/\S*?skillfetch-e2e-wt/sq/[A-Za-z0-9_.-]+")
P_NAMES = list(u13.P_NAMES)
AUDIT = re.compile(r"(?i)skillfetch|\bcnry|staging-4|index-staging|resolve_and_load|search_skills|load_skills|resolve_set|"
                   r"profile_repo|\bmcp\b|taste-skill|\.claude/skills|\b[APR]-[FB]-(?:m|p)\d\b|\bs14-[apr]\b|"
                   r"(?<![\w-])(?:" + "|".join(map(re.escape, P_NAMES)) + r")(?![\w-])")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def runs():
    out = []
    for m in sorted((PRIV / "runs").glob("*-*-m*.meta.json")):
        meta = json.loads(m.read_text())
        base = str(m)[: -len(".meta.json")]
        for s in meta["steps"]:
            out.append({"cond": meta["cond"], "order": meta["order"], "tag": meta["tag"], "k": s["k"], "task": s["task"],
                        "base": f"{base}.p{s['k']}", "check": (meta.get("checks") or {}).get(s["task"]) or {}})
    return out


def apitests_text(chk):
    m = chk.get("metrics") or {}
    L = ["objective check (API tests), frozen before the runs", ""]
    for i in chk.get("items") or []:
        L.append(f"- {'PASS' if i['pass'] else 'FAIL'}: {i['name']}" + (f" — {i['detail']}" if i.get("detail") else ""))
    mk = m.get("mutants") or {}
    if mk:
        L.append(f"- contract-level mutants caught by the suite: {m.get('mutants_killed')}/8 — " +
                 ", ".join(f"{k} {'caught' if v else 'missed'}" for k, v in mk.items()))
    else:
        L.append("- mutants not run (the suite did not pass unmutated)")
    return redact("\n".join(L) + "\n")[0]


def docs_text(chk):
    m = chk.get("metrics") or {}
    L = ["objective check (root README), frozen before the runs", ""]
    for i in chk.get("items") or []:
        L.append(f"- {'PASS' if i['pass'] else 'FAIL'}: {i['name']}" + (f" — {i['detail']}" if i.get("detail") and not i["pass"] else ""))
    L.append(f"- README words: {m.get('readme_words')}; doc files added/changed: {', '.join(m.get('doc_files') or [])}")
    L.append(f"- non-doc files changed: {', '.join(m.get('non_doc_changes') or []) or 'none'}")
    return redact("\n".join(L) + "\n")[0]


def trace_terms(rs_):
    ids = set()
    for r in rs_:
        p = Path(r["base"] + ".jsonl")
        ids |= {f"x/{n}@0" for n in u13.r_session(p)}
        for d in u13.events(p):
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                    s = str((c.get("input") or {}).get("skill") or "").split(":")[-1]
                    if s:
                        ids.add(f"x/{s}@0")
    ids |= {f"p/{n}@0" for n in P_NAMES}
    return trace_patterns(sorted(ids))


def main():
    pas = sys.argv[1]
    top = PRIV / "judge-package"
    rdir = top / "rubrics"
    if not rdir.exists():
        rdir.mkdir(parents=True)
        for name, src in RUBRIC.items():
            shutil.copyfile(src, rdir / name)
    root, keyf = top / pas, PRIV / "keys" / f"blind-key-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    allr = runs()
    assert len(allr) == 36, f"expected 36 main requests, found {len(allr)}"
    tpats, _ = trace_terms([r for r in allr if r["task"] == "rust"])
    cp = task_patterns()["s11-t266"][0]
    keys, red, audit = [], 0, []
    for task, sname in SETS.items():
        sdir = root / sname
        assert not sdir.exists(), f"{sdir} already built"
        sdir.mkdir(parents=True)
        items = [r for r in allr if r["task"] == task]
        assert len(items) == 6, (task, len(items))
        import random
        random.SystemRandom().shuffle(items)
        prompt = re.search(rf"^## \d {task} \(\w+\)\n((?:> .*\n?)+)", (S14 / "requests.md").read_text(), re.M).group(1)
        (sdir / "TASK.md").write_text("# Request (verbatim)\n\n" + "\n".join(l[2:] for l in prompt.strip().splitlines()) + "\n")
        if task == "docs":
            arch = subprocess.run(["git", "-C", str(E2E / "repos" / "s14-mono"), "archive", "s14-a"], capture_output=True, check=True).stdout
            (sdir / "_context").mkdir()
            subprocess.run(["tar", "-x", "-C", str(sdir / "_context")], input=arch, check=True)
        if task == "data":
            for rel in CONTEXT["s2-data"]:
                src = subprocess.run(["git", "-C", str(E2E / "repos" / "s14-mono"), "show", f"s14-a:data/{rel}"], capture_output=True).stdout
                (sdir / "_context" / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
                (sdir / "_context" / "data" / rel).write_bytes(src)
        for r in items:
            code = secrets.token_hex(4)
            d = sdir / code
            d.mkdir()
            chk = r["check"]
            cdir = Path(r["base"] + ".check")
            if task == "landing":
                for sub, name in (("screens", "wide.png"), ("screens-375", "narrow.png")):
                    pngs = sorted((cdir / sub).glob("*.png")) if (cdir / sub).exists() else []
                    if pngs:
                        shutil.copyfile(pngs[0], d / name)
            else:
                diff, k = scrub(clean_diff(Path(r["base"] + ".diff")))
                red += k
                (d / "diff.patch").write_text(diff)
                if task in ("api", "data"):
                    (d / "check.txt").write_text(scrub(check_text(f"s2-{task}", chk))[0])
                elif task == "apitests":
                    (d / "check.txt").write_text(apitests_text(chk))
                elif task == "docs":
                    (d / "check.txt").write_text(docs_text(chk))
                else:
                    (d / "check.md").write_text(scrub(check_md("s11-t266", chk))[0])
                    reply = Path(r["base"] + ".reply.txt").read_text(errors="replace")
                    txt, recs = process(WT.sub("<worktree>", reply), tpats, cp)
                    (d / "reply.md").write_text(txt)
                    red += len(recs)
                if task == "data" and (cdir / "out").exists():
                    for f in sorted((cdir / "out").rglob("*")):
                        if f.is_file():
                            dst = d / "out" / f.relative_to(cdir / "out")
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            if f.stat().st_size > 400_000:
                                dst.write_bytes(f.read_bytes()[:400_000])
                            elif f.suffix in (".md", ".txt", ".json", ".html", ".csv"):
                                dst.write_text(scrub(f.read_text(errors="replace"))[0])
                            else:
                                shutil.copyfile(f, dst)
            keys.append({"code": code, "task": task, "set": sname, "cond": r["cond"], "order": r["order"], "tag": r["tag"], "k": r["k"]})
    with keyf.open("a") as f:
        f.write("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["set"], k["code"]))))
    for p in root.rglob("*"):
        if p.is_file() and "_context" not in p.parts and p.suffix in (".md", ".txt", ".patch", ".json", ".csv", ".html"):
            for m in AUDIT.finditer(p.read_text(errors="replace")):
                audit.append(f"{p.relative_to(root)}: {m.group(0)}")
    ts = 1792656000
    for p in sorted(root.rglob("*"), reverse=True):
        os.utime(p, (ts, ts))
    os.utime(root, (ts, ts))
    print(f"{pas}: {len(keys)} items, redactions {red}, audit hits {len(audit)}")
    if audit:
        sys.exit("audit hits:\n" + "\n".join(audit[:40]))


if __name__ == "__main__":
    main()
