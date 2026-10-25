#!/usr/bin/env python3
"""stage6/6b/blind-p<N>/<task>/ : one blind set per task and judging pass, new random codes per pass.
  TASK.md                      the request, verbatim
  bundle (1)  <code>/wide.png, narrow.png          screenshots from the check (none if the page/email did not render)
  bundle (2)  <code>/diff.patch, check.txt, out/   exactly as stage2/scripts/build_blind_s2.py (imported), _context/
  bundle (3)  <code>/diff.patch, check.md          diff cleaned and redacted as in stage 2; check items
Condition-revealing words are redacted (stage-2 pattern). Keys: keys/blind-key-p<N>.jsonl (outside the blind folders).
Uniform mtimes. Prints counts only. usage: build_blind_6b.py <pass number>"""
import json
import os
import random
import secrets
import shutil
import sys
from pathlib import Path

S6B = Path(__file__).resolve().parents[1]
E2E = S6B.parents[1]
sys.path.insert(0, str(E2E / "stage2" / "scripts"))
from build_blind_s2 import CONTEXT, check_text, clean_diff, redact  # noqa: E402

n = int(sys.argv[1])
root, keyf = S6B / f"blind-p{n}", S6B / "keys" / f"blind-key-p{n}.jsonl"
assert not root.exists() and not keyf.exists(), "already built"
keyf.parent.mkdir(exist_ok=True)
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6B / "tasks.jsonl").open()}
rng = random.SystemRandom()
keys, red = [], 0
for tid, t in tasks.items():
    sess = [(c, f"r{k}") for c in ("A", "C0", "Cb") for k in (1, 2, 3)
            if (S6B / "runs" / c / f"{tid}-r{k}.meta.json").exists()]
    rng.shuffle(sess)
    tdir = root / tid
    tdir.mkdir(parents=True)
    (tdir / "TASK.md").write_text("# Request (verbatim)\n\n" + t["prompt"] + "\n")
    if t["bundle"] == 2:
        ctx = tdir / "_context"
        for rel in CONTEXT[tid]:
            (ctx / rel).parent.mkdir(parents=True, exist_ok=True)
            (ctx / rel).write_text(os.popen(f"git -C '{E2E / 'repos' / t['repo']}' show s6b-a:'{rel}'").read())
    for cond, rep in sess:
        code = secrets.token_hex(4)
        d = tdir / code
        d.mkdir()
        base = S6B / "runs" / cond / f"{tid}-{rep}"
        meta = json.loads(Path(str(base) + ".meta.json").read_text())
        chk = meta["check"]
        if t["bundle"] == 1:
            cdir = Path(str(base) + ".check")
            for sub, name in (("screens", "wide.png"), ("screens-375", "narrow.png")):
                pngs = sorted((cdir / sub).glob("*.png")) if (cdir / sub).exists() else []
                if pngs:
                    shutil.copyfile(pngs[0], d / name)
        elif t["bundle"] == 2:
            diff, k = redact(clean_diff(Path(str(base) + ".diff")))
            red += k
            (d / "diff.patch").write_text(diff)
            (d / "check.txt").write_text(check_text(tid, chk))
            outdir = Path(str(base) + ".check") / "out"
            if tid == "s2-data" and outdir.exists():
                for f in sorted(outdir.rglob("*")):
                    if f.is_file():
                        dst = d / "out" / f.relative_to(outdir)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if f.stat().st_size > 400_000:
                            dst.write_bytes(f.read_bytes()[:400_000])
                        elif f.suffix in (".md", ".txt", ".json", ".html", ".csv"):
                            txt, k = redact(f.read_text(errors="replace"))
                            red += k
                            dst.write_text(txt)
                        else:
                            shutil.copyfile(f, dst)
        else:
            diff, k = redact(clean_diff(Path(str(base) + ".diff")))
            red += k
            (d / "diff.patch").write_text(diff)
            L = [f"objective check ({tid}), frozen before the runs", ""]
            for i in chk.get("items", []):
                tag = "PASS" if i["pass"] else ("FAIL" if i["pass"] is False else "INFO")
                det = str(i.get("detail") or "").replace("\n", " ")[:300]
                L.append(f"- {tag}: {i['name']}" + (f" — {det}" if det and i["pass"] is not True else ""))
            txt, k = redact("\n".join(L) + "\n")
            red += k
            (d / "check.md").write_text(txt)
        keys.append({"code": code, "task": tid, "bundle": t["bundle"], "cond": cond, "rep": rep})
keyf.write_text("".join(json.dumps(k) + "\n" for k in sorted(keys, key=lambda k: (k["task"], k["code"]))))
ts = 1792656000
for p in sorted(root.rglob("*"), reverse=True):
    os.utime(p, (ts, ts))
os.utime(root, (ts, ts))
print(f"blind-p{n}: {len(keys)} items, redactions {red}")
