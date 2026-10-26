#!/usr/bin/env python3
"""Hidden objective check for Stage 11 s11-t266.

Task: "`routes/media.rs`에서 `image` crate로 하는 리사이즈를 axum async 핸들러 안에서 그냥 돌리고 있어서, 동시 요청이 20개만
넘어가도 다른 CMS API까지 전부 느려져요. `spawn_blocking`으로 빼고 `Semaphore`로 동시 처리 수 제한도 걸어주세요."

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

Item a runs the session's own tests in the worktree. Items b-e run in a temp copy of the worktree in which every
`image::load_from_memory(…)` / `load_from_memory_with_format(…)` call in the library (src/, not main.rs or src/bin) is
wrapped by a probe (probe.rs, added as `pub mod __s11_probe`), and tests/zz_s11_probe.rs is added. The probe records
whether a decode runs on a tokio async worker thread (2-worker runtime; worker ids taken at startup and from plain
tasks), counts concurrent decodes, and holds each decode up to 300 ms until 48 are in flight, so an unbounded burst of
48 resize requests shows its full width while a semaphore of size L shows at most L. The test also samples /healthz,
/api/articles and timer lateness every 25 ms during the burst. cargo runs --offline; the copy builds into the
worktree's target/ (git-ignored).

Items:
  a cargo_test          `cargo test --offline` passes in the worktree (existing and session tests)
  b offloaded           probe found, >= 1 decode, and no decode ran on an async worker thread
  c bounded             max concurrent decodes during the 48-request burst is between 1 and 32; every response is 200,
                        429 or 503, and at least one is 200
  d others_responsive   during the burst: /healthz and /api/articles all succeed, max latency < 200 ms, timer
                        lateness < 200 ms
  e output_ok           a single 1600x1200 -> 400x400 request returns 200 with 400x300; every 200 in the burst decodes
                        to at most 400x400
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TASK = "t266"
HERE = os.path.dirname(os.path.abspath(__file__))
CALL = re.compile(r"(?:(?:::)?\bimage\s*::\s*)?\b(load_from_memory_with_format|load_from_memory)\s*\(")


def run(cmd, cwd, env, timeout=1200):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True).stdout


def strip_comments_mask(src):
    """Positions inside // or /* */ comments or string literals (so calls there are not rewritten)."""
    mask = bytearray(len(src))
    i, n = 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j == -1 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
        elif src[i] == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            j += 1
        else:
            i += 1
            continue
        for k in range(i, min(j, n)):
            mask[k] = 1
        i = j
    return mask


