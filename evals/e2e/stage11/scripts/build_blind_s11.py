#!/usr/bin/env python3
"""stage11/judge-package/<pass>/<task>/ : one blind set per task and judging pass (p1, p2, gpt), new random codes per
pass (DESIGN §5). Same material and procedure as stage10/scripts/build_blind_s10.py; Stage 11 cells:
  bundles (1)(2)  E1 R0, R1 × m1–m3            (6 results per set)
  bundle (3)      E1 R0, R1 × m1–m6            (12)
  bundle (4)      E1 A, R0, R1 × m1–m6         (18; A included, DESIGN §5)
  TASK.md                      the request, verbatim
  bundle (1)  <code>/wide.png, narrow.png         screenshots from the check
  bundle (2)  <code>/diff.patch, check.txt, out/  as Stage 10; _context/ from s6b-a
  bundle (3)  <code>/diff.patch, check.md
  bundle (4)  <code>/diff.patch, check.md, reply.md   reply.md = stage11-private/redacted/<cond>/... (DESIGN §6)
Diffs and check text: stage-2 cleaning and LEAK redaction, session directories (…/skillfetch-e2e-wt/s11/<random id>)
replaced with <worktree>. Keys: stage11-private/keys/blind-key-<pass>.jsonl. Uniform mtimes. After the build every text
file of the pass is scanned for condition tokens; any hit stops with the list (key not printed).
usage: build_blind_s11.py <pass> <bundles, e.g. 1,2,3,4>"""
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path

S11 = Path(__file__).resolve().parents[1]
E2E = S11.parent
PRIV = E2E / "stage11-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(S11 / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402
from run_s11 import load_tasks  # noqa: E402

CELLS = {1: ("R0", "R1"), 2: ("R0", "R1"), 3: ("R0", "R1"), 4: ("A", "R0", "R1")}
TAGS = {1: 3, 2: 3, 3: 6, 4: 6}
WT = re.compile(r"/\S*?skillfetch-e2e-wt/s1[01]/[A-Za-z0-9_.-]+")
AUDIT = re.compile(r"(?i)skillfetch|\bR1s\b|\bR0\b|-E[12]-|\bs1[01]-rs?\b|staging-4|index-staging|resolve_and_load|search_skills|"
                   r"load_skills|resolve_set|profile_repo|\bmcp\b")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def check_md(tid, chk):
    L = [f"objective check ({tid}), frozen before the runs", ""]
    for i in chk.get("items", []):
        tag = "PASS" if i["pass"] else ("FAIL" if i["pass"] is False else "UNDECIDABLE")
        det = str(i.get("detail") or "").replace("\n", " ")[:300]
        L.append(f"- {tag}: {i['name']}" + (f" — {det}" if det and i["pass"] is not True else ""))
    return "\n".join(L) + "\n"


def main():
    pas, bundles = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
    root, keyf = S11 / "judge-package" / pas, PRIV / "keys" / f"blind-key-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid, t in tasks.items():
        b = t["bundle"]
        if b not in bundles:
            continue
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(c, f"m{k}") for c in CELLS[b] for k in range(1, TAGS[b] + 1)]
        missing = [f"{c} {g}" for c, g in sess if not (PRIV / "runs" / c / f"{tid}-{g}.meta.json").exists()]
        assert not missing, f"{tid}: missing runs {missing}"
        rng.shuffle(sess)
        tdir.mkdir(parents=True)
        (tdir / "TASK.md").write_text("# Request (verbatim)\n\n" + t["prompt"] + "\n")
        if b == 2:
            ctx = tdir / "_context"
            for rel in CONTEXT[tid]:
                (ctx / rel).parent.mkdir(parents=True, exist_ok=True)
                (ctx / rel).write_text(os.popen(f"git -C '{E2E / 'repos' / t['repo']}' show s6b-a:'{rel}'").read())
        for cond, tag in sess:
            code = secrets.token_hex(4)
            d = tdir / code
            d.mkdir()
            base = PRIV / "runs" / cond / f"{tid}-{tag}"
            chk = json.loads(Path(str(base) + ".meta.json").read_text())["check"]
            if b == 1:
                cdir = Path(str(base) + ".check")
                for sub, name in (("screens", "wide.png"), ("screens-375", "narrow.png")):
                    pngs = sorted((cdir / sub).glob("*.png")) if (cdir / sub).exists() else []
                    if pngs:
                        shutil.copyfile(pngs[0], d / name)
            else:
                diff, k = scrub(clean_diff(Path(str(base) + ".diff")))
                red += k
                (d / "diff.patch").write_text(diff)
                if b == 2:
                    txt, k = scrub(check_text(tid, chk))
                    red += k
                    (d / "check.txt").write_text(txt)
                    outdir = Path(str(base) + ".check") / "out"
                    if tid == "s2-data" and outdir.exists():
                        for f in sorted(outdir.rglob("*")):
                            if f.is_file():
                                dst = d / "out" / f.relative_to(outdir)
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                if f.stat().st_size > 400_000:
                                    dst.write_bytes(f.read_bytes()[:400_000])
                                elif f.suffix in (".md", ".txt", ".json", ".html", ".csv"):
                                    txt, k = scrub(f.read_text(errors="replace"))
                                    red += k
                                    dst.write_text(txt)
                                else:
                                    shutil.copyfile(f, dst)
                else:
                    txt, k = scrub(check_md(tid, chk))
                    red += k
                    (d / "check.md").write_text(txt)
                if b == 4:
                    rp = PRIV / "redacted" / cond / f"{tid}-{tag}.reply.md"
                    (d / "reply.md").write_text(WT.sub("<worktree>", rp.read_text()))
            keys.append({"code": code, "task": tid, "bundle": b, "env": "E1", "cond": cond, "tag": tag})
    with keyf.open("a") as f:
        f.write("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["task"], k["code"]))))
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".txt", ".patch", ".json", ".csv", ".html"):
            for m in AUDIT.finditer(p.read_text(errors="replace")):
                hits.append(f"{p.relative_to(root)}: {m.group(0)}")
    ts = 1792656000
    for p in sorted(root.rglob("*"), reverse=True):
        os.utime(p, (ts, ts))
    os.utime(root, (ts, ts))
    print(f"{pas} bundles {sorted(bundles)}: {len(keys)} items, redactions {red}, audit hits {len(hits)}")
    if hits:
        sys.exit("audit hits:\n" + "\n".join(hits[:40]))


if __name__ == "__main__":
    main()
