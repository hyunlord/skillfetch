#!/usr/bin/env python3
"""Re-check finished Stage 12 sessions whose check ran on an uncommitted worktree (pilot, 2026-10-27; DESIGN §11).
Same procedure as the reference validation: single-branch clone of the session's branch at its base commit, the session's
collected diff (<out>.diff) applied, dependencies prepared as for a session, then run_12.run_check (snapshot commit +
frozen check). The first check result is kept in meta["check_uncommitted"]; meta["check"] gets the new one.
With --label L on a session already re-checked, the current meta["check"] moves to meta["check_before_<L>"] first
(2026-10-27: label "t-wrapper-multiline" after the t() wrapper/alias and multi-line call fixes).
usage: recheck_12.py [--label L] <cond>/<task>-<tag> [...]"""
import json
import secrets
import shutil
import sys
from pathlib import Path

import run_12

base = run_12.base


def recheck(key, label=None):
    cond, rest = key.split("/")
    task_id, tag = rest.rsplit("-", 1)
    run_12.configure(cond, task_id)
    task = run_12.load_tasks()[task_id]
    out = run_12.PRIV / "runs" / cond / f"{task_id}-{tag}"
    meta_p = Path(str(out) + ".meta.json")
    m = json.loads(meta_p.read_text())
    if "check_uncommitted" in m:
        assert label and f"check_before_{label}" not in m, f"{key}: already re-checked (pass a new --label)"
    sid = secrets.token_hex(4)
    wt = base.WT_ROOT / f"recheck-{sid}"
    try:
        base.clone(task, cond, wt)
        assert base.git(wt, "rev-parse", "HEAD") == m["base"], "clone head != session base"
        diff = Path(str(out) + ".diff")
        if diff.read_text().strip():
            base.sh(["git", "apply", "--whitespace=nowarn", str(diff)], cwd=wt, check=True)
        base.prepare(task, wt, sid)
        cdir = Path(str(out) + ".check")
        if cdir.exists():
            shutil.move(str(cdir), str(out) + (f".check-before-{label}" if "check_uncommitted" in m else ".check-uncommitted"))
        res = run_12.run_check(task, wt, m["base"], out)
    finally:
        shutil.rmtree(wt, ignore_errors=True)
    if "check_uncommitted" in m:
        m[f"check_before_{label}"], m["check"] = m["check"], res
        m.setdefault("rechecks", []).append(f"2026-10-27 recheck_12.py --label {label}")
    else:
        m["check_uncommitted"], m["check"] = m.get("check"), res
        m["rechecked"] = "2026-10-27 recheck_12.py (diff applied to a fresh clone, committed)"
    meta_p.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(key, f"rule {res.get('rule_pass')}/{res.get('rule_total')} undec {res.get('rule_undecidable')}"
               f" func {res.get('func_pass')}/{res.get('func_total')}", res.get("error") or "")


if __name__ == "__main__":
    args = sys.argv[1:]
    lab = args[args.index("--label") + 1] if "--label" in args else None
    for k in [a for a in args if not a.startswith("--") and a != lab]:
        recheck(k, lab)
