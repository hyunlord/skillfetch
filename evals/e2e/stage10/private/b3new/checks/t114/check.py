#!/usr/bin/env python3
"""Hidden objective check for t114.

Task: "add crate-level docs to telemetry-codec/src/lib.rs, explain the wire
packet format bytes"

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

Items:
  a cargo_test        `cargo test --workspace` passes (includes doctests)
  b cargo_doc         `cargo doc --no-deps -p telemetry-codec` with RUSTDOCFLAGS=-D warnings
  c code_unchanged    no .rs file added/removed; every .rs file's token stream with
                      comments/whitespace (and doc / lint-level attributes) removed
                      equals the base
  d crate_docs_present lib.rs crate-level docs (//!, /*! */, #![doc = ...],
                      #![doc = include_str!(...)]) total >= 15 non-blank lines
  e docs_explain_bytes crate-level doc text mentions every required term group

The worktree is left as found (only the git-ignored target/ dir is touched;
Cargo.lock is restored byte-for-byte if cargo rewrote it).
"""
import argparse
import json
import os
import re
import subprocess
import sys

TASK = "t114"
LIB_RS = "telemetry-codec/src/lib.rs"
MIN_DOC_LINES = 15
CARGO_TIMEOUT = 900

# Required term groups for item e: any regex in a group satisfies the group.
# Matched case-insensitively against the crate-level doc text.
TERM_GROUPS = [
    ("magic", [r"0x54\b", r"0x43\b", r"\b54\s*43\b", r"0x5443\b", r"0x4354\b", r"\btc\b"]),
    ("version", [r"version"]),
    ("flags", [r"flag"]),
    ("sensor", [r"sensor"]),
    ("seq", [r"seq"]),
    ("timestamp", [r"timestamp", r"time\s*stamp"]),
    ("length", [r"payload_len", r"length", r"\blen\b"]),
    ("payload", [r"payload"]),
    ("crc", [r"crc", r"checksum"]),
    ("little_endian", [r"little[\s_-]*endian", r"\ble\b", r"le_bytes",
                       r"\b[ui](16|32|64)[\s_-]?le\b"]),
    ("crc_variant", [r"ccitt", r"0x1021\b", r"ibm[\s_-]*3740"]),
    ("header_20", [r"\b20\b", r"\b0x14\b", r"\btwenty\b", r"\b19\b"]),
]

LINT_ATTRS = {"warn", "allow", "deny", "forbid", "expect"}


# --------------------------------------------------------------------------
# Minimal Rust lexer: comments, string/char literals, idents, numbers, punct.
# --------------------------------------------------------------------------
RAW_STR_RE = re.compile(r'(br|cr|r)(#*)"')
IDENT_START = re.compile(r"[A-Za-z_]")


def _is_ident_char(ch):
    return ch.isalnum() or ch == "_"


def lex(src):
    toks = []  # (kind, text)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
            toks.append(("comment", src[i:j]))
            i = j
            continue
        if src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth += 1
                    j += 2
                elif src.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            toks.append(("comment", src[i:j]))
            i = j
            continue
        m = RAW_STR_RE.match(src, i)
        if m:
            hashes = m.group(2)
            start = m.end()
            end = src.find('"' + hashes, start)
            j = n if end == -1 else end + 1 + len(hashes)
            toks.append(("str", src[i:j]))
            i = j
            continue
        if c == '"' or (c in "bc" and i + 1 < n and src[i + 1] == '"'):
            j = i + (1 if c == '"' else 2)
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            j += 1
            toks.append(("str", src[i:j]))
            i = j
            continue
        if c == "'" or (c == "b" and i + 1 < n and src[i + 1] == "'"):
            k = i + (1 if c == "'" else 2)
            if k < n and src[k] == "\\":
                j = k + 2
                while j < n and src[j] != "'":
                    j += 1
                toks.append(("char", src[i:j + 1]))
                i = j + 1
                continue
            if k + 1 < n and src[k + 1] == "'":
                toks.append(("char", src[i:k + 2]))
                i = k + 2
                continue
            # lifetime / label
            toks.append(("punct", "'"))
            i += 1
            continue
        if IDENT_START.match(c) or (ord(c) > 127 and c.isalpha()):
            j = i + 1
            while j < n and _is_ident_char(src[j]):
                j += 1
            toks.append(("ident", src[i:j]))
            i = j
            continue
        if c.isdigit():
            j = i + 1
            while j < n and _is_ident_char(src[j]):
                j += 1
            toks.append(("num", src[i:j]))
            i = j
            continue
        toks.append(("punct", c))
        i += 1
    return toks


