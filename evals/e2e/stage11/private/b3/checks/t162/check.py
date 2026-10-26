#!/usr/bin/env python3
"""Hidden objective check for Stage 11 s11-t162.

Task: "goreleaser로 `inventory-cli` 바이너리 릴리스할 때 macOS arm64랑 linux amd64만 빌드하고 Homebrew tap에도 자동으로
올라가게 `.goreleaser.yaml` 수정해줘. 지금은 windows까지 빌드돼서 릴리스가 10분 넘게 걸려."

Usage: python3 check.py <worktree> <outdir> [--reply <file>] [--base <commit>]

The worktree (with its .git) is copied to a temp dir and `goreleaser release --snapshot --clean` runs there
(GOPROXY=off; snapshot mode never publishes). Results are read from dist/artifacts.json and dist/config.yaml (the
effective config).

Items:
  a go_build_vet_test   `go build ./...`, `go vet ./...`, `go test ./...` pass
  b goreleaser_check    `goreleaser check` exits 0, or 2 (valid but uses deprecated properties, e.g. `brews`)
  c targets             the snapshot release succeeds and its inventory-cli binaries are exactly darwin/arm64 and
                        linux/amd64
  d homebrew_generated  a Homebrew formula or cask for inventory-cli is generated, its tap repository owner and name are
                        set, and it mentions no windows artifact
  e tap_auto_upload     the Homebrew entry does not set skip_upload: true (so a release pushes to the tap)
  f no_go_changes       no .go file (or go.mod/go.sum) added, removed or changed against the base commit
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

TASK = "t162"
JDK = "/opt/homebrew/opt/openjdk/bin"
BREW_TYPES = ("Brew Tap", "Homebrew Formula", "Homebrew Cask")


def sh(cmd, cwd, env, timeout=900):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True, check=True).stdout


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

    env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "HOMEBREW_TAP", "GORELEASER"))}
    env.update({"PATH": f"{JDK}:{os.environ.get('PATH', '')}", "GOPROXY": "off", "GOTOOLCHAIN": "local", "GOFLAGS": ""})
    status0 = git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
    tmp = tempfile.mkdtemp(prefix="s11chk-")
    try:
        outs, ok_a = [], True
        for cmd in (["go", "build", "./..."], ["go", "vet", "./..."], ["go", "test", "./..."]):
            rc, out = sh(cmd, wt, env)
            outs.append(f"{' '.join(cmd)} rc={rc}")
            if rc != 0:
                ok_a = False
                outs.append(out.strip()[-200:])
        add("a_go_build_vet_test", ok_a, "; ".join(outs))

        rc, out = sh(["goreleaser", "check"], wt, env)
        add("b_goreleaser_check", rc in (0, 2), f"rc={rc}" + ("" if rc == 0 else " | " + " ".join(l.strip() for l in out.splitlines() if "DEPRECATED" in l or "error" in l)[:300]))

        cp = os.path.join(tmp, "wt")
        shutil.copytree(wt, cp, symlinks=True, ignore=shutil.ignore_patterns("dist"))
        rc, out = sh(["goreleaser", "release", "--snapshot", "--clean"], cp, env)
        open(os.path.join(a.outdir, "snapshot.log"), "w").write(out.replace(cp, "<copy>"))
        arts = []
        af = os.path.join(cp, "dist", "artifacts.json")
        if rc == 0 and os.path.exists(af):
            arts = json.load(open(af))
        bins = sorted({(x.get("goos"), x.get("goarch")) for x in arts
                       if x.get("type") == "Binary" and (x.get("extra", {}).get("Binary") or x.get("name", "")).startswith("inventory-cli")})
        want = [("darwin", "arm64"), ("linux", "amd64")]
        add("c_targets", rc == 0 and bins == want, f"snapshot rc={rc}; binaries={bins}" + ("" if rc == 0 else " | " + out.strip()[-200:]))

        cfg = {}
        cf = os.path.join(cp, "dist", "config.yaml")
        if os.path.exists(cf):
            cfg = yaml.safe_load(open(cf)) or {}
        entries = [("brews", e) for e in (cfg.get("brews") or [])] + [("homebrew_casks", e) for e in (cfg.get("homebrew_casks") or [])]
        repos = [(k, (e.get("repository") or {}).get("owner"), (e.get("repository") or {}).get("name")) for k, e in entries]
        brew_arts = [x for x in arts if x.get("type") in BREW_TYPES]
        rb = [p for p in glob.glob(os.path.join(cp, "dist", "**", "*.rb"), recursive=True)]
        rb_text = "\n".join(open(p).read() for p in rb)
        ok_d = (bool(brew_arts) and bool(rb) and "inventory-cli" in rb_text and "windows" not in rb_text.lower()
                and bool(repos) and all(o and n for _, o, n in repos))
        add("d_homebrew_generated", ok_d, f"artifacts={[x.get('type') for x in brew_arts]}; files={[os.path.relpath(p, cp) for p in rb]}; repositories={repos}")
        skips = [(k, e.get("skip_upload")) for k, e in entries]
        ok_e = bool(entries) and all(str(s).lower() not in ("true",) for _, s in skips)
        add("e_tap_auto_upload", ok_e, f"skip_upload={skips}" if entries else "no homebrew entry")

        changed = git(wt, "diff", "--name-only", a.base).splitlines()
        untracked = git(wt, "ls-files", "--others", "--exclude-standard").splitlines()
        go_ch = sorted(p for p in set(changed) | set(untracked) if p.endswith(".go") or p in ("go.mod", "go.sum"))
        add("f_no_go_changes", not go_ch, f"changed Go files: {go_ch}" if go_ch else "no .go/go.mod changes")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if git(wt, "status", "--porcelain=v1", "--untracked-files=all", "--ignored") != status0:
        print("warning: worktree status changed during check", file=sys.stderr)
    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    with open(os.path.join(a.outdir, "check.json"), "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"task": TASK, "pass": result["pass"], "failed": [i["name"] for i in items if not i["pass"]]}))


if __name__ == "__main__":
    main()
