#!/usr/bin/env python3
"""Hidden objective check for Stage 11 s11-t160.

Task: "add ko build + push for cmd/tracker-ingest to the release makefile target"

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

`make release` is run for real with REGISTRY=registry.check.local/fleet VERSION=v9.9.9-check and PATH shims for `ko`
and `docker` that only record their arguments and environment (nothing is built or pushed). `go` is real, except that a
wrapper maps `go run github.com/google/ko[@v]` to the ko shim. GOPROXY=off, GOTOOLCHAIN=local.

Items:
  a go_build_vet_test   `go build ./...`, `go vet ./...`, `go test ./...` pass
  b release_runs_ko     `make release` exits 0 and calls ko build/publish for cmd/tracker-ingest (relative path, import
                        path or ko:// form) with push not disabled (--push=false, -L/--local, --tarball, --oci-layout-path)
                        and KO_DOCKER_REPO set
  c registry_follows    the ko call's KO_DOCKER_REPO starts with the REGISTRY passed to make (not hard-coded)
  d existing_steps      the existing API image steps still run with the same arguments (docker build ... -t
                        <REGISTRY>/tracker-api:<VERSION> . and docker push of that tag) and go vet/test still run
  e ko_failure_fails    with the ko shim exiting 1, `make release` exits non-zero
  f no_go_changes       no .go file added, removed or changed against the base commit
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

TASK = "t160"
MODULE = "github.com/acme-fleet/tracker"
REG = "registry.check.local/fleet"
VER = "v9.9.9-check"
JDK = "/opt/homebrew/opt/openjdk/bin"

KO_SHIM = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CHECK_LOG"], "a") as f:
    f.write(json.dumps({"tool": "ko", "argv": sys.argv[1:], "cwd": os.getcwd(),
                        "KO_DOCKER_REPO": os.environ.get("KO_DOCKER_REPO"), "env_VERSION": os.environ.get("VERSION")}) + "\n")
if os.environ.get("KO_FAIL") == "1":
    print("ko: simulated failure", file=sys.stderr)
    sys.exit(1)
if sys.argv[1:2] and sys.argv[1] in ("build", "publish", "b"):
    print((os.environ.get("KO_DOCKER_REPO") or "missing-repo") + "/tracker-ingest@sha256:" + "0" * 64)
'''
DOCKER_SHIM = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CHECK_LOG"], "a") as f:
    f.write(json.dumps({"tool": "docker", "argv": sys.argv[1:], "cwd": os.getcwd()}) + "\n")
'''
GO_WRAPPER = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ["CHECK_LOG"], "a") as f:
    f.write(json.dumps({"tool": "go", "argv": a, "cwd": os.getcwd()}) + "\n")
if len(a) >= 2 and a[0] == "run" and a[1].split("@")[0] in ("github.com/google/ko", "github.com/ko-build/ko"):
    os.execv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ko"), ["ko"] + a[2:])
os.execv(os.environ["REAL_GO"], ["go"] + a)
'''


def sh(cmd, cwd, env, timeout=900):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True, check=True).stdout


def base_env(shim, log):
    env = {k: v for k, v in os.environ.items() if not k.startswith("KO_") and k not in ("VERSION", "REGISTRY")}
    env.update({"PATH": f"{shim}:{JDK}:{os.environ.get('PATH', '')}", "CHECK_LOG": log, "GOPROXY": "off",
                "GOTOOLCHAIN": "local", "GOFLAGS": "", "REAL_GO": shutil.which("go") or "go"})
    return env


def read_log(log):
    if not os.path.exists(log):
        return []
    return [json.loads(l) for l in open(log) if l.strip()]


def is_ingest_target(arg, cwd, wt):
    a = arg.removeprefix("ko://")
    if a in (f"{MODULE}/cmd/tracker-ingest", f"{MODULE}/cmd/tracker-ingest/"):
        return True
    if a.startswith(".") or a.startswith("/"):
        return os.path.realpath(os.path.join(cwd, a)) == os.path.realpath(os.path.join(wt, "cmd", "tracker-ingest"))
    return False


def ko_calls_ok(calls, wt):
    good, notes = [], []
    for c in calls:
        if c["tool"] != "ko":
            continue
        argv = c["argv"]
        if not argv or argv[0] not in ("build", "publish", "b"):
            notes.append(f"ko {' '.join(argv)[:80]}: not build/publish")
            continue
        targets = [x for x in argv[1:] if not x.startswith("-")]
        if not any(is_ingest_target(x, c["cwd"], wt) for x in targets):
            notes.append(f"ko {' '.join(argv)[:80]}: no tracker-ingest target")
            continue
        no_push = any(x in ("--push=false", "-L", "--local", "--local=true") or x.startswith("--tarball")
                      or x.startswith("--oci-layout-path") for x in argv)
        if no_push:
            notes.append(f"ko {' '.join(argv)[:80]}: push disabled")
            continue
        if not c.get("KO_DOCKER_REPO"):
            notes.append(f"ko {' '.join(argv)[:80]}: KO_DOCKER_REPO not set")
            continue
        good.append(c)
    return good, notes


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

    status0 = git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
    tmp = tempfile.mkdtemp(prefix="s11chk-")
    shim = os.path.join(tmp, "bin")
    os.makedirs(shim)
    for name, body in (("ko", KO_SHIM), ("docker", DOCKER_SHIM), ("go", GO_WRAPPER)):
        p = os.path.join(shim, name)
        open(p, "w").write(body)
        os.chmod(p, 0o755)
    try:
        log = os.path.join(tmp, "a.jsonl")
        env = base_env(shim, log)
        outs = []
        ok_a = True
        for cmd in (["go", "build", "./..."], ["go", "vet", "./..."], ["go", "test", "./..."]):
            rc, out = sh(cmd, wt, env)
            outs.append(f"{' '.join(cmd)} rc={rc}")
            if rc != 0:
                ok_a = False
                outs.append(out.strip()[-200:])
        add("a_go_build_vet_test", ok_a, "; ".join(outs))

        log = os.path.join(tmp, "release.jsonl")
        env = base_env(shim, log)
        rc, out = sh(["make", "release", f"REGISTRY={REG}", f"VERSION={VER}"], wt, env)
        calls = read_log(log)
        open(os.path.join(a.outdir, "release_calls.json"), "w").write(json.dumps(calls, indent=1))
        good, notes = ko_calls_ok(calls, wt)
        add("b_release_runs_ko", rc == 0 and bool(good),
            f"make release rc={rc}; ko calls ok={len(good)}; " + ("; ".join(notes) if notes else "")
            + ("" if rc == 0 else " | " + out.strip()[-200:]))
        add("c_registry_follows", bool(good) and all(c["KO_DOCKER_REPO"].startswith(REG) for c in good),
            "KO_DOCKER_REPO=" + ", ".join(sorted({c["KO_DOCKER_REPO"] for c in good})) if good else "no valid ko call")
        want_build = ["build", "-f", "deploy/api.Dockerfile", "--build-arg", f"VERSION={VER}", "-t", f"{REG}/tracker-api:{VER}", "."]
        want_push = ["push", f"{REG}/tracker-api:{VER}"]
        dk = [c["argv"] for c in calls if c["tool"] == "docker"]
        gos = [c["argv"][0] for c in calls if c["tool"] == "go" and c["argv"]]
        ok_d = want_build in dk and want_push in dk and "vet" in gos and "test" in gos
        add("d_existing_steps", ok_d, f"docker build={want_build in dk} push={want_push in dk}; go vet={'vet' in gos} test={'test' in gos}")

        log = os.path.join(tmp, "fail.jsonl")
        env = base_env(shim, log)
        env["KO_FAIL"] = "1"
        rc2, out2 = sh(["make", "release", f"REGISTRY={REG}", f"VERSION={VER}"], wt, env)
        called = any(c["tool"] == "ko" for c in read_log(log))
        add("e_ko_failure_fails", called and rc2 != 0, f"ko called={called}; make release rc={rc2} with ko exiting 1")

        changed = git(wt, "diff", "--name-only", a.base).splitlines()
        untracked = git(wt, "ls-files", "--others", "--exclude-standard").splitlines()
        go_ch = sorted(p for p in set(changed) | set(untracked) if p.endswith(".go") or p in ("go.mod", "go.sum"))
        add("f_no_go_changes", not go_ch, f"changed Go files: {go_ch}" if go_ch else "no .go/go.mod changes")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for d in ("bin", "dist"):  # git-ignored build output the release may create
            p = os.path.join(wt, d)
            if os.path.isdir(p) and f"!! {d}/" not in status0:
                shutil.rmtree(p, ignore_errors=True)
    if git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored") != status0:
        print("warning: worktree status changed during check", file=sys.stderr)
    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"], "failed": [i["name"] for i in items if not i["pass"]]}))


if __name__ == "__main__":
    main()