def strip_attrs(toks):
    """Drop comments, #[doc..]/#![doc..] attrs and inner lint-level attrs."""
    out = []
    i, n = 0, len(toks)
    while i < n:
        kind, text = toks[i]
        if kind == "comment":
            i += 1
            continue
        if kind == "punct" and text == "#":
            j = i + 1
            inner = j < n and toks[j] == ("punct", "!")
            if inner:
                j += 1
            if j + 1 < n and toks[j] == ("punct", "[") and toks[j + 1][0] == "ident":
                name = toks[j + 1][1]
                if name == "doc" or (inner and name in LINT_ATTRS):
                    depth, k = 0, j
                    while k < n:
                        if toks[k] == ("punct", "["):
                            depth += 1
                        elif toks[k] == ("punct", "]"):
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    i = k + 1
                    continue
        out.append(toks[i])
        i += 1
    return out


# --------------------------------------------------------------------------
# Crate-level doc extraction from lib.rs
# --------------------------------------------------------------------------
def unescape_str_literal(lit):
    m = RAW_STR_RE.match(lit)
    if m:
        hashes = m.group(2)
        body = lit[m.end():]
        if hashes:
            body = body[: -len(hashes)]
        return body[:-1]
    if lit[0] in "bc":
        lit = lit[1:]
    body = lit[1:-1]
    out, i = [], 0
    simple = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nx = body[i + 1]
            if nx == "\n":  # line continuation: skip newline + leading ws
                i += 2
                while i < len(body) and body[i] in " \t\r\n":
                    i += 1
                continue
            if nx in simple:
                out.append(simple[nx])
                i += 2
                continue
            if nx == "x" and i + 3 < len(body):
                out.append(chr(int(body[i + 2:i + 4], 16)))
                i += 4
                continue
            if nx == "u":
                end = body.find("}", i)
                try:
                    out.append(chr(int(body[i + 3:end].replace("_", ""), 16)))
                except ValueError:
                    pass
                i = end + 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def crate_doc_text(lib_path):
    """Return (text, sources, problems)."""
    with open(lib_path, encoding="utf-8") as f:
        src = f.read()
    toks = lex(src)
    parts, sources, problems = [], set(), []
    for kind, text in toks:
        if kind != "comment":
            continue
        if text.startswith("//!"):
            line = text[3:]
            if line.startswith(" "):
                line = line[1:]
            parts.append(line)
            sources.add("//!")
        elif text.startswith("/*!"):
            parts.extend(text[3:-2].splitlines())
            sources.add("/*!")
    # #![doc = "..."] / #![doc = include_str!("...")]
    i, n = 0, len(toks)
    while i < n:
        if (toks[i] == ("punct", "#") and i + 4 < n and toks[i + 1] == ("punct", "!")
                and toks[i + 2] == ("punct", "[") and toks[i + 3] == ("ident", "doc")
                and toks[i + 4] == ("punct", "=")):
            j = i + 5
            if j < n and toks[j][0] == "str":
                parts.extend(unescape_str_literal(toks[j][1]).splitlines())
                sources.add("#![doc=str]")
            elif (j + 3 < n and toks[j] == ("ident", "include_str") and toks[j + 1] == ("punct", "!")
                  and toks[j + 2] == ("punct", "(") and toks[j + 3][0] == "str"):
                rel = unescape_str_literal(toks[j + 3][1])
                path = os.path.normpath(os.path.join(os.path.dirname(lib_path), rel))
                try:
                    with open(path, encoding="utf-8") as f:
                        parts.extend(f.read().splitlines())
                    sources.add("include_str")
                except OSError as e:
                    problems.append(f"include_str unreadable: {rel} ({e.strerror})")
            else:
                problems.append("unsupported #![doc = ...] form")
            i = j
            continue
        i += 1
    return "\n".join(parts), sorted(sources), problems


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def git(wt, *args, check=True):
    r = subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_bytes(wt, *args):
    r = subprocess.run(["git", "-C", wt, *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return r.stdout


def run_cargo(wt, args, extra_env=None):
    env = dict(os.environ)
    env["CARGO_TERM_COLOR"] = "never"
    if extra_env:
        env.update(extra_env)
    try:
        r = subprocess.run(["cargo", *args], cwd=wt, capture_output=True, text=True,
                           env=env, timeout=CARGO_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0, out


def tail_detail(out, pat):
    lines = [l.strip() for l in out.splitlines() if re.search(pat, l)]
    return "; ".join(lines[:4])[:300]


# --------------------------------------------------------------------------
# items
# --------------------------------------------------------------------------
def item_cargo_test(wt):
    ok, out = run_cargo(wt, ["test", "--workspace", "--offline"])
    if ok:
        results = re.findall(r"test result: ok\. (\d+) passed", out)
        return True, f"ok ({sum(map(int, results))} tests in {len(results)} suites)"
    det = (tail_detail(out, r"\.\.\. FAILED|^error|panicked|test result: FAILED")
           or out.strip()[-300:])
    return False, det


def item_cargo_doc(wt):
    ok, out = run_cargo(wt, ["doc", "--no-deps", "--offline", "-p", "telemetry-codec"],
                        {"RUSTDOCFLAGS": "-D warnings"})
    if ok:
        return True, "ok"
    return False, tail_detail(out, r"^(error|warning)") or out.strip()[-300:]


def item_code_unchanged(wt, base):
    base_files = {p for p in git(wt, "ls-tree", "-r", "--name-only", base).splitlines()
                  if p.endswith(".rs")}
    listed = git(wt, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    cur_files = {p for p in listed if p.endswith(".rs") and os.path.isfile(os.path.join(wt, p))}
    added = sorted(cur_files - base_files)
    removed = sorted(base_files - cur_files)
    if added or removed:
        return False, f"added={added} removed={removed}"
    changed = []
    for p in sorted(base_files):
        old = git_bytes(wt, "show", f"{base}:{p}").decode("utf-8", "replace")
        with open(os.path.join(wt, p), encoding="utf-8", errors="replace") as f:
            new = f.read()
        if strip_attrs(lex(old)) != strip_attrs(lex(new)):
            changed.append(p)
    if changed:
        return False, f"code changed in: {changed}"
    return True, f"{len(base_files)} .rs files, code identical modulo comments/doc attrs"


def item_docs_present(wt):
    lib = os.path.join(wt, LIB_RS)
    if not os.path.isfile(lib):
        return False, "lib.rs missing", ""
    text, sources, problems = crate_doc_text(lib)
    nonblank = [l for l in text.splitlines() if l.strip()]
    ok = len(nonblank) >= MIN_DOC_LINES
    det = f"{len(nonblank)} non-blank crate doc lines (need {MIN_DOC_LINES}); sources={sources}"
    if problems:
        det += f"; {problems}"
    return ok, det, text


def item_docs_explain(text):
    low = text.lower()
    missing = [name for name, pats in TERM_GROUPS
               if not any(re.search(p, low) for p in pats)]
    if missing:
        return False, f"missing term groups: {missing}"
    return True, f"all {len(TERM_GROUPS)} term groups present"


# --------------------------------------------------------------------------
def snapshot(wt):
    status = git(wt, "status", "--porcelain=v1", "--untracked-files=all", check=False)
    lock = os.path.join(wt, "Cargo.lock")
    lock_bytes = open(lock, "rb").read() if os.path.isfile(lock) else None
    return status, lock_bytes


def restore(wt, snap):
    _, lock_bytes = snap
    lock = os.path.join(wt, "Cargo.lock")
    if lock_bytes is not None:
        cur = open(lock, "rb").read() if os.path.isfile(lock) else None
        if cur != lock_bytes:
            with open(lock, "wb") as f:
                f.write(lock_bytes)


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

    def add(name, ok, detail):
        items.append({"name": name, "pass": bool(ok), "detail": detail})

    try:
        git(wt, "rev-parse", "--verify", f"{a.base}^{{commit}}")
    except RuntimeError as e:
        add("setup", False, str(e))
        a.base = None

    snap = snapshot(wt)
    try:
        add("a_cargo_test", *item_cargo_test(wt))
        add("b_cargo_doc", *item_cargo_doc(wt))
    finally:
        restore(wt, snap)

    if a.base:
        try:
            add("c_code_unchanged", *item_code_unchanged(wt, a.base))
        except Exception as e:  # noqa: BLE001
            add("c_code_unchanged", False, f"error: {e}")
    try:
        ok_d, det_d, text = item_docs_present(wt)
    except Exception as e:  # noqa: BLE001
        ok_d, det_d, text = False, f"error: {e}", ""
    add("d_crate_docs_present", ok_d, det_d)
    add("e_docs_explain_bytes", *item_docs_explain(text))

    after_status, _ = snapshot(wt)
    if after_status != snap[0]:
        print("warning: worktree status changed during check", file=sys.stderr)

    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"],
                      "failed": [i["name"] for i in items if not i["pass"]]}))


if __name__ == "__main__":
    main()
