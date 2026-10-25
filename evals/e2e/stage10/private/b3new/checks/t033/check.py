#!/usr/bin/env python3
"""Hidden objective check for t033 (Google Docs redirect links in sanitizeHtml).

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

The worktree is expected to have had `npm ci` run already. Writes
<outdir>/check.json and prints a one-line JSON summary.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HIDDEN_SRC = os.path.join(HERE, "t033_hidden.test.ts")
HIDDEN_REL = os.path.join("tests", "t033_hidden.test.ts")
TOOLBAR = "components/editor/Toolbar.tsx"
TIMEOUT = 600
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run(cmd, cwd):
    env = dict(os.environ, CI="1", FORCE_COLOR="0", NO_COLOR="1")
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=TIMEOUT)
        return p.returncode, ANSI.sub("", p.stdout.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def git_show(wt, base, path):
    p = subprocess.run(["git", "-C", wt, "show", f"{base}:{path}"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout if p.returncode == 0 else None


def read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def tail(text, n=160):
    text = " ".join(text.split())
    return text[-n:]


def vitest_summary(out):
    m = re.findall(r"Tests\s+([^\n]+)", out)
    return m[-1].strip() if m else tail(out)


def check_typecheck(wt):
    code, out = run(["npx", "--no-install", "tsc", "--noEmit"], wt)
    if code == 0:
        return True, "tsc ok"
    errs = len(re.findall(r"error TS\d+", out))
    return False, f"tsc exit {code}, {errs} errors: {tail(out, 120)}"


def check_tests(wt):
    code, out = run(["npx", "--no-install", "vitest", "run",
                     "--exclude", "**/t033_hidden.test.ts"], wt)
    return code == 0, f"exit {code}: {vitest_summary(out)}"


def check_hidden(wt):
    dst = os.path.join(wt, HIDDEN_REL)
    backup = read_bytes(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(HIDDEN_SRC, dst)
    try:
        code, out = run(["npx", "--no-install", "vitest", "run", HIDDEN_REL], wt)
    finally:
        if backup is not None:
            with open(dst, "wb") as f:
                f.write(backup)
        else:
            try:
                os.remove(dst)
            except OSError:
                pass
    detail = f"exit {code}: {vitest_summary(out)}"
    if code != 0:
        failed = re.findall(r"(?:FAIL|×|✗)\s+[^\n]*?t033_hidden\.test\.ts\s*>\s*([^\n]+)", out)
        if failed:
            names = sorted({f.split(">")[-1].strip()[:50] for f in failed})
            detail += " | failed: " + "; ".join(names[:4])
    return code == 0, detail[:300]


def check_no_new_packages(wt, base):
    base_pkg = git_show(wt, base, "package.json")
    cur_pkg = read_bytes(os.path.join(wt, "package.json"))
    if base_pkg is None or cur_pkg is None:
        return False, "package.json missing (base or worktree)"
    try:
        b, c = json.loads(base_pkg), json.loads(cur_pkg)
    except ValueError as e:
        return False, f"package.json unparsable: {e}"
    problems = []
    for key in ("dependencies", "devDependencies"):
        if (b.get(key) or {}) != (c.get(key) or {}):
            problems.append(f"{key} changed")
    base_lock = git_show(wt, base, "package-lock.json")
    cur_lock = read_bytes(os.path.join(wt, "package-lock.json"))
    if base_lock is None or cur_lock is None:
        problems.append("package-lock.json missing")
    elif base_lock != cur_lock:
        problems.append("package-lock.json changed")
    return (not problems), ("deps and lockfile unchanged" if not problems else ", ".join(problems))


def check_toolbar(wt, base):
    b = git_show(wt, base, TOOLBAR)
    c = read_bytes(os.path.join(wt, TOOLBAR))
    if b is None:
        return False, "Toolbar.tsx missing at base"
    if c is None:
        return False, "Toolbar.tsx deleted"
    return b == c, ("Toolbar.tsx unchanged" if b == c else "Toolbar.tsx modified")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("outdir")
    ap.add_argument("--reply", default=None)  # ignored
    ap.add_argument("--base", default="s10-a")
    a = ap.parse_args()
    wt = os.path.abspath(a.worktree)
    os.makedirs(a.outdir, exist_ok=True)

    items = []

    def add(name, fn, *args):
        try:
            ok, detail = fn(*args)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"check error: {type(e).__name__}: {e}"[:200]
        items.append({"name": name, "pass": bool(ok), "detail": detail})

    add("typecheck", check_typecheck, wt)
    add("tests_pass", check_tests, wt)
    add("hidden_tests", check_hidden, wt)
    add("no_new_packages", check_no_new_packages, wt, a.base)
    add("toolbar_untouched", check_toolbar, wt, a.base)

    result = {"task": "t033", "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"task": "t033", "pass": result["pass"],
                      "items": {i["name"]: i["pass"] for i in items}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
