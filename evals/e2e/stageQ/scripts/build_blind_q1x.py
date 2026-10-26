#!/usr/bin/env python3
"""Q1 extension blind sets (DESIGN-Q1x.md §3): stageQ/judge-package-q1x/<pass>/<task>/, one set per task and pass
(p1, p2, gpt), new random codes per pass; each set = 켬 and 끔 × m1–m3 (6 outputs). Material as build_blind_q.py /
build_blind_s11.py by bundle:
  d2-redesign, d3-dashboard            wide.png, narrow.png                      rubric-design.md
  s2-docs, s2-tests                    diff.patch, check.txt; set _context/       rubrics-s2.md
  s10-t263, s10-t115, s10-t198         diff.patch, check.md, reply.md (redacted)  rubric-b4.md
  s11-t160, s11-t118                   diff.patch, check.md                      rubric-b3-s11.md (= stage11 rubric-b3.md)
  s10-t001, s10-t033                   diff.patch, check.md                      rubric-b3new.md
  s6b-t179                             diff.patch, check.md                      rubric-b3-s10.md (= stage10 rubric-b3.md)
The local-skill tasks (lq:*) are not judged (on only; DESIGN-Q1x §2.1). reply.md = stageQ1x-private/redacted/
q1-<task>-<cond>-<tag>.reply.md (redact_q.py with SQ_PRIV). Keys: stageQ1x-private/keys/blind-key-<pass>.jsonl.
Session directories -> <worktree>; uniform mtimes; condition-token audit (build_blind_q's, without "canary": the Next.js
branch name in URLs) stops the build on any hit.
usage: build_blind_q1x.py <pass>"""
import json
import os
import random
import secrets
import shutil
import sys
from pathlib import Path

SQ = Path(__file__).resolve().parents[1]
E2E = SQ.parent
PRIV = E2E / "stageQ1x-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
sys.path.insert(0, str(SQ / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff  # noqa: E402
from build_blind_s11 import check_md  # noqa: E402
import re  # noqa: E402
from build_blind_q import AUDIT as AUDIT_Q, WT, scrub  # noqa: E402

# The judged Q1-extension sets have no local canary skill; "canary" also names the Next.js branch in GitHub URLs
# (vercel/next.js/tree/canary/...), so it is dropped from the audit here. The token `cnry` stays.
AUDIT = re.compile(AUDIT_Q.pattern.replace("canary|", ""))
import run_q  # noqa: E402

TASKS = ("d2-redesign", "d3-dashboard", "s2-docs", "s2-tests", "s10-t263", "s10-t115", "s10-t198", "s11-t160", "s11-t118",
         "s10-t001", "s10-t033", "s6b-t179")
RUBRICS = {"rubric-design.md": E2E / "stage10/judge-package/rubrics/rubric-design.md",
           "rubrics-s2.md": E2E / "stage10/judge-package/rubrics/rubrics-s2.md",
           "rubric-b4.md": E2E / "stage10/judge-package/rubrics/rubric-b4.md",
           "rubric-b3new.md": E2E / "stage10/judge-package/rubrics/rubric-b3new.md",
           "rubric-b3-s10.md": E2E / "stage10/judge-package/rubrics/rubric-b3.md",
           "rubric-b3-s11.md": E2E / "stage11/judge-package/rubrics/rubric-b3.md"}


def main():
    pas = sys.argv[1]
    top = SQ / "judge-package-q1x"
    rdir = top / "rubrics"
    if not rdir.exists():
        rdir.mkdir(parents=True)
        for name, src in RUBRICS.items():
            shutil.copyfile(src, rdir / name)
    root, keyf = top / pas, PRIV / "keys" / f"blind-key-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    tasks = run_q.all_tasks()
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid in TASKS:
        t = tasks[tid]
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(c, f"m{k}") for c in ("on", "off") for k in (1, 2, 3)]
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
            chk = json.loads(Path(str(base) + ".meta.json").read_text())["check"] or {}
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
                if t["check"] == "s2":
                    txt, k = scrub(check_text(tid, chk))
                    red += k
                    (d / "check.txt").write_text(txt)
                else:
                    txt, k = scrub(check_md(tid, chk))
                    red += k
                    (d / "check.md").write_text(txt)
                if t["check"] == "b4":
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
    print(f"{pas}: {len(keys)} items, redactions {red}, audit hits {len(hits)}")
    if hits:
        sys.exit("audit hits:\n" + "\n".join(hits[:40]))


if __name__ == "__main__":
    main()
