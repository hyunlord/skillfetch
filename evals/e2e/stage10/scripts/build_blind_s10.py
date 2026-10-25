#!/usr/bin/env python3
"""stage10/judge-package/<pass>/<task>/ : one blind set per task and judging pass (p1, p2, gpt), new random codes per pass.
Each set holds every main-run session of the task: E1 {A, R0, R1, R1s} and E2 {A, R1}, tags m1-m3 (18 results).
  TASK.md                      the request, verbatim
  bundle (1)  <code>/wide.png, narrow.png         screenshots from the check (as 6b)
  bundle (2)  <code>/diff.patch, check.txt, out/  as stage2 build_blind_s2 / 6b; _context/ from s6b-a
  bundle (3)  <code>/diff.patch, check.md         as 6b
  bundle (4)  <code>/diff.patch, check.md, reply.md   reply.md = stage10-private/redacted/... (DESIGN §4.6)
Diffs and check text: stage-2 cleaning and LEAK redaction (as 6b), after replacing session worktree paths
(…/skillfetch-e2e-wt/s10/s10-<env>-<cond>-<task>-<tag>, which name the condition) with <worktree>.
Keys: stage10-private/keys/blind-key-<pass>.jsonl (appended per bundle build). Uniform mtimes. After the build every
text file of the pass is scanned for condition tokens; any hit stops with the list (key not printed).
usage: build_blind_s10.py <pass> <bundles, e.g. 1,2,3> [--tasks <file>] [--cells E1:R0,E1:R1,...] [--tags n1,n2,n3]
  (defaults: tasks.jsonl, the six cells above, m1-m3; the DESIGN §11 re-measurement uses tasks-b3new.jsonl,
   E1:R0,E1:R1,E1:R1s, n1-n3, and its own pass names, e.g. p1n, p2n, gptn)"""
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
E2E = S10.parent
PRIV = E2E / "stage10-private"
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402

CELLS = [("E1", "A"), ("E1", "R0"), ("E1", "R1"), ("E1", "R1s"), ("E2", "A"), ("E2", "R1")]
TAGS = ("m1", "m2", "m3")
WT = re.compile(r"/\S*?skillfetch-e2e-wt/s10/[A-Za-z0-9_.-]+|\bs10-E[12]-(?:A|R0|R1s?)-[A-Za-z0-9_.-]+")
AUDIT = re.compile(r"(?i)skillfetch|\bR1s\b|\bR0\b|-E[12]-|\bs10-rs?\b|staging-4|index-staging|resolve_and_load|search_skills|"
                   r"load_skills|resolve_set|profile_repo|\bmcp\b")


def scrub(text):
    return redact(WT.sub("<worktree>", text))


def check_md(tid, chk):
    L = [f"objective check ({tid}), frozen before the runs", ""]
    for i in chk.get("items", []):
        tag = "PASS" if i["pass"] else ("FAIL" if i["pass"] is False else "INFO")
        det = str(i.get("detail") or "").replace("\n", " ")[:300]
        L.append(f"- {tag}: {i['name']}" + (f" — {det}" if det and i["pass"] is not True else ""))
    return "\n".join(L) + "\n"


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    global CELLS, TAGS
    pas, bundles = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
    tasks_file = opt("--tasks", "tasks.jsonl")
    CELLS = [tuple(c.split(":")) for c in opt("--cells", ",".join(f"{e}:{c}" for e, c in CELLS)).split(",")]
    TAGS = tuple(opt("--tags", ",".join(TAGS)).split(","))
    root, keyf = S10 / "judge-package" / pas, PRIV / "keys" / f"blind-key-{pas}.jsonl"
    keyf.parent.mkdir(parents=True, exist_ok=True)
    tasks = {json.loads(l)["id"]: json.loads(l) for l in (S10 / tasks_file).open()}
    rng = random.SystemRandom()
    keys, red = [], 0
    for tid, t in tasks.items():
        if t["bundle"] not in bundles:
            continue
        tdir = root / tid
        assert not tdir.exists(), f"{tdir} already built"
        sess = [(e, c, g) for e, c in CELLS for g in TAGS]
        assert all((PRIV / "runs" / e / c / f"{tid}-{g}.meta.json").exists() for e, c, g in sess), tid
        rng.shuffle(sess)
        tdir.mkdir(parents=True)
        (tdir / "TASK.md").write_text("# Request (verbatim)\n\n" + t["prompt"] + "\n")
        if t["bundle"] == 2:
            ctx = tdir / "_context"
            for rel in CONTEXT[tid]:
                (ctx / rel).parent.mkdir(parents=True, exist_ok=True)
                (ctx / rel).write_text(os.popen(f"git -C '{E2E / 'repos' / t['repo']}' show s6b-a:'{rel}'").read())
        for env, cond, tag in sess:
            code = secrets.token_hex(4)
            d = tdir / code
            d.mkdir()
            base = PRIV / "runs" / env / cond / f"{tid}-{tag}"
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
                if t["bundle"] == 4:
                    rp = PRIV / "redacted" / env / cond / f"{tid}-{tag}.reply.md"
                    (d / "reply.md").write_text(WT.sub("<worktree>", rp.read_text()))
            keys.append({"code": code, "task": tid, "bundle": t["bundle"], "env": env, "cond": cond, "tag": tag})
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
