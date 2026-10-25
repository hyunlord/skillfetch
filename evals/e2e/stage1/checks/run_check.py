#!/usr/bin/env python3
"""Frozen outcome checks for skillfetch e2e stage 1 (one task per call).

usage:
  python3 stage1/checks/run_check.py <task_id> <worktree> <outdir> --pg postgresql://postgres:changethis@localhost:55432
          [--lock FILE] [--base SHA] [--pgbin DIR]
  python3 stage1/checks/run_check.py --capture-baseline <task_id> <upstream-worktree>

Writes <outdir>/check.json = {task_id, pass, items:[{name, pass, detail}], visual:[png], duration_s, ...}.
pass = all items with pass != null are true. Visual / diff-review items and non-applicable mutants are null.
The worktree is left as found: hidden tests are copied in and removed, mutants restored in `finally`,
and a guard snapshot (tracked + untracked non-ignored files) is restored at the end.
Diff-based items compare against --base (default: the worktree's HEAD) and ignore condition files
(.claude/, .mcp.json, .omc/, graft/, .ignore, .gitignore).
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE1 = HERE.parent
SCREENSHOT = STAGE1 / "scripts" / "screenshot.py"
HIDDEN = HERE / "hidden"
BASE_SCREENS = HERE / "baseline-screens"
STRIP_ENV = ["VIRTUAL_ENV", "UV", "UV_RUN_RECURSION_DEPTH", "CLAUDECODE"]
COND_DIRS = {".claude", ".omc", "graft"}
COND_FILES = {".mcp.json", ".ignore", ".gitignore"}
SKIP_DIRS = {"node_modules", ".next", ".venv", ".git"} | COND_DIRS
EXISTING_MIN = 58          # fastapi tests on the upstream commit
FA_PREV_HEAD = "fe56fa70289e"  # alembic head of the upstream fastapi commit
# test cases per hidden file (after parametrize expansion)
HIDDEN_CASES = {"test_s1_fa01.py": 7, "test_s1_fa02.py": 3, "test_s1_fa04.py": 13, "test_s1_fa05.py": 4,
                "test_s1_fa08.py": 3, "test_s1_fa09.py": 4}
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# screenshot runs per task: (out subdir, kind, routes, extra args); also used by --capture-baseline
SHOTS = {
    "s1-fa-03": [("screens", "fastapi-frontend", ["/", "/items"], ["--seed-items", "4"])],
    "s1-nx-01": [("screens", "nextjs", ["/users/101", "/users/102", "/users/104"], [])],
    "s1-nx-02": [("screens", "nextjs", ["/api/users/101", "/api/users/999", "/api/users/abc", "/api/users"], [])],
    "s1-nx-03": [("screens", "nextjs", ["/does-not-exist", "/users/999"], [])],
    "s1-nx-04": [("screens", "nextjs", ["/about"], []),
                 ("screens-375", "nextjs", ["/about"], ["--viewport", "375x800"])],
    "s1-nx-05": [("screens", "nextjs", ["/", "/about", "/users"], [])],
    "s1-nx-06": [("screens", "nextjs", ["/", "/users", "/users/101", "/users/104", "/api/users"], [])],
    "s1-nx-09": [("screens", "nextjs", ["/", "/about", "/users", "/users/101", "/does-not-exist"], [])],
}
BASELINE_TASKS = ["s1-fa-03", "s1-nx-02", "s1-nx-05", "s1-nx-06", "s1-nx-09"]


def base_env(extra=None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.update({"CI": "1", "NEXT_TELEMETRY_DISABLED": "1", "PYTHONDONTWRITEBYTECODE": "1", "BROWSER": "none"})
    env.update(extra or {})
    return env


def tail(s: str, n=12) -> str:
    return "\n".join(s.strip().splitlines()[-n:])


def git(wt: Path, *args, check=True) -> str:
    return subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True, check=check).stdout


def is_cond(rel: str) -> bool:
    return rel.split("/", 1)[0] in COND_DIRS or rel in COND_FILES


# ---------------------------------------------------------------- worktree guard

def snapshot(wt: Path) -> dict:
    files = {}
    tracked = [r for r in git(wt, "ls-files", "-z").split("\0") if r]
    untracked = [r for r in git(wt, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if r]
    for rel in tracked + untracked:
        p = wt / rel
        files[rel] = ("link", os.readlink(p)) if p.is_symlink() else ("file", p.read_bytes()) if p.is_file() else None
    return {"files": files, "untracked": set(untracked), "status": git(wt, "status", "--porcelain")}


def restore(wt: Path, snap: dict) -> list[str]:
    notes = []
    for rel, v in snap["files"].items():
        p = wt / rel
        if v is None:
            if p.is_file() or p.is_symlink():
                p.unlink()
                notes.append(f"removed {rel}")
        elif v[0] == "link":
            if not p.is_symlink() or os.readlink(p) != v[1]:
                if p.exists() or p.is_symlink():
                    p.unlink()
                os.symlink(v[1], p)
                notes.append(f"restored link {rel}")
        elif p.is_symlink() or not p.is_file() or p.read_bytes() != v[1]:
            if p.is_symlink():
                p.unlink()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(v[1])
            notes.append(f"restored {rel}")
    now = set(r for r in git(wt, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if r)
    for rel in sorted(now - set(snap["files"])):
        p = wt / rel
        if p.is_file() or p.is_symlink():
            p.unlink()
            notes.append(f"removed new file {rel}")
    return notes


# ---------------------------------------------------------------- context

class Check:
    def __init__(self, task, wt: Path, out: Path, pg: str | None, lock: str | None, base: str | None, pgbin: str):
        self.task, self.wt, self.out, self.pg, self.lock, self.pgbin = task, wt, out, (pg or "").rstrip("/"), lock, pgbin
        self.base = base or git(wt, "rev-parse", "HEAD").strip()
        self.items, self.visual, self.n = [], [], 0
        self.logs = out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.env = base_env()
        self._synced = False

    def add(self, name, ok, detail=""):
        self.items.append({"name": name, "pass": ok, "detail": detail})
        return ok

    def sh(self, label, cmd, cwd, env=None, timeout=900) -> tuple[int, str]:
        self.n += 1
        log = self.logs / f"{self.n:02d}-{re.sub(r'[^A-Za-z0-9._-]+', '_', label)[:60]}.log"
        t0 = time.time()
        p = subprocess.Popen(cmd, cwd=cwd, env=env or self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            raw, _ = p.communicate(timeout=timeout)
            rc = p.returncode
        except BaseException as exc:
            # TERM first so screenshot.py can stop its servers, then KILL the group
            with contextlib.suppress(ProcessLookupError):
                os.killpg(p.pid, signal.SIGTERM)
            try:
                raw, _ = p.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(p.pid, signal.SIGKILL)
                raw, _ = p.communicate()
            rc = 124
            raw += b"\n[killed: timeout or interrupt]"
            if not isinstance(exc, subprocess.TimeoutExpired):
                raise
        finally:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(p.pid, signal.SIGKILL)  # leftovers of the group
        out = raw.decode("utf-8", "replace")
        log.write_text(f"$ {' '.join(map(str, cmd))}\n(cwd={cwd})\n{out}\n[rc={rc} {time.time() - t0:.1f}s]\n")
        return rc, out

    # ------------------------------------------------ generic pieces
    @contextlib.contextmanager
    def mutated(self, rel, old, new):
        """Apply one exact string replacement; yields False (not applicable) if the text is not there."""
        p = self.wt / rel
        orig = p.read_bytes() if p.is_file() else None
        if orig is None or old not in orig.decode("utf-8", "replace"):
            yield False
            return
        try:
            p.write_bytes(orig.decode("utf-8").replace(old, new, 1).encode("utf-8"))
            yield True
        finally:
            p.write_bytes(orig)

    @contextlib.contextmanager
    def locked(self):
        if not self.lock:
            yield
            return
        with open(self.lock, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def screenshot(self, sub, kind, routes, extra, out_root=None) -> tuple[int, dict | None]:
        out = (out_root or self.out) / sub
        cmd = ["uv", "run", "-q", str(SCREENSHOT), "--worktree", str(self.wt), "--kind", kind, "--out", str(out),
               *extra, "--routes", *routes]
        with self.locked():
            rc, _ = self.sh(f"screenshot {sub}", cmd, STAGE1, timeout=1800)
        mf = out / "screens.json"
        return rc, (json.loads(mf.read_text()) if mf.exists() else None)

    def shots(self) -> dict:
        """Run SHOTS[task]; returns {sub: manifest-or-None}; adds a 'screenshot <sub>' item per run."""
        res = {}
        for sub, kind, routes, extra in SHOTS[self.task]:
            rc, m = self.screenshot(sub, kind, routes, extra)
            err = (m or {}).get("start_error")
            self.add(f"screenshot.py {sub} ({' '.join(routes)})", rc == 0, f"rc={rc}" + (f", start_error={err}" if err else ""))
            res[sub] = m
        return res

    def visual_items(self, sub, pairs):
        for route, expect in pairs:
            png = self.out / sub / f"{slug(route)}.png"
            if png.exists():
                self.visual.append(str(png))
            self.add(f"visual {sub}{route}", None, f"{expect} ({png.name if png.exists() else 'no PNG'})")

    # ------------------------------------------------ fastapi
    def psql(self, sql, db="postgres") -> tuple[int, str]:
        return self.sh("psql", [f"{self.pgbin}/psql", f"{self.pg}/{db}", "-v", "ON_ERROR_STOP=1", "-Atc", sql],
                       self.out, timeout=120)

    @contextlib.contextmanager
    def chk_db(self):
        name = f"chk_{secrets.token_hex(5)}"
        rc, out = self.psql(f'CREATE DATABASE "{name}"')
        if rc != 0:
            raise RuntimeError(f"create database failed: {tail(out, 3)}")
        try:
            yield name, f"{self.pg}/{name}"
        finally:
            self.psql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')

    def fa_env(self, url):
        return base_env({"FASTAPI_ENV": "development", "DATABASE_URL": url})

    def uv_sync(self):
        if self._synced:
            return
        rc, _ = self.sh("uv sync --locked", ["uv", "sync", "--locked", "-q"], self.wt, timeout=900)
        if rc != 0:
            rc, out = self.sh("uv sync", ["uv", "sync", "-q"], self.wt, timeout=900)
            if rc != 0:
                self.add("uv sync", False, tail(out, 5))
        self._synced = True

    def alembic(self, url, *args) -> tuple[int, str]:
        return self.sh(f"alembic {' '.join(args)}", ["uv", "run", "alembic", *args], self.wt / "backend",
                       self.fa_env(url), timeout=300)

    @contextlib.contextmanager
    def hidden_tests(self, names):
        dest = self.wt / "backend" / "tests" / "hidden_s1"
        if not names:
            yield
            return
        if dest.exists():
            raise RuntimeError(f"{dest} already exists in the worktree")
        try:
            dest.mkdir()
            (dest / "__init__.py").write_text("")
            for n in ["s1util.py", *names]:
                shutil.copy(HIDDEN / n, dest / n)
            yield
        finally:
            shutil.rmtree(dest, ignore_errors=True)

    def fa_pytest(self, label, hidden=()) -> dict:
        """Fresh chk_ DB -> alembic upgrade head -> pytest tests/ (+ hidden). Returns parsed junit counts."""
        self.uv_sync()
        res = {"rc": None, "error": None, "existing": {"passed": 0, "failed": 0, "skipped": 0},
               "hidden": {"passed": 0, "failed": 0, "skipped": 0}, "failed_names": [], "hidden_cases": {}}
        with self.chk_db() as (_, url):
            rc, out = self.alembic(url, "upgrade", "head")
            if rc != 0:
                res.update(rc=rc, error=f"alembic upgrade head failed: {tail(out, 4)}")
                return res
            junit = self.out / f"junit-{label}.xml"
            junit.unlink(missing_ok=True)
            with self.hidden_tests(list(hidden)):
                rc, out = self.sh(f"pytest {label}", ["uv", "run", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
                                                      f"--junitxml={junit}"], self.wt / "backend", self.fa_env(url),
                                  timeout=1800)
        res["rc"] = rc
        if not junit.exists():
            res["error"] = f"no junit report: {tail(out, 6)}"
            return res
        cases = {}
        for tc in ET.parse(junit).getroot().iter("testcase"):
            key = (tc.get("classname") or "", tc.get("name") or "")
            tags = {c.tag for c in tc}
            outcome = "failed" if tags & {"failure", "error"} else "skipped" if "skipped" in tags else "passed"
            if cases.get(key) != "failed":
                cases[key] = outcome
        for (cls, name), outcome in cases.items():
            hid = "hidden_s1" in cls or "hidden_s1" in name
            res["hidden" if hid else "existing"][outcome] += 1
            if hid:
                res["hidden_cases"][name] = outcome
            if outcome == "failed":
                res["failed_names"].append(f"{cls}::{name}")
        if rc not in (0, 1) and not res["error"]:
            res["error"] = f"pytest rc={rc}: {tail(out, 4)}"
        return res

    def fa_items(self, res, hidden_file=None):
        """Items for one pytest run: existing (non-hidden) tests, hidden totals, one item per hidden test."""
        e, h = res["existing"], res["hidden"]
        err = f"; {res['error']}" if res["error"] else ""
        bad = [n for n in res["failed_names"] if "hidden_s1" not in n][:8]
        self.add("existing tests (non-hidden) all pass, >= 58", not res["error"] and e["failed"] == 0 and
                 e["passed"] >= EXISTING_MIN, f"passed={e['passed']} failed={e['failed']} skipped={e['skipped']} "
                 f"rc={res['rc']}{err}" + (f"; failed: {bad}" if bad else ""))
        if hidden_file:
            want_cases = HIDDEN_CASES[hidden_file]
            self.add(f"hidden tests {hidden_file} all pass", not res["error"] and h["failed"] == 0 and
                     h["skipped"] == 0 and h["passed"] == want_cases,
                     f"passed={h['passed']} failed={h['failed']} skipped={h['skipped']} expected={want_cases}")
            for name in sorted(res["hidden_cases"]):
                self.add(f"hidden::{name}", res["hidden_cases"][name] == "passed", res["hidden_cases"][name])

    def fa_hidden_task(self, hidden_file):
        self.fa_items(self.fa_pytest("hidden", [hidden_file]), hidden_file)

    def fa_mutants(self, rel, mutants):
        res = self.fa_pytest("unmutated")
        ok = self.add("suite passes unmutated", not res["error"] and res["rc"] == 0 and res["existing"]["failed"] == 0,
                      f"passed={res['existing']['passed']} failed={res['existing']['failed']} rc={res['rc']}"
                      + (f"; {res['error']}" if res["error"] else ""))
        for mid, old, new in mutants:
            self._mutant(mid, rel, old, new, ok, lambda m=mid: self._fa_mutant_run(m))

    def _fa_mutant_run(self, mid):
        r = self.fa_pytest(mid)
        return r["rc"] != 0, f"rc={r['rc']} passed={r['existing']['passed']} failed={r['existing']['failed']}" + (
            f"; {r['error']}" if r["error"] else "")

    def _mutant(self, mid, rel, old, new, suite_ok, run):
        name = f"mutant {mid} caught ({rel})"
        if not suite_ok:
            return self.add(name, None, "skipped: suite fails unmutated")
        with self.mutated(rel, old, new) as applied:
            if not applied:
                return self.add(name, None, "not_applicable: target text not found")
            caught, detail = run()
        return self.add(name, caught, ("caught: " if caught else "NOT caught: ") + detail)

    # ------------------------------------------------ nextjs
    def nx_prepare(self):
        if not (self.wt / "node_modules").is_dir():
            cmd = ["npm", "ci", "--no-audit", "--no-fund"] if (self.wt / "package-lock.json").exists() \
                else ["npm", "install", "--no-audit", "--no-fund"]
            rc, out = self.sh("npm ci", cmd, self.wt, timeout=900)
            if rc != 0:
                self.add("npm ci", False, tail(out, 5))

    def nx_build(self):
        rc, out = self.sh("type-check", ["npm", "run", "type-check"], self.wt, timeout=600)
        self.add("npm run type-check", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
        rc, out = self.sh("next build", ["npx", "--no-install", "next", "build"], self.wt, timeout=900)
        self.add("npx next build", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))

    def npm_test(self, label) -> tuple[int, str]:
        try:
            script = json.loads((self.wt / "package.json").read_text()).get("scripts", {}).get("test", "")
        except Exception:  # noqa: BLE001
            script = ""
        cmd = ["npm", "test"]
        if "vitest" in script and not re.search(r"\bvitest\s+run\b|--run\b", script):
            cmd += ["--", "--run"]
        rc, out = self.sh(f"npm test {label}", cmd, self.wt, timeout=900)
        return rc, f"rc={rc} script={script!r}" + ("" if rc == 0 else "\n" + tail(out, 8))

    def nx_mutants(self, mutants):
        rc, detail = self.npm_test("unmutated")
        ok = self.add("npm test passes unmutated", rc == 0, detail)
        self.nx_build()
        for mid, rel, old, new in mutants:
            self._mutant(mid, rel, old, new, ok, lambda m=mid: (lambda r: (r[0] != 0, r[1]))(self.npm_test(m)))

    def baseline(self, sub) -> dict | None:
        f = BASE_SCREENS / self.task / sub / "screens.json"
        return json.loads(f.read_text()) if f.exists() else None


def slug(route: str) -> str:
    r = route.split("@")[0].strip("/")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", r).strip("-") or "index"


def route_rec(m, route):
    for s in (m or {}).get("screens", []):
        if s.get("route") == route:
            return s
    return {}


def parse_json(text):
    try:
        return True, json.loads(text)
    except Exception:  # noqa: BLE001
        return False, None


def norm_text(t: str) -> str:
    return UUID_RE.sub("<uuid>", t or "")


def same_as_baseline(c: Check, sub, route, cur, fields=("text", "links"), norm=lambda x: x):
    b = route_rec(c.baseline(sub), route)
    if not b:
        return c.add(f"{route} unchanged vs baseline", False, "baseline manifest missing")
    diffs = [f for f in fields if norm(json.dumps(cur.get(f), ensure_ascii=False)) != norm(json.dumps(b.get(f), ensure_ascii=False))]
    return c.add(f"{route} {'+'.join(fields)} unchanged vs baseline", not diffs and cur.get("status") == b.get("status"),
                 f"status {cur.get('status')} (baseline {b.get('status')})" + (f"; differs: {diffs}" if diffs else ""))


def grep_count(path: Path, pattern: str) -> int | None:
    if not path.is_file():
        return None
    return sum(1 for line in path.read_text(errors="replace").splitlines() if re.search(pattern, line))


def changed_paths(c: Check) -> list[str]:
    tracked = [p for p in git(c.wt, "diff", "--name-only", c.base).splitlines() if p]
    untracked = [p for p in git(c.wt, "ls-files", "--others", "--exclude-standard").splitlines() if p]
    return sorted(set(p for p in tracked + untracked if not is_cond(p)))


# ================================================================ tasks: fastapi

def fa01(c):
    c.fa_hidden_task("test_s1_fa01.py")


def fa02(c):
    c.uv_sync()
    with c.chk_db() as (_, url):
        rc, out = c.alembic(url, "upgrade", "head")
        c.add("fresh DB: alembic upgrade head", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 5)))
        rc, out = c.alembic(url, "check")
        clean = rc == 0 and "No new upgrade operations detected" in out
        c.add("alembic check clean", clean, f"rc={rc}; " + tail(out, 2))
        rc1, out1 = c.alembic(url, "downgrade", "-1")
        rc2, out2 = c.alembic(url, "upgrade", "head") if rc1 == 0 else (None, "")
        c.add("alembic downgrade -1 && upgrade head", rc1 == 0 and rc2 == 0,
              f"downgrade rc={rc1}, upgrade rc={rc2}" + ("" if rc1 == 0 and rc2 == 0 else "\n" + tail(out1 + out2, 5)))
    with c.chk_db() as (name, url):
        rc, out = c.alembic(url, "upgrade", FA_PREV_HEAD)
        ok, detail = False, f"upgrade {FA_PREV_HEAD} rc={rc}"
        if rc == 0:
            rc, out = c.psql("INSERT INTO \"user\" (id, email, is_active, is_superuser, hashed_password) VALUES "
                             "(gen_random_uuid(), 'chk-old@example.com', true, false, 'x'); "
                             "INSERT INTO item (id, title, owner_id) SELECT gen_random_uuid(), 'old row', id FROM \"user\";",
                             db=name)
            detail += f"; insert rc={rc}"
            if rc == 0:
                rc, out = c.alembic(url, "upgrade", "head")
                detail += f"; upgrade head rc={rc}"
                if rc == 0:
                    rc, out = c.psql("SELECT is_done FROM item WHERE title = 'old row'", db=name)
                    detail += f"; is_done = {out.strip()!r}"
                    ok = rc == 0 and out.strip() == "f"
        c.add(f"existing row at {FA_PREV_HEAD} -> upgrade head -> is_done = false", ok,
              detail + ("" if ok else "\n" + tail(out, 3)))
    c.fa_hidden_task("test_s1_fa02.py")


def fa03(c):
    fe = c.wt / "frontend"
    if not (c.wt / "node_modules").is_dir():
        rc, out = c.sh("bun install", ["bun", "install", "--frozen-lockfile"], c.wt, timeout=900)
        if rc != 0:
            c.sh("bun install (unfrozen)", ["bun", "install"], c.wt, timeout=900)
    rc, out = c.sh("tsc", ["bunx", "tsc", "-p", "tsconfig.build.json"], fe, timeout=600)
    c.add("bunx tsc -p tsconfig.build.json", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
    rc, out = c.sh("biome ci", ["bunx", "biome", "ci", "./"], fe, timeout=600)
    c.add("bunx biome ci ./", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
    m = c.shots()["screens"]
    r = route_rec(m, "/")
    t = r.get("text", "")
    c.add("'/' status 200, no page_errors", r.get("status") == 200 and not r.get("page_errors"),
          f"status={r.get('status')} page_errors={r.get('page_errors')}")
    for s in ("Seed item 4", "Seed item 3", "Seed item 2"):
        c.add(f"'/' text contains {s!r}", s in t)
    c.add("'/' text does not contain 'Seed item 1'", bool(r) and "Seed item 1" not in t)
    stripped = UUID_RE.sub(" ", re.sub(r"Seed item \d+|Seeded by screenshot\.py \(\d+\)", " ", t))
    c.add("'/' text has a standalone '4'", bool(re.search(r"(?<![0-9A-Za-z])4(?![0-9A-Za-z])", stripped)),
          "after removing 'Seed item N', seeded descriptions and UUIDs; 4 not adjacent to [0-9A-Za-z]")
    same_as_baseline(c, "screens", "/items", route_rec(m, "/items"), norm=norm_text)
    c.visual_items("screens", [("/", "card with item count 4 and titles Seed item 4/3/2, styled like the app")])


def fa04(c):
    f = c.wt / "backend/app/api/routes/items.py"
    for s in ("Not enough permissions", "Item not found"):
        n = grep_count(f, re.escape(s))
        c.add(f"grep -c {s!r} items.py <= 1", n is not None and n <= 1, f"count={n}")
    c.fa_hidden_task("test_s1_fa04.py")


def fa05(c):
    for rel in ("backend/app/api/routes/items.py", "backend/app/api/routes/users.py"):
        n = grep_count(c.wt / rel, r"skip: int = 0|limit: int = 100")
        c.add(f"grep -cE 'skip: int = 0|limit: int = 100' {rel} == 0", n == 0, f"count={n}")
    c.fa_hidden_task("test_s1_fa05.py")


def fa06(c):
    w = "            .where(Item.owner_id == current_user.id)\n"
    c.fa_mutants("backend/app/api/routes/items.py", [
        ("M1", "            select(Item)\n" + w, "            select(Item)\n"),
        ("M2", "            .select_from(Item)\n" + w, "            .select_from(Item)\n"),
    ])


def fa07(c):
    c.fa_mutants("backend/app/api/deps.py", [
        ("M1", '    if not user.is_active:\n        raise HTTPException(status_code=400, detail="Inactive user")\n', ""),
        ("M2", '    if not user:\n        raise HTTPException(status_code=404, detail="User not found")\n', ""),
        ("M3", "token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]",
         'token, settings.SECRET_KEY, algorithms=[security.ALGORITHM], options={"verify_exp": False}'),
    ])


def fa08(c):
    c.fa_hidden_task("test_s1_fa08.py")


def fa09(c):
    c.fa_hidden_task("test_s1_fa09.py")


def fa10(c):
    cfg = git(c.wt, "show", f"{c.base}:backend/app/core/config.py")
    names = re.findall(r"^    ([A-Z][A-Z0-9_]+):", cfg, re.M)
    readme = c.wt / "backend/README.md"
    rows = [ln for ln in (readme.read_text(errors="replace").splitlines() if readme.exists() else []) if ln.startswith("|")]
    word = lambda n: re.compile(rf"(?<![A-Za-z0-9_]){n}(?![A-Za-z0-9_])")  # noqa: E731
    missing = [n for n in names if not any(word(n).search(r) for r in rows)]
    c.add(f"all {len(names)} Settings names occur in a '|' line of backend/README.md", len(names) == 20 and not missing,
          f"names={len(names)} (from {c.base[:12]}:config.py); missing={missing}")
    bad = []
    for n in ("SECRET_KEY", "PROJECT_NAME", "DATABASE_URL", "FIRST_SUPERUSER", "FIRST_SUPERUSER_PASSWORD"):
        mine = [r for r in rows if len(r.split("|")) > 2 and word(n).search(r.split("|")[1])] or \
               [r for r in rows if word(n).search(r)]
        if not any("required" in r.lower() for r in mine):
            bad.append(n)
    c.add("rows of the 5 required settings contain 'required'", not bad, f"without 'required': {bad}")
    ch = changed_paths(c)
    c.add("changed files vs base == [backend/README.md]", ch == ["backend/README.md"], f"changed={ch[:20]}")


# ================================================================ tasks: nextjs

def links(r):
    return r.get("links") or []


def nx01(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    r101, r102, r104 = (route_rec(m, x) for x in ("/users/101", "/users/102", "/users/104"))
    want = [("/users/101", "Previous"), ("/users/103", "Next"), ("/users", "Back to list")]
    miss = [w for w in want if not any(lk.get("href") == w[0] and w[1] in (lk.get("text") or "") for lk in links(r102))]
    c.add("/users/102 links: Previous->/users/101, Next->/users/103, Back to list->/users", bool(r102) and not miss,
          f"missing={miss}")
    c.add("/users/101 has no link text 'Previous'", bool(r101) and not any("Previous" in (lk.get("text") or "") for lk in links(r101)))
    c.add("/users/104 has no link text 'Next'", bool(r104) and not any("Next" in (lk.get("text") or "") for lk in links(r104)))
    pe = {x: route_rec(m, x).get("page_errors") for x in ("/users/101", "/users/102", "/users/104")}
    c.add("no page_errors", all(v == [] for v in pe.values()), str(pe))
    c.visual_items("screens", [("/users/101", "Alice detail; Next -> Bob; Back to list; no Previous"),
                               ("/users/102", "Bob detail; Previous -> Alice, Next -> Caroline; Back to list"),
                               ("/users/104", "Dave detail; Previous -> Caroline; no Next")])


def nx02(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    r = route_rec(m, "/api/users/101")
    ok, v = parse_json(r.get("text", ""))
    c.add('/api/users/101: 200 and JSON == {"id":101,"name":"Alice"}', r.get("status") == 200 and ok and v == {"id": 101, "name": "Alice"},
          f"status={r.get('status')} text={r.get('text', '')[:120]!r}")
    for route, code in (("/api/users/999", 404), ("/api/users/abc", 400)):
        r = route_rec(m, route)
        ok, _ = parse_json(r.get("text", ""))
        c.add(f"{route}: {code} and JSON body", r.get("status") == code and ok,
              f"status={r.get('status')} text={r.get('text', '')[:120]!r}")
    r = route_rec(m, "/api/users")
    b = route_rec(c.baseline("screens"), "/api/users")
    ok, v = parse_json(r.get("text", ""))
    okb, vb = parse_json(b.get("text", ""))
    c.add("/api/users unchanged (200, same JSON as baseline)", r.get("status") == 200 and ok and okb and v == vb and len(v) == 4,
          f"status={r.get('status')} text={r.get('text', '')[:120]!r}")


def nx03(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    for route in ("/does-not-exist", "/users/999"):
        r = route_rec(m, route)
        t = r.get("text", "")
        miss = [s for s in ("페이지를 찾을 수 없습니다", "Users List", "Footer") if s not in t]
        c.add(f"{route}: status 404", r.get("status") == 404, f"status={r.get('status')}")
        c.add(f"{route}: text has 페이지를 찾을 수 없습니다 / Users List / Footer", bool(r) and not miss, f"missing={miss}")
        c.add(f"{route}: a link with href '/'", any(lk.get("href") == "/" for lk in links(r)))
        c.add(f"{route}: not 'This page could not be found'", bool(r) and "This page could not be found" not in t)
    c.visual_items("screens", [("/does-not-exist", "site nav, 페이지를 찾을 수 없습니다, link home, footer"),
                               ("/users/999", "same custom 404")])


def nx04(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    r = route_rec(m, "/about")
    t = r.get("text", "")
    miss = [s for s in ("Alice", "Bob", "Caroline", "Dave", "101", "102", "103", "104") if s not in t]
    c.add("/about text contains Alice, Bob, Caroline, Dave, 101..104", bool(r) and not miss, f"missing={miss}")
    hrefs = {lk.get("href") for lk in links(r)}
    miss = [h for h in ("/users/101", "/users/102", "/users/103", "/users/104") if h not in hrefs]
    c.add("/about links include /users/101../users/104", bool(r) and not miss, f"missing={miss}")
    c.visual_items("screens", [("/about", "4 cards in a grid at 1280px, each with ID and link")])
    c.visual_items("screens-375", [("/about", "375x800: one card per row")])


def nx05(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    bm = c.baseline("screens")
    for route in ("/", "/about", "/users"):
        r, b = route_rec(m, route), route_rec(bm, route)
        cur = [lk.get("href") for lk in links(r) if lk.get("aria_current") == "page"]
        c.add(f"{route}: exactly one aria-current=page link, href {route}", cur == [route], f"aria-current hrefs={cur}")
        line, bline = (r.get("text") or "").split("\n")[0], (b.get("text") or "").split("\n")[0]
        c.add(f"{route}: nav text line identical to baseline", bool(r) and bool(b) and line == bline, f"{line!r} vs {bline!r}")
        nav = [(lk.get("href"), lk.get("text")) for lk in links(r)[:4]]
        bnav = [(lk.get("href"), lk.get("text")) for lk in links(b)[:4]]
        c.add(f"{route}: nav links in baseline order", bool(b) and nav == bnav, f"{nav}")
    c.add("diff review: nav links defined in one array", None, "judged by reading the diff")
    c.visual_items("screens", [("/", "nav as before; Home current"), ("/about", "About current"),
                               ("/users", "Users List current")])


def nx06(c):
    found = []
    for root, dirs, files in os.walk(c.wt):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith((".ts", ".tsx")):
                p = Path(root) / f
                if "sampleUserData" in p.read_text(errors="replace"):
                    found.append(p.relative_to(c.wt).as_posix())
    found.sort()
    c.add("grep -rl sampleUserData (*.ts, *.tsx) only utils/sample-data.ts and lib/users.ts",
          set(found) <= {"utils/sample-data.ts", "lib/users.ts"}, f"files={found}")
    lib = c.wt / "lib/users.ts"
    src = lib.read_text(errors="replace") if lib.exists() else ""
    miss = [n for n in ("getAllUsers", "getUserById")
            if not re.search(rf"^.*\bexport\b.*\b{n}\b", src, re.M) and not re.search(rf"export\s*\{{[^}}]*\b{n}\b", src)]
    c.add("lib/users.ts exports getAllUsers and getUserById", lib.exists() and not miss, f"missing={miss}" if lib.exists() else "lib/users.ts missing")
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    for route in SHOTS["s1-nx-06"][0][2]:
        same_as_baseline(c, "screens", route, route_rec(m, route))


def nx07(c):
    c.nx_prepare()
    c.nx_mutants([
        ("M1", "components/ListDetail.tsx", "Detail for {user.name}", "Detail for {user.id}"),
        ("M2", "components/Layout.tsx", '<Link href="/users">Users List</Link>', ""),
    ])


def nx08(c):
    c.nx_prepare()
    c.nx_mutants([
        ("M1", "pages/users/[id].tsx", "const paths = sampleUserData.map(", "const paths = sampleUserData.slice(0, 3).map("),
        ("M2", "pages/users/[id].tsx", "data.id === Number(id)", "data.id === Number(id) + 1"),
    ])


def nx09(c):
    c.nx_prepare()
    c.nx_build()
    m = c.shots()["screens"]
    routes = SHOTS["s1-nx-09"][0][2]
    for route in routes:
        r = route_rec(m, route)
        c.add(f"{route}: html_lang == 'en'", r.get("html_lang") == "en", f"html_lang={r.get('html_lang')!r}")
    for route in routes[:4]:
        same_as_baseline(c, "screens", route, route_rec(m, route), fields=("text",))


def nx10(c):
    c.nx_prepare()
    rc, out = c.sh("nx10_jsdoc", ["node", str(HIDDEN / "nx10_jsdoc.cjs"), str(c.wt)], c.out, timeout=120)
    try:
        res = json.loads(out)
        c.add("JSDoc on every component, Props member (or @param) and exported type", res["ok"],
              "; ".join(res["problems"])[:1500] or "all documented")
    except Exception:  # noqa: BLE001
        c.add("JSDoc on every component, Props member (or @param) and exported type", False, f"rc={rc} {tail(out, 5)}")
    diff = git(c.wt, "diff", "-U0", c.base, "--", "components", "interfaces")
    lines = [ln for ln in diff.splitlines() if re.match(r"^[+-][^+-]", ln)]
    for rel in git(c.wt, "ls-files", "--others", "--exclude-standard", "--", "components", "interfaces").splitlines():
        lines += ["+" + ln for ln in (c.wt / rel).read_text(errors="replace").splitlines()
                  if re.match(r"^[+-][^+-]", "+" + ln)]
    code = [ln for ln in lines if not re.match(r"^[+-]\s*(/\*\*|\*|\*/|//)", ln)]
    c.add("comment-only change in components/ interfaces/ (non-comment +/- lines == 0)", not code,
          f"count={len(code)}" + (f": {code[:6]}" if code else ""))
    c.nx_build()


TASKS = {"s1-fa-01": fa01, "s1-fa-02": fa02, "s1-fa-03": fa03, "s1-fa-04": fa04, "s1-fa-05": fa05,
         "s1-fa-06": fa06, "s1-fa-07": fa07, "s1-fa-08": fa08, "s1-fa-09": fa09, "s1-fa-10": fa10,
         "s1-nx-01": nx01, "s1-nx-02": nx02, "s1-nx-03": nx03, "s1-nx-04": nx04, "s1-nx-05": nx05,
         "s1-nx-06": nx06, "s1-nx-07": nx07, "s1-nx-08": nx08, "s1-nx-09": nx09, "s1-nx-10": nx10}


def on_signal(signum, _frame):
    raise SystemExit(128 + signum)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture-baseline", action="store_true", help="store SHOTS[task] manifests under baseline-screens/")
    ap.add_argument("task_id", choices=sorted(TASKS))
    ap.add_argument("worktree", type=Path)
    ap.add_argument("outdir", type=Path, nargs="?")
    ap.add_argument("--pg", help="postgres server URL without db, e.g. postgresql://postgres:changethis@localhost:55432")
    ap.add_argument("--lock", help="flock file serialising screenshot.py runs")
    ap.add_argument("--base", help="commit to diff against (default: worktree HEAD)")
    ap.add_argument("--pgbin", default=os.environ.get("PGBIN", "/opt/homebrew/opt/postgresql@16/bin"))
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, on_signal)
    wt = a.worktree.resolve()

    if a.capture_baseline:
        dest = BASE_SCREENS / a.task_id
        shutil.rmtree(dest, ignore_errors=True)
        c = Check(a.task_id, wt, dest, None, a.lock, a.base, a.pgbin)
        snap = snapshot(wt)
        try:
            for sub, kind, routes, extra in SHOTS[a.task_id]:
                rc, _ = c.screenshot(sub, kind, routes, extra)
                print(f"{sub}: rc={rc}")
        finally:
            restore(wt, snap)
            shutil.rmtree(dest / "logs", ignore_errors=True)
            for sub, *_ in SHOTS[a.task_id]:
                shutil.rmtree(dest / sub / "logs", ignore_errors=True)
        return 0

    if a.outdir is None:
        ap.error("outdir is required")
    if a.task_id.startswith("s1-fa") and a.task_id not in ("s1-fa-03", "s1-fa-10") and not a.pg:
        ap.error("--pg is required for fastapi checks")
    out = a.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    c = Check(a.task_id, wt, out, a.pg, a.lock, a.base, a.pgbin)
    snap = snapshot(wt)
    error = None
    try:
        TASKS[a.task_id](c)
    except BaseException as e:  # noqa: BLE001 - always write check.json
        error = f"{type(e).__name__}: {e}"
        c.add("check ran to completion", False, error)
    finally:
        restored = restore(wt, snap)
        status_after = git(wt, "status", "--porcelain")
        res = {"task_id": a.task_id,
               "pass": error is None and all(i["pass"] is not False for i in c.items) and any(i["pass"] for i in c.items),
               "items": c.items, "visual": c.visual, "duration_s": round(time.time() - t0, 1),
               "worktree": str(wt), "base": c.base, "worktree_restored": restored,
               "git_status_unchanged": status_after == snap["status"]}
        (out / "check.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"task_id": a.task_id, "pass": res["pass"], "duration_s": res["duration_s"],
                      "failed": [i["name"] for i in c.items if i["pass"] is False]}, ensure_ascii=False))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
