#!/usr/bin/env python3
"""Build plans-blind/ for s1b-fa-tags-plan: per session <code>/PLAN.md + <code>/impl.diff (code changes without
PLAN.md, lockfiles, env noise). Mentions that could reveal the condition (skill names, skillfetch, router tool
names) are replaced by [redacted] in every condition alike. Prints counts only; mapping goes to plans-key.jsonl.
Also sets one fixed mtime on every file under screens-blind/ and plans-blind/."""
import json
import os
import random
import re
import secrets
import subprocess
from pathlib import Path

S1B = Path(__file__).resolve().parents[1]
TASK = "s1b-fa-tags-plan"
OUT, KEY = S1B / "plans-blind" / TASK, S1B / "plans-key.jsonl"
LEAK = re.compile(r"(?i)skillfetch|search_skills|resolve_set|load_skills|profile_repo|writing[-_ ]plans|<E2 plugin>|"
                  r"\bskills?\b|router skill|precedence header")
SKIP = re.compile(r"(^|/)(PLAN\.md|package-lock\.json|bun\.lock|uv\.lock|\.ignore)$|(^|/)\.omc/")
GRAFT = {"+", "+# graft's local graph cache — regenerable, not committed (run `graft build`).", "+/graft/"}


def redact(text):
    n = len(LEAK.findall(text))
    return LEAK.sub("[redacted]", text), n


def impl_diff(diff_path: Path) -> str:
    out = []
    for ch in re.split(r"(?=^diff --git )", diff_path.read_text(), flags=re.M):
        if not ch.startswith("diff --git"):
            continue
        path = re.match(r"diff --git a/(.*?) b/(.*)$", ch.split("\n", 1)[0]).group(2)
        if SKIP.search(path):
            continue
        lines = [ln for ln in ch.split("\n") if not ln.startswith("index ")]
        if path == ".gitignore":
            lines = [ln for ln in lines if ln not in GRAFT]
            if not any(ln[:1] in "+-" and not ln.startswith(("+++", "---")) for ln in lines):
                continue
        out.append("\n".join(lines))
    return "".join(out)


def main():
    assert not OUT.exists() and not KEY.exists(), "plans-blind already built"
    metas = sorted((S1B / "runs").glob(f"*/{TASK}-r*.meta.json"))
    random.SystemRandom().shuffle(metas)
    rows, n_red, n_missing = [], 0, 0
    for mp in metas:
        meta = json.loads(mp.read_text())
        wt = Path(meta["worktree"])
        files = subprocess.run(["git", "-C", str(wt), "ls-files", "--others", "--cached", "--exclude-standard"],
                               capture_output=True, text=True).stdout.splitlines()
        plans = sorted(p for p in files if Path(p).name == "PLAN.md")
        code = secrets.token_hex(4)
        d = OUT / code
        d.mkdir(parents=True)
        if plans:
            plan, k1 = redact((wt / plans[0]).read_text(errors="replace"))
        else:
            plan, k1 = "(PLAN.md not found in the worktree)\n", 0
            n_missing += 1
        diff, k2 = redact(impl_diff(Path(str(mp)[: -len(".meta.json")] + ".diff")))
        (d / "PLAN.md").write_text(plan)
        (d / "impl.diff").write_text(diff)
        n_red += k1 + k2
        rows.append(json.dumps({"code": code, "task": TASK, "cond": meta["cond"], "rep": meta["rep"],
                                "plan_path": plans[0] if plans else None, "redactions": k1 + k2}))
    KEY.write_text("\n".join(sorted(rows)) + "\n")
    t = 1792656000
    for root in (S1B / "screens-blind", S1B / "plans-blind"):
        if root.exists():
            for p in sorted(root.rglob("*"), reverse=True):
                os.utime(p, (t, t))
            os.utime(root, (t, t))
    print(f"plans-blind: {len(rows)} sets, PLAN.md missing in {n_missing}, total redactions {n_red}")


if __name__ == "__main__":
    main()
