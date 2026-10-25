#!/usr/bin/env python3
"""stage1b/rejudge/: a fresh blind set over A, B, C (first 1b run) and C2 (rerun, search k=50), new random codes.
  screens-blind/<task>/<code>/  desktop + 375px PNGs of the two landing tasks (8 sets each)
  plans-blind/s1b-fa-tags-plan/<code>/PLAN.md + impl.diff (8), same redaction as build_plans_blind.py
Mappings: rejudge/screens-key.jsonl, rejudge/plans-key.jsonl (outside the blind folders). Uniform mtimes.
Prints counts only."""
import json
import os
import random
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

S1B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from build_plans_blind import impl_diff, redact  # noqa: E402

OUT = S1B / "rejudge"
CONDS = ("A", "B", "C", "C2")
LANDING = ("s1b-nx-landing", "s1b-fa-landing")
PLAN = "s1b-fa-tags-plan"


def metas(task):
    return [mp for c in CONDS for mp in sorted((S1B / "runs" / c).glob(f"{task}-r*.meta.json"))]


def main():
    assert not (OUT / "screens-blind").exists() and not (OUT / "plans-blind").exists(), "already built"
    rng = random.SystemRandom()
    skeys, pkeys, n_png, n_red = [], [], 0, 0
    for task in LANDING:
        ms = metas(task)
        rng.shuffle(ms)
        for mp in ms:
            meta = json.loads(mp.read_text())
            pngs = sorted(Path(str(mp)[: -len(".meta.json")] + ".check").glob("screens*/*.png"))
            code = secrets.token_hex(4)
            d = OUT / "screens-blind" / task / code
            d.mkdir(parents=True)
            for png in pngs:
                shutil.copyfile(png, d / f"{png.parent.name}__{png.name}")
                n_png += 1
            skeys.append({"code": code, "task": task, "cond": meta["cond"], "rep": meta["rep"]})
    ms = metas(PLAN)
    rng.shuffle(ms)
    for mp in ms:
        meta = json.loads(mp.read_text())
        wt = Path(meta["worktree"])
        files = subprocess.run(["git", "-C", str(wt), "ls-files", "--others", "--cached", "--exclude-standard"],
                               capture_output=True, text=True).stdout.splitlines()
        plans = sorted(p for p in files if Path(p).name == "PLAN.md")
        code = secrets.token_hex(4)
        d = OUT / "plans-blind" / PLAN / code
        d.mkdir(parents=True)
        plan, k1 = redact((wt / plans[0]).read_text(errors="replace")) if plans else ("(PLAN.md not found)\n", 0)
        diff, k2 = redact(impl_diff(Path(str(mp)[: -len(".meta.json")] + ".diff")))
        (d / "PLAN.md").write_text(plan)
        (d / "impl.diff").write_text(diff)
        n_red += k1 + k2
        pkeys.append({"code": code, "task": PLAN, "cond": meta["cond"], "rep": meta["rep"], "redactions": k1 + k2})
    (OUT / "screens-key.jsonl").write_text("".join(json.dumps(k) + "\n" for k in sorted(skeys, key=lambda k: k["code"])))
    (OUT / "plans-key.jsonl").write_text("".join(json.dumps(k) + "\n" for k in sorted(pkeys, key=lambda k: k["code"])))
    t = 1792656000
    for root in (OUT / "screens-blind", OUT / "plans-blind"):
        for p in sorted(root.rglob("*"), reverse=True):
            os.utime(p, (t, t))
        os.utime(root, (t, t))
    print(f"screens: {len(skeys)} sets, {n_png} png; plans: {len(pkeys)} sets, redactions {n_red}")


if __name__ == "__main__":
    main()
