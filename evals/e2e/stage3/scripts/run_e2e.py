#!/usr/bin/env python3
"""Step 5: 40 real Claude Code sessions (same harness as stages 1-2: stage1 run_session, claude -p stream-json,
allowed tools Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*), each in an empty git repo that contains only the
router skill (skillfetch main 64f4bd8) and a project .mcp.json pinned to 64f4bd8. --max-turns 12: enough for the router
chain; the work itself is not scored.
  run_e2e.py sample      -> e2e-sample.json (stratified by offline failure class, seeded)
  run_e2e.py <task_id>   -> runs/<task_id>.{jsonl,ts,debug.log,stderr,meta.json}   (run 1: empty repo)
  run_e2e.py --stub <id> -> runs-stub/...   (run 2: the files the task names exist as stubs; no manifests or lockfiles,
                                             so profile_repo stays empty as in the offline evaluation)"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
S3 = E2E / "stage3"
sys.path.insert(0, str(E2E / "scripts"))
sys.path.insert(0, str(E2E / "stage1" / "scripts"))
WT = Path.home() / "skillfetch-e2e-wt" / "s3"
PIN = "64f4bd8"
import re  # noqa: E402

PATH = re.compile(r"(?<![\w@:/])((?:[\w.\[\]()-]+/)*[\w.\[\]()-]+\.(?:py|pyi|ts|tsx|js|jsx|mjs|go|rs|java|kt|kts|swift|dart|ya?ml|json|md|sql|tf|sh|"
                  r"html|templ|xml|plist|cfg|ini|proto|toml|css|scss|vue|svelte|rb|php|cs|gradle|properties|env|txt|csv|ipynb))\b")
DIRS = re.compile(r"(?<![\w@:/.])((?:[\w-]+/)+)(?=[\s`'\",.)]|$)")
MANIFESTS = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "pyproject.toml", "uv.lock", "poetry.lock",
             "requirements.txt", "setup.py", "setup.cfg", "go.mod", "go.sum", "cargo.toml", "cargo.lock", "pom.xml", "build.gradle",
             "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "pubspec.yaml", "pubspec.lock", "podfile", "gemfile",
             "composer.json", "next.config.js", "next.config.mjs", "next.config.ts", "tsconfig.json", "deno.json", "bun.lockb"}
STUB = {".py": "", ".go": "package main\n", ".ts": "export {}\n", ".tsx": "export {}\n", ".js": "", ".rs": "", ".java": "", ".kt": "",
        ".swift": "", ".dart": "", ".md": ""}


SEED = {"python": "app/main.py", "ts_react_next": "src/index.ts", "go": "main.go", "rust": "src/main.rs",
        "java_kotlin": "src/main/kotlin/App.kt", "mobile": "lib/main.dart"}  # one source file per stack, not a manifest


def stubs(text):
    files = {m.group(1).lstrip("./") for m in PATH.finditer(text)}
    files = {f for f in files if Path(f).name.lower() not in MANIFESTS and ".." not in f}
    dirs = {m.group(1) for m in DIRS.finditer(text) if not m.group(1).startswith(("http", "www"))}
    return sorted(files), sorted(dirs)


def sample():
    ev = [json.loads(l) for l in (S3 / "selection-eval.jsonl").open()]
    rng = random.Random("e2e-40")
    want = {"over_load": 10, "select_fail": 10, "restate_fail": 10, "search_fail": 10}
    picked = []
    for cls, n in want.items():
        pool = [r["id"] for r in ev if r["class"] == cls]
        picked += rng.sample(pool, min(n, len(pool)))
    ok = [r["id"] for r in ev if r["class"] == "ok"]
    picked += rng.sample(ok, 40 - len(picked))
    (S3 / "e2e-sample.json").write_text(json.dumps(sorted(picked)))
    print(len(picked), {c: sum(1 for r in ev if r["id"] in picked and r["class"] == c) for c in list(want) + ["ok"]})


def run(tid, stub=False):
    import run_stage1 as rs
    task = next(json.loads(l) for l in (S3 / "tasks.jsonl").open() if json.loads(l)["id"] == tid)
    wt = (WT.parent / "s3-stub" if stub else WT) / tid
    made = []
    if wt.exists():
        subprocess.run(["rm", "-rf", str(wt)], check=True)
    (wt / ".claude" / "skills" / "skillfetch-router").mkdir(parents=True)
    router = subprocess.run(["git", "-C", str(E2E.parent / "router-fix"), "show", f"{PIN}:assets/router-skill/SKILL.md"],
                            capture_output=True, text=True, check=True).stdout
    (wt / ".claude" / "skills" / "skillfetch-router" / "SKILL.md").write_text(router)
    (wt / ".mcp.json").write_text(json.dumps({"mcpServers": {"skillfetch": {"type": "stdio", "command": "uvx", "args": [
        "--from", f"git+https://github.com/hyunlord/skillfetch@{PIN}", "skillfetch", "serve"], "env": {}}}}, indent=2) + "\n")
    if stub:
        files, dirs = stubs(task["text"])
        files = sorted(set(files) | {SEED[task["stack"]]})
        for d in dirs:
            (wt / d).mkdir(parents=True, exist_ok=True)
            made.append(d)
        for f in files:
            (wt / f).parent.mkdir(parents=True, exist_ok=True)
            (wt / f).write_text(STUB.get(Path(f).suffix, ""))
            made.append(f)
        for d in dirs:  # git does not keep empty directories
            if not any((wt / d).iterdir()):
                (wt / d / ".gitkeep").write_text("")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.name=e2e", "-c", "user.email=e2e@local", "commit", "-q", "-m", "router + mcp"]):
        subprocess.run(cmd, cwd=wt, check=True)
    out = S3 / ("runs-stub" if stub else "runs") / tid
    out.parent.mkdir(exist_ok=True)
    meta = {"task": task, "worktree": str(wt), "pin": PIN, "max_turns": 12, "stub_paths": made, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    meta["session"] = rs.run_session({"id": tid, "prompt": task["text"]}, "C", wt, {}, out, max_turns="12")
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(tid, "done", meta["session"]["exit_code"], meta["session"]["wall_s"])


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample()
    elif sys.argv[1] == "--stub":
        run(sys.argv[2], stub=True)
    else:
        run(sys.argv[1])
