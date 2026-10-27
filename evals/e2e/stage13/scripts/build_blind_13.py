#!/usr/bin/env python3
"""Stage 13 blind sets (stage13/DESIGN.md §3; user 2026-10-27: "판정은 A·P·R을 같은 세트에 섞어서 새로 한다"):
stage13-private/judge-package/<pass>/<task>/, one set per task and pass (p1, p2), new random codes per pass; each set =
A (off), P, R (on) × m1–m3 (9 outputs). Material and rubric per bundle as in Stage Q Q1 (build_blind_q.py) and the Q1
extension (build_blind_q1x.py):
  bundle 1 (d1-landing, d2-redesign, d3-dashboard, d4-email)  <code>/wide.png, narrow.png            rubric-design.md
  bundle 2 (s2-api, s2-data, s2-docs, s2-tests)               diff.patch, check.txt (+ out/ s2-data); _context/   rubrics-s2.md
  bundle 3 (s11-t160, s11-t118)                               diff.patch, check.md                  rubric-b3-s11.md
           (s10-t001, s10-t033)                               diff.patch, check.md                  rubric-b3new.md
           (s6b-t179)                                         diff.patch, check.md                  rubric-b3-s10.md
  bundle 4 (s10-t016, s10-t263, s10-t115, s10-t198)           diff.patch, check.md, reply.md        rubric-b4.md
           (s11-t266)                                         diff.patch, check.md, reply.md        rubric-b4-add.md
Sources: A·R of the Q1 tasks = stageQ-private/runs/q1-<task>-<off|on>-m1..m3; of the Q1-extension tasks =
stageQ1x-private/runs/…; P = stage13-private/runs/p-<task>-m1..m3. reply.md = stage13-private/redacted/<cond>-<task>-<tag>
.reply.md (redact_13.py, one rule for all three conditions). Keys: stage13-private/keys/blind-key-<pass>.jsonl.
Uniform mtimes; after the build every text file is scanned for condition tokens (skillfetch tool names, MCP, the P skill
names, branch names); any hit stops (key not printed). "canary" is not an audit word here: it is the Next.js branch name in
GitHub URLs (vercel/next.js/tree/canary/…), as in build_blind_q1x.py; the canary skill token `cnry` stays.
usage: build_blind_13.py <pass>"""
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
E2E = S13.parent
PRIV = E2E / "stage13-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
sys.path.insert(0, str(E2E / "stageQ" / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402
from build_blind_s11 import check_md  # noqa: E402
import run_q  # noqa: E402

Q1 = ("d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data")
TASKS = json.loads((PRIV / "tasks13.json").read_text())["tasks"]
P_NAMES = [m["name"] for m in json.loads((PRIV / "p-skills-manifest.json").read_text())]
RUBRIC = {"rubric-design.md": E2E / "stage10/judge-package/rubrics/rubric-design.md",
          "rubrics-s2.md": E2E / "stage10/judge-package/rubrics/rubrics-s2.md",
          "rubric-b4.md": E2E / "stage10/judge-package/rubrics/rubric-b4.md",
          "rubric-b4-add.md": E2E / "stage11/rubric-b4-add.md",
          "rubric-b3new.md": E2E / "stage10/judge-package/rubrics/rubric-b3new.md",
          "rubric-b3-s10.md": E2E / "stage10/judge-package/rubrics/rubric-b3.md",
          "rubric-b3-s11.md": E2E / "stage11/judge-package/rubrics/rubric-b3.md"}
WT = re.compile(r"/\S*?skillfetch-e2e-wt/sq/[A-Za-z0-9_.-]+")
AUDIT = re.compile(r"(?i)skillfetch|\bcnry|staging-4|index-staging|resolve_and_load|search_skills|load_skills|"
                   r"resolve_set|profile_repo|\bmcp\b|\bq1-|\bs11-r\b|\bs13-p|:on\b|:off\b|"
                   r"(?<![\w-])(?:" + "|".join(map(re.escape, P_NAMES)) + r")(?![\w-])")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def source(tid, cond, tag):
    if cond == "P":
        return PRIV / "runs" / f"p-{tid}-{tag}"
    d = "stageQ-private" if tid in Q1 else "stageQ1x-private"
    return E2E / d / "runs" / f"q1-{tid}-{'on' if cond == 'R' else 'off'}-{tag}"


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
    tasks = run_q.all_tasks()
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid in TASKS:
        t = tasks[tid]
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(c, f"m{k}") for c in ("A", "P", "R") for k in (1, 2, 3)]
        missing = [f"{c} {g}" for c, g in sess if not Path(str(source(tid, c, g)) + ".meta.json").exists()]
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
            base = source(tid, cond, tag)
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
                if t["bundle"] == 4:
                    rp = PRIV / "redacted" / f"{cond}-{tid}-{tag}.reply.md"
                    (d / "reply.md").write_text(WT.sub("<worktree>", rp.read_text()))
            keys.append({"code": code, "task": tid, "bundle": t["bundle"], "cond": cond, "tag": tag})
    with keyf.open("a") as f:
        f.write("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["task"], k["code"]))))
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and "_context" not in p.parts and p.suffix in (".md", ".txt", ".patch", ".json", ".csv", ".html"):
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
