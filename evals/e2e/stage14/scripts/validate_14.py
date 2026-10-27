#!/usr/bin/env python3
"""Stage 14 check validation (DESIGN §7 step 3), no model calls. On a clone of s14-a, simulates the forward order with
reference changes and runs each request's check exactly as run_14.py does (check_repo + run_task_check):
  1 landing   Stage Q R d1-landing m3 diff (check passed there), applied under web/
  2 api       Stage Q R s2-api m2 diff (27/27), under api/
  3 apitests  stage14-private/refs/test_s14_ref.py added as api/tests/test_s14_ref.py (one test per mutant behaviour)
  4 rust      stage11-private/b4/ref/t266.patch, under media/
  5 docs      stage14-private/refs/README.ref.md as README.md
  6 data      Stage Q R s2-data m1 diff, under data/
Negative cases: every check on an unchanged tree (before = after = the start, or for apitests the state after step 2).
Expected: references pass (apitests: mutants 8/8 killed), negatives fail. Also records how many mutants the step-2
reference's own tests kill. Writes stage14-private/validation/validation.json.
usage: validate_14.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
E2E = S14.parent
sys.path.insert(0, str(S14 / "scripts"))
import run_14 as r  # noqa: E402

PRIV = E2E / "stage14-private"
OUT = PRIV / "validation"
REFS = PRIV / "refs"
QR = E2E / "stageQ-private" / "runs"


def apply(wt, patch, directory):
    p = subprocess.run(["git", "-C", str(wt), "apply", "--whitespace=nowarn", f"--directory={directory}", str(patch)],
                       capture_output=True, text=True)
    assert p.returncode == 0, (patch, p.stderr[:500])


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    tmp = Path(tempfile.mkdtemp(prefix="s14v-"))
    wt = tmp / "wt"
    idx = tmp / "index"
    res = {}
    try:
        subprocess.run(["git", "clone", "-q", "--no-local", "--single-branch", "--branch", "s14-a", str(r.REPO), str(wt)], check=True)
        snaps = [r.q.snapshot(wt, idx)]
        steps = [
            (1, lambda: apply(wt, QR / "q1-d1-landing-on-m3.diff", "web")),
            (2, lambda: apply(wt, QR / "q1-s2-api-on-m2.diff", "api")),
            (3, lambda: shutil.copyfile(REFS / "test_s14_ref.py", wt / "api" / "tests" / "test_s14_ref.py")),
            (4, lambda: apply(wt, E2E / "stage11-private" / "b4" / "ref" / "t266.patch", "media")),
            (5, lambda: shutil.copyfile(REFS / "README.ref.md", wt / "README.md")),
            (6, lambda: apply(wt, QR / "q1-s2-data-on-m1.diff", "data")),
        ]
        reply = tmp / "reply.txt"
        reply.write_text("Moved the resize into tokio::task::spawn_blocking and bounded it with a tokio::sync::Semaphore.")
        for k, fn in steps:
            fn()
            snaps.append(r.q.snapshot(wt, idx))
        cases = [(f"ref-{r.TASKS[k][0]}", k, snaps[k - 1], snaps[k]) for k, _ in steps]
        cases += [(f"none-{r.TASKS[k][0]}", k, snaps[0], snaps[0]) for k in (1, 2, 4, 5, 6)]
        cases += [("none-apitests", 3, snaps[2], snaps[2]), ("refown-apitests", 3, snaps[1], snaps[2])]
        for name, k, a, b in cases:
            chk = tmp / f"chk-{name}"
            base = r.check_repo(wt, [a, b], r.TASKS[k][1], chk)
            c = r.run_task_check(k, chk, base, OUT / name, reply)
            res[name] = {"pass": c.get("pass"), "items": [(i.get("name"), i.get("pass")) for i in c.get("items") or []],
                         "metrics": {x: (c.get("metrics") or {}).get(x) for x in ("mutants_killed", "tests_before", "tests_after", "contract_pass")
                                     if x in (c.get("metrics") or {})}, "undecidable": c.get("undecidable"), "error": c.get("error")}
            print(name, res[name]["pass"], res[name]["metrics"], flush=True)
            shutil.rmtree(chk, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    (OUT / "validation.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    ok = all(v["pass"] is True for k, v in res.items() if k.startswith("ref-")) and \
        all(v["pass"] is False for k, v in res.items() if k.startswith("none-")) and res["ref-apitests"]["metrics"].get("mutants_killed") == 8
    print("VALIDATION", "OK" if ok else "NOT OK")


if __name__ == "__main__":
    main()
