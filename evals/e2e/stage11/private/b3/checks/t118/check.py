#!/usr/bin/env python3
"""Hidden objective check for Stage 11 s11-t118.

Task: "javadoc for PaymentReconciliationService, reviewer flagged missing @throws on reconcileBatch"

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

JDK: /opt/homebrew/opt/openjdk/bin first on PATH (keg-only openjdk; nothing else changed).

Items:
  a build_test        `make test` passes (javac -Xlint:all -Werror, then the test main)
  b doclint_all       `javadoc --release 21 -Xdoclint:all -Werror` over src/main/java passes (no missing comments,
                      @param/@return/@throws, no broken references or HTML)
  c code_unchanged    no .java file removed; every .java file's token stream without comments equals the base; new
                      .java files only package-info.java with no code beyond the package declaration
  d throws_complete   the Javadoc of reconcileBatch has an @throws/@exception tag with a description for each of
                      CurrencyMismatchException, UnmatchedAmountException, DuplicateTransactionException,
                      IllegalArgumentException, IllegalStateException (simple or qualified names; NullPointerException
                      optional)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TASK = "t118"
JDK = "/opt/homebrew/opt/openjdk/bin"
SRC = "src/main/java"
SERVICE = "src/main/java/com/acme/payments/reconciliation/PaymentReconciliationService.java"
REQUIRED = ["CurrencyMismatchException", "UnmatchedAmountException", "DuplicateTransactionException",
            "IllegalArgumentException", "IllegalStateException"]


def lex(src):
    """Java tokens: ('comment', text) / ('doc', text) / ('str', text) / ('word', text) / ('punct', ch)."""
    toks, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
            toks.append(("comment", src[i:j]))
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            toks.append(("doc" if src.startswith("/**", i) and not src.startswith("/**/", i) else "comment", src[i:j]))
            i = j
        elif src.startswith('"""', i):
            j = src.find('"""', i + 3)
            while j != -1 and src[j - 1] == "\\":
                j = src.find('"""', j + 1)
            j = n if j == -1 else j + 3
            toks.append(("str", src[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            toks.append(("str", src[i:j + 1]))
            i = j + 1
        elif c.isalnum() or c in "_$" or ord(c) > 127:
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "_$." and not src.startswith("...", j) or ord(src[j]) > 127):
                j += 1
            toks.append(("word", src[i:j]))
            i = j
        else:
            toks.append(("punct", c))
            i += 1
    return toks


def code(toks):
    return [t for t in toks if t[0] not in ("comment", "doc")]


def git(wt, *args, binary=False):
    p = subprocess.run(["git", "-C", wt, *args], capture_output=True, check=True)
    return p.stdout if binary else p.stdout.decode()


def sh(cmd, cwd, env, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def reconcile_doc(src):
    """Javadoc text directly before the reconcileBatch method declaration (annotations/modifiers allowed between)."""
    toks = lex(src)
    for k, (kind, text) in enumerate(toks):
        if kind == "word" and text == "reconcileBatch" and k + 1 < len(toks) and toks[k + 1] == ("punct", "("):
            j = k - 1
            while j >= 0 and toks[j][0] != "doc" and not (toks[j][0] == "punct" and toks[j][1] in ";{}"):
                j -= 1
            return toks[j][1] if j >= 0 and toks[j][0] == "doc" else None
    return None


def throws_tags(doc):
    body = re.sub(r"^\s*/\*\*|\*/\s*$", "", doc)
    lines = [re.sub(r"^\s*\*\s?", "", l) for l in body.splitlines()]
    text = "\n".join(lines)
    tags = {}
    for m in re.finditer(r"@(?:throws|exception)\s+([\w.$]+)([\s\S]*?)(?=\n\s*@\w|\Z)", text):
        tags[m.group(1).split(".")[-1]] = " ".join(m.group(2).split())
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("outdir")
    ap.add_argument("--reply", default=None)  # ignored
    ap.add_argument("--base", default="s11-a")
    a = ap.parse_args()
    wt = os.path.realpath(a.worktree)
    os.makedirs(a.outdir, exist_ok=True)
    items = []

    def add(name, ok, detail):
        items.append({"name": name, "pass": bool(ok), "detail": str(detail)[:400]})

    env = dict(os.environ)
    env["PATH"] = f"{JDK}:{env.get('PATH', '')}"
    env.pop("JAVA_HOME", None)
    status0 = git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
    had_build = os.path.isdir(os.path.join(wt, "build"))
    tmp = tempfile.mkdtemp(prefix="s11chk-")
    try:
        rc, out = sh(["make", "test"], wt, env)
        add("a_build_test", rc == 0, f"make test rc={rc}" + (" | " + out.strip()[-250:] if rc else " | " + out.strip().splitlines()[-1][:120]))

        srcs = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(wt, SRC)) for f in fs if f.endswith(".java"))
        rc, out = sh(["javadoc", "--release", "21", "-quiet", "-Xdoclint:all", "-Werror", "-d", os.path.join(tmp, "docs"), *srcs], wt, env)
        msgs = [l.replace(wt + "/", "") for l in out.splitlines() if re.search(r": (warning|error):", l)]
        add("b_doclint_all", rc == 0, f"rc={rc}; {len(msgs)} messages" + ("; " + " | ".join(msgs[:5]) if msgs else ""))

        base_files = {p for p in git(wt, "ls-tree", "-r", "--name-only", a.base).splitlines() if p.endswith(".java")}
        listed = git(wt, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
        cur_files = {p for p in listed if p.endswith(".java") and os.path.isfile(os.path.join(wt, p))}
        problems = [f"removed {p}" for p in sorted(base_files - cur_files)]
        for p in sorted(cur_files - base_files):
            toks = code(lex(open(os.path.join(wt, p), encoding="utf-8", errors="replace").read()))
            if not (p.endswith("package-info.java") and [t[1] for t in toks][:1] == ["package"] and len(toks) == 3):
                problems.append(f"added {p}")
        for p in sorted(base_files & cur_files):
            old = git(wt, "show", f"{a.base}:{p}", binary=True).decode("utf-8", "replace")
            new = open(os.path.join(wt, p), encoding="utf-8", errors="replace").read()
            if code(lex(old)) != code(lex(new)):
                problems.append(f"code changed in {p}")
        add("c_code_unchanged", not problems, "; ".join(problems) if problems else f"{len(base_files)} .java files, code identical modulo comments")

        path = os.path.join(wt, SERVICE)
        doc = reconcile_doc(open(path, encoding="utf-8").read()) if os.path.isfile(path) else None
        if doc is None:
            add("d_throws_complete", False, "no Javadoc before reconcileBatch")
        else:
            tags = throws_tags(doc)
            missing = [x for x in REQUIRED if x not in tags]
            empty = [x for x in REQUIRED if x in tags and not tags[x]]
            add("d_throws_complete", not missing and not empty,
                f"documented={sorted(tags)}" + (f"; missing={missing}" if missing else "") + (f"; no description={empty}" if empty else ""))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if not had_build:
            shutil.rmtree(os.path.join(wt, "build"), ignore_errors=True)
    if git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored") != status0:
        print("warning: worktree status changed during check", file=sys.stderr)
    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"], "failed": [i["name"] for i in items if not i["pass"]]}))


if __name__ == "__main__":
    main()
