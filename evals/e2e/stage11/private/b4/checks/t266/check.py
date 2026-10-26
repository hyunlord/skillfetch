#!/usr/bin/env python3
"""Hidden objective check for Stage 11 s11-t266.

Task: "`routes/media.rs`에서 `image` crate로 하는 리사이즈를 axum async 핸들러 안에서 그냥 돌리고 있어서, 동시 요청이 20개만
넘어가도 다른 CMS API까지 전부 느려져요. `spawn_blocking`으로 빼고 `Semaphore`로 동시 처리 수 제한도 걸어주세요."

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

Item a runs the session's own tests in the worktree. Items b-e run in a temp copy of the worktree built against a
patched copy of the `image` crate: the version in the copy's Cargo.lock is copied from the cargo registry cache, a probe
(probe.rs, `image::__s11_probe`) is called at the top of its private `decoder_to_image`, where every public decode entry
point converges (load_from_memory, load_from_memory_with_format, load, open, ImageReader::decode,
DynamicImage::from_decoder), and the copy's Cargo.toml gets `[patch.crates-io] image = { path = … }`; tests/zz_s11_probe.rs
is added. The probe records whether a decode runs on a tokio async worker thread (2-worker runtime; worker ids taken at
startup and from plain tasks), counts concurrent decodes, and holds each decode up to 300 ms until 48 are in flight, so an
unbounded burst of 48 resize requests shows its full width while a semaphore of size L shows at most L. The test also
samples /healthz, /api/articles and timer lateness every 25 ms during the burst. cargo runs --offline; the copy builds
into the worktree's target/ (git-ignored).

Undecidable (DESIGN §3.2.4, fixed before the pilot): when the probe cannot be applied (image version not in the cargo
cache, more than one image version, injection point not found) or is never reached although resize requests returned
200 (the session decodes by a path that bypasses decoder_to_image), items b and c (and d, e when the probe could not be
applied at all, since the hidden test is then not run) are recorded with "pass": null and
the check result is "pass": null with "undecidable": [...], unless another item failed (then "pass": false). They are
counted separately from pass and fail.

Items:
  a cargo_test          `cargo test --offline` passes in the worktree (existing and session tests)
  b offloaded           >= 1 decode reached the probe, and no decode ran on an async worker thread
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
INJECT = re.compile(r"fn\s+decoder_to_image\s*<[^>]*>\s*\([^)]*\)\s*->\s*ImageResult\s*<\s*DynamicImage\s*>\s*\{")
REGISTRY = os.path.expanduser("~/.cargo/registry/src")


def run(cmd, cwd, env, timeout=1200):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True).stdout


def lock_versions(lock_path, name):
    vs, cur = [], None
    for line in open(lock_path, encoding="utf-8"):
        m = re.match(r'name = "(.+)"', line)
        if m:
            cur = m.group(1)
        m = re.match(r'version = "(.+)"', line)
        if m and cur == name:
            vs.append(m.group(1))
            cur = None
    return vs


def instrument(copy, tmp):
    """Patch the image crate of the copy with the probe. Returns (ok, detail)."""
    lock = os.path.join(copy, "Cargo.lock")
    if not os.path.exists(lock):
        return False, "no Cargo.lock"
    vs = sorted(set(lock_versions(lock, "image")))
    if len(vs) != 1:
        return False, f"image versions in Cargo.lock: {vs}"
    srcs = [os.path.join(REGISTRY, d, f"image-{vs[0]}") for d in os.listdir(REGISTRY)
            if os.path.isdir(os.path.join(REGISTRY, d, f"image-{vs[0]}"))]
    if not srcs:
        return False, f"image {vs[0]} not in the cargo registry cache"
    img = os.path.join(tmp, f"image-{vs[0]}")
    shutil.copytree(srcs[0], img)
    dyn = os.path.join(img, "src", "images", "dynimage.rs")
    s = open(dyn, encoding="utf-8").read() if os.path.exists(dyn) else ""
    m = INJECT.search(s)
    if not m:
        return False, f"decoder_to_image not found in image {vs[0]}"
    open(dyn, "w", encoding="utf-8").write(s[:m.end()] + "\n    let _s11_probe = crate::__s11_probe::enter();" + s[m.end():])
    with open(os.path.join(img, "src", "lib.rs"), "a", encoding="utf-8") as f:
        f.write("\n#[doc(hidden)]\n#[allow(missing_docs, dead_code, clippy::all)]\npub mod __s11_probe;\n")
    shutil.copy(os.path.join(HERE, "probe.rs"), os.path.join(img, "src", "__s11_probe.rs"))
    toml = os.path.join(copy, "Cargo.toml")
    t = open(toml, encoding="utf-8").read()
    line = f'image = {{ path = "{img}" }}\n'
    t = t.replace("[patch.crates-io]\n", "[patch.crates-io]\n" + line, 1) if "[patch.crates-io]\n" in t else t + "\n[patch.crates-io]\n" + line
    open(toml, "w", encoding="utf-8").write(t)
    os.makedirs(os.path.join(copy, "tests"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "zz_s11_probe.rs"), os.path.join(copy, "tests", "zz_s11_probe.rs"))
    return True, f"image {vs[0]} patched (decoder_to_image)"


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
        items.append({"name": name, "pass": None if ok is None else bool(ok), "detail": str(detail)[:500]})

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
        inst_ok, inst = instrument(copy, tmp)
        open(os.path.join(a.outdir, "instrumented.json"), "w").write(json.dumps({"ok": inst_ok, "detail": inst}))
        r = None
        if inst_ok:
            env2 = dict(env, CARGO_TARGET_DIR=os.path.join(wt, "target"))
            rc, out = run(["cargo", "test", "--offline", "--test", "zz_s11_probe", "--", "--nocapture", "--test-threads=1"], copy, env2)
            open(os.path.join(a.outdir, "probe_test.log"), "w").write(out.replace(copy, "<copy>").replace(wt, "<wt>").replace(tmp, "<tmp>")[-20000:])
            m = re.search(r"S11_PROBE_RESULT (\{.*\})", out)
            r = json.loads(m.group(1)) if m else None
            if r:
                open(os.path.join(a.outdir, "probe.json"), "w").write(json.dumps(r, indent=1))
            else:
                err = " ".join(l.strip() for l in out.splitlines() if re.search(r"^error|panicked", l))[:300]
        if not inst_ok:  # probe could not be applied: b, c undecidable; d, e not measured either
            for name in ("b_offloaded", "c_bounded"):
                add(name, None, "undecidable: " + inst)
            for name in ("d_others_responsive", "e_output_ok"):
                add(name, None, "undecidable: " + inst)
        elif r is None:  # the session's code does not build/run with the hidden test: a real failure
            for name in ("b_offloaded", "c_bounded", "d_others_responsive", "e_output_ok"):
                add(name, False, "probe test did not run: " + err)
        else:
            st = {int(k): v for k, v in r["statuses"].items()}
            reached = r["calls"] >= 1
            if not reached and st.get(200, 0) >= 1:
                why = f"undecidable: no decode reached the probe although {st.get(200)} resizes returned 200 ({inst})"
                add("b_offloaded", None, why)
                add("c_bounded", None, why)
            else:
                add("b_offloaded", reached and r["on_worker"] == 0,
                    f"decodes={r['calls']}, on async worker={r['on_worker']} (workers={r['workers']}); {inst}")
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
    und = [i["name"] for i in items if i["pass"] is None]
    verdict = False if any(i["pass"] is False for i in items) else (None if und else True)
    result = {"task": TASK, "pass": verdict, "undecidable": und, "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"], "failed": [i["name"] for i in items if i["pass"] is False],
                      "undecidable": und}))


if __name__ == "__main__":
    main()
