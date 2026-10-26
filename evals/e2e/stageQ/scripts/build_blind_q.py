#!/usr/bin/env python3
"""Stage Q, Q1 blind sets (DESIGN §0, §1): stageQ/judge-package/<pass>/<task>/, one set per Q1 task and judging pass
(p1, p2, gpt), new random codes per pass. Material and procedure as stage11/scripts/build_blind_s11.py:
  d1-landing, d4-email   <code>/wide.png, narrow.png   (check screenshots)               rubric-design.md
  s2-api, s2-data        <code>/diff.patch, check.txt (+ out/ for s2-data); _context/   rubrics-s2.md
  s10-t016               <code>/diff.patch, check.md, reply.md                          rubric-b4.md
  s11-t266               <code>/diff.patch, check.md, reply.md                          rubric-b4-add.md
Each set: on and off × m1, m2 (4 outputs). reply.md = stageQ-private/redacted/<job>-<tag>.reply.md (redact_q.py).
Session directories (…/skillfetch-e2e-wt/sq/<random id>) -> <worktree>. Keys: stageQ-private/keys/blind-key-<pass>.jsonl.
Uniform mtimes; after the build every text file is scanned for condition tokens; any hit stops (key not printed).
usage: build_blind_q.py <pass>"""
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = E2E / "stageQ-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402
from build_blind_s11 import check_md  # noqa: E402
from run_s11 import load_tasks  # noqa: E402

TASKS = ("d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data")
WT = re.compile(r"/\S*?skillfetch-e2e-wt/sq/[A-Za-z0-9_.-]+")
AUDIT = re.compile(r"(?i)skillfetch|\bcnry|canary|staging-4|index-staging|resolve_and_load|search_skills|load_skills|"
                   r"resolve_set|profile_repo|\bmcp\b|\bq1-|\bs11-r\b|:on\b|:off\b")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def main():
    pas = sys.argv[1]
    root, keyf = SQ / "judge-package" / pas, PRIV / "keys" / f"blind-key-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid in TASKS:
        t = tasks[tid]
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(c, f"m{k}") for c in ("on", "off") for k in (1, 2)]
        missing = [f"{c} {g}" for c, g in sess if not (PRIV / "runs" / f"q1-{tid}-{c}-{g}.meta.json").exists()]
        assert not missing, f"{tid}: missing runs {missing}"
        rng.shuffle(sess)
        tdir.mkdir(parents=True)
        (tdir / "TASK.md").write_text("# Request (verbatim)\n\n" + t["prompt"] + "\n")
        if tid in CONTEXT:
            for rel in CONTEXT[tid]:
                (tdir / "_context" / rel).parent.mkdir(parents=True, exist_ok=True)
                (tdir / "_context" / rel).write_text(os.popen(f"git -C '{E2E / 'repos' / t['repo']}' show s6b-a:'{rel}'").read())
        for cond, tag in sess:
            code = secrets.token_hex(4)
            d = tdir / code
            d.mkdir()
            base = PRIV / "runs" / f"q1-{tid}-{cond}-{tag}"
            chk = json.loads(Path(str(base) + ".meta.json").read_text())["check"]
            if t["bundle"] == 1:
                cdir = Path(str(base) + ".check")
                for sub, name in (("screens", "wide.png"), ("screens-375", "narrow.png")):
                    pngs = sorted((cdir / sub).glob("*.png")) if (cdir / sub).exists() else []
                    if pngs:
                        shutil.copyfile(pngs[0], d / name)
            else:
                diff, k = scrub(clean_diff(Path(str(base) + ".diff")))
                red += k
                (d / "diff.patch").write_text(diff)
                if t["bundle"] == 2:
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
                    rp = PRIV / "redacted" / f"q1-{tid}-{cond}-{tag}.reply.md"
                    (d / "reply.md").write_text(WT.sub("<worktree>", rp.read_text()))
            keys.append({"code": code, "task": tid, "bundle": t["bundle"], "cond": cond, "tag": tag})
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
    print(f"{pas}: {len(keys)} items, redactions {red}, audit hits {len(hits)}")
    if hits:
        sys.exit("audit hits:\n" + "\n".join(hits[:40]))


if __name__ == "__main__":
    main()