def instrument(copy):
    """Wrap decode calls in src/ (library only). Returns list of (file, count)."""
    done = []
    for dp, dns, fns in os.walk(os.path.join(copy, "src")):
        dns[:] = [d for d in dns if d != "bin"]
        for fn in fns:
            p = os.path.join(dp, fn)
            if not fn.endswith(".rs") or os.path.relpath(p, copy) == os.path.join("src", "main.rs"):
                continue
            src = open(p, encoding="utf-8").read()
            mask = strip_comments_mask(src)
            out, last, cnt = [], 0, 0
            for m in CALL.finditer(src):
                if mask[m.start()]:
                    continue
                # skip definitions / paths that are not calls of the image crate function (e.g. `fn load_from_memory(`)
                if re.search(r"\bfn\s+$", src[max(0, m.start() - 10):m.start()]):
                    continue
                wrap = "probed2" if m.group(1) == "load_from_memory_with_format" else "probed"
                out.append(src[last:m.start()])
                out.append(f"crate::__s11_probe::{wrap}(::image::{m.group(1)})(")
                last = m.end()
                cnt += 1
            if cnt:
                out.append(src[last:])
                open(p, "w", encoding="utf-8").write("".join(out))
                done.append((os.path.relpath(p, copy), cnt))
    lib = os.path.join(copy, "src", "lib.rs")
    with open(lib, "a", encoding="utf-8") as f:
        f.write("\n#[doc(hidden)]\n#[allow(dead_code)]\npub mod __s11_probe;\n")
    shutil.copy(os.path.join(HERE, "probe.rs"), os.path.join(copy, "src", "__s11_probe.rs"))
    os.makedirs(os.path.join(copy, "tests"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "zz_s11_probe.rs"), os.path.join(copy, "tests", "zz_s11_probe.rs"))
    return done


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
        items.append({"name": name, "pass": bool(ok), "detail": str(detail)[:500]})

    env = dict(os.environ)
    env["CARGO_TERM_COLOR"] = "never"
    status0 = git(wt, "status", "--porcelain=v1", "--untracked-files=all")
    lock = os.path.join(wt, "Cargo.lock")
    lock_bytes = open(lock, "rb").read() if os.path.exists(lock) else None
    tmp = tempfile.mkdtemp(prefix="s11chk-")
    try:
        rc, out = run(["cargo", "test", "--offline", "-q"], wt, env)
        passed = sum(map(int, re.findall(r"test result: ok\. (\d+) passed", out)))
        add("a_cargo_test", rc == 0, f"rc={rc}; {passed} tests passed" + ("" if rc == 0 else " | " + " ".join(
            l.strip() for l in out.splitlines() if re.search(r"FAILED|panicked|^error", l))[:300]))

        copy = os.path.join(tmp, "w")
        shutil.copytree(wt, copy, symlinks=True, ignore=shutil.ignore_patterns("target", ".git"))
        wrapped = instrument(copy)
        open(os.path.join(a.outdir, "instrumented.json"), "w").write(json.dumps(wrapped))
        env2 = dict(env, CARGO_TARGET_DIR=os.path.join(wt, "target"))
        rc, out = run(["cargo", "test", "--offline", "--test", "zz_s11_probe", "--", "--nocapture", "--test-threads=1"], copy, env2)
        open(os.path.join(a.outdir, "probe_test.log"), "w").write(out.replace(copy, "<copy>").replace(wt, "<wt>")[-20000:])
        m = re.search(r"S11_PROBE_RESULT (\{.*\})", out)
        r = json.loads(m.group(1)) if m else None
        if r:
            open(os.path.join(a.outdir, "probe.json"), "w").write(json.dumps(r, indent=1))
        why = None if r else ("probe test did not run: " + " ".join(l.strip() for l in out.splitlines() if re.search(r"^error|panicked", l))[:300])
        if not wrapped:
            why = "no image::load_from_memory call found in the library (probe not inserted)"
        if why:
            for name in ("b_offloaded", "c_bounded", "d_others_responsive", "e_output_ok"):
                add(name, False, why)
        else:
            st = {int(k): v for k, v in r["statuses"].items()}
            add("b_offloaded", r["calls"] >= 1 and r["on_worker"] == 0,
                f"decodes={r['calls']}, on async worker={r['on_worker']} (workers={r['workers']}); probe in {wrapped}")
            add("c_bounded", 1 <= r["max_concurrency"] <= 32 and set(st) <= {200, 429, 503} and st.get(200, 0) >= 1,
                f"max concurrent decodes={r['max_concurrency']} for a burst of 48; statuses={st}; burst {r['burst_ms']} ms")
            add("d_others_responsive", r["other_failed"] == 0 and r["other_requests"] > 0 and r["other_latency_max_ms"] < 200
                and r["timer_lateness_max_ms"] < 200,
                f"other requests={r['other_requests']} failed={r['other_failed']} max latency={r['other_latency_max_ms']} ms, "
                f"timer lateness max={r['timer_lateness_max_ms']} ms")
            add("e_output_ok", r["single_status"] == 200 and r["single_dims"] == [400, 300] and r["dims_ok"],
                f"single: status={r['single_status']} dims={r['single_dims']}; burst 200s within 400x400={r['dims_ok']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if lock_bytes is not None and open(lock, "rb").read() != lock_bytes:
            open(lock, "wb").write(lock_bytes)
    if git(wt, "status", "--porcelain=v1", "--untracked-files=all") != status0:
        print("warning: worktree status changed during check", file=sys.stderr)
    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"], "failed": [i["name"] for i in items if not i["pass"]]}))


if __name__ == "__main__":
    main()
