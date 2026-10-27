#!/usr/bin/env python3
"""Stage 12/12b rulebook judging sets (stage12b/DESIGN.md §4 "규칙집 판정"; copy of build_blind_12.py): stage12-private/
judge-package-rules/<pass>/<task>/, one set per task and pass (p1, p2), new random codes per pass; each set =
A, R, O (Stage 12) and Rp, N, F (12b) × m1–m3 (18 outputs). RULES.md (the 16 platform rules) is copied into each pass;
rubric: judge-package-rules/rubrics/rubric-s12-rules.md. Same material per output as build_blind_12.py.
  TASK.md            the request, verbatim
  _context/          the repository at the task's start commit (tracked files; lock files left out)
  <code>/diff.patch  the session's diff (stage-2 cleaning and LEAK redaction; session directories -> <worktree>)
  <code>/check.md    the functional check items only. The rule items are left out: rule compliance is measured by the
                     check, and the judges score overall quality only (DESIGN §7: "규칙 준수는 체크가 재고, 판정은 종합
                     품질만 본다"); the rule items' names would also show the company rules to the judge.
  <code>/reply.md    the final reply, redacted by redact_12.py (Stage 10 §4.6 rule)
Keys: stage12-private/keys/blind-key-rules-<pass>.jsonl. Uniform mtimes. After the build every text file of the pass is
scanned for condition tokens; any hit stops with the list (key not printed).
usage: build_blind_rules.py <pass>"""
import shutil
import json
import os
import random
import re
import secrets
import subprocess
import sys
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
E2E = S12.parent
PRIV = E2E / "stage12-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
from build_blind_s2 import clean_diff, redact  # noqa: E402

TASKS = {json.loads(l)["id"]: json.loads(l) for l in (PRIV / "tasks.jsonl").open()}
WT = re.compile(r"/\S*?skillfetch-e2e-wt/s12/[A-Za-z0-9_.-]+")
NW = sorted({r["id"].split("/", 1)[1].split("@")[0] for r in map(json.loads, (PRIV / "index-nw" / "skills.jsonl").open())
             if r["id"].startswith("northwind/")})
AUDIT = re.compile(r"(?i)skillfetch|\bs12-r\b|index-nw|staging-4|resolve_and_load|search_skills|load_skills|resolve_set|"
                   r"profile_repo|\bmcp\b|\bskills?\b|스킬|northwind/|(?<![\w-])(?:" + "|".join(map(re.escape, NW)) + r")(?![\w-])")
SKIP_CTX = re.compile(r"(^|/)(uv\.lock|package-lock\.json)$")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def check_md(tid, chk):
    L = [f"objective functional check ({tid}), frozen before the runs", ""]
    for i in chk.get("functional_items", []):
        tag = "PASS" if i["pass"] else ("FAIL" if i["pass"] is False else "UNDECIDABLE")
        det = str(i.get("detail") or "").replace("\n", " ")[:300]
        L.append(f"- {tag}: {i['id']}" + (f" — {det}" if det and i["pass"] is not True else ""))
    return "\n".join(L) + "\n"


def context(tdir, t):
    g = E2E / "repos" / t["repo"]
    files = subprocess.run(["git", "-C", str(g), "ls-tree", "-r", "--name-only", t["base_branch"]], capture_output=True,
                           text=True, check=True).stdout.split()
    for f in files:
        if SKIP_CTX.search(f) or f.startswith(".claude/"):
            continue
        dst = tdir / "_context" / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(subprocess.run(["git", "-C", str(g), "show", f"{t['base_branch']}:{f}"], capture_output=True).stdout)


def main():
    pas = sys.argv[1]
    top = PRIV / "judge-package-rules"
    root, keyf = top / pas, PRIV / "keys" / f"blind-key-rules-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid, t in TASKS.items():
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(c, f"m{k}") for c in ("A", "R", "O", "Rp", "N", "F") for k in (1, 2, 3)]
        missing = [f"{c} {g}" for c, g in sess if not (PRIV / "runs" / c / f"{tid}-{g}.meta.json").exists()]
        assert not missing, f"{tid}: missing runs {missing}"
        rng.shuffle(sess)
        tdir.mkdir(parents=True)
        (tdir / "TASK.md").write_text("# Request (verbatim)\n\n" + t["prompt"] + "\n")
        context(tdir, t)
        for cond, tag in sess:
            code = secrets.token_hex(4)
            d = tdir / code
            d.mkdir()
            base = PRIV / "runs" / cond / f"{tid}-{tag}"
            chk = json.loads(Path(str(base) + ".meta.json").read_text())["check"]
            diff, k = scrub(clean_diff(Path(str(base) + ".diff")))
            red += k
            (d / "diff.patch").write_text(diff)
            (d / "check.md").write_text(check_md(tid, chk))
            rp = PRIV / "redacted" / cond / f"{tid}-{tag}.reply.md"
            txt, k = scrub(rp.read_text())
            red += k
            (d / "reply.md").write_text(txt)
            keys.append({"code": code, "task": tid, "cond": cond, "tag": tag})
    shutil.copyfile(top / "RULES.md", root / "RULES.md")
    with keyf.open("a") as f:
        f.write("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["task"], k["code"]))))
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and "_context" not in p.parts and p.name != "RULES.md" and p.suffix in (".md", ".txt", ".patch", ".json"):
            for m in AUDIT.finditer(p.read_text(errors="replace")):
                hits.append(f"{p.relative_to(root)}: {m.group(0)}")
    ts = 1792656000
    for p in sorted(root.rglob("*"), reverse=True):
        os.utime(p, (ts, ts))
    os.utime(root, (ts, ts))
    print(f"{pas}: {len(keys)} items, redactions {red}, audit hits {len(hits)}")
    if hits:
        sys.exit("audit hits:\n" + "\n".join(hits[:40]))


if __name__ == "__main__":
    main()
