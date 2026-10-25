# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.50"]
# ///
"""Build + start an app from a worktree, take full-page screenshots, stop everything.

usage:
  uv run stage1/scripts/screenshot.py --worktree WT --kind nextjs --out DIR --routes / /about /users
  uv run stage1/scripts/screenshot.py --worktree WT --kind fastapi-frontend --out DIR \
      --routes /login@anon / /items /admin /settings

Kinds
  nextjs            npm ci (only if node_modules is missing) -> next build -> next start
                    (--mode dev: next dev instead of build+start)
  fastapi-frontend  throwaway Postgres (initdb in a temp dir) -> uv sync (only if .venv is missing)
                    -> alembic upgrade head -> initial_data -> uvicorn via `fastapi run`;
                    bun install (only if node_modules is missing) -> tsc + vite build into a temp
                    dir -> vite preview (--mode dev: vite dev server). Routes are visited logged in
                    as FIRST_SUPERUSER from the worktree's .env unless the route ends in "@anon".
                    --seed-items N creates N items through the API before the screenshots.

Ports are taken from 4100-4199 (first free ones). Output: <out>/<route-slug>.png, <out>/screens.json,
<out>/logs/*.log. screens.json has per route: status, final_url, title, html_lang, text (body innerText,
first 20k chars), links (href/text/aria-current of up to 200 <a>), console_errors, page_errors,
http_errors (responses >= 400), file. Tracked files the build/servers changed (tsconfig.json, routeTree.gen.ts, lockfiles,
...) are restored and new untracked non-ignored files are removed when the script ends; both are
listed in screens.json under "worktree_restored". Ignored paths (node_modules, .next, .venv) stay.
Exit code: 0 = all routes captured, 1 = some route failed, 2 = build/start failed (manifest still written).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PORT_RANGE = range(4100, 4200)
PGBIN_DEFAULT = "/opt/homebrew/opt/postgresql@16/bin"
# env of a parent Claude Code / uv session that should not leak into child processes
STRIP_ENV = ["VIRTUAL_ENV", "UV", "UV_RUN_RECURSION_DEPTH", "CLAUDECODE"]


class StartError(RuntimeError):
    pass


# ---------------------------------------------------------------- helpers

def base_env(extra: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
    env.update({"NEXT_TELEMETRY_DISABLED": "1", "CI": "1", "BROWSER": "none"})
    env.update(extra or {})
    return env


def port_free(port: int) -> bool:
    for fam, addr in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        with socket.socket(fam, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex((addr, port)) == 0:
                    return False
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def pick_ports(n: int) -> list[int]:
    got = [p for p in PORT_RANGE if port_free(p)][:n]
    if len(got) < n:
        raise StartError(f"need {n} free ports in 4100-4199, found {got}")
    return got


def slug(route: str) -> str:
    r = route.split("@")[0].strip("/")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", r).strip("-") or "index"


def run(cmd, cwd, env, log: Path, timeout=900) -> int:
    with open(log, "a") as fh:
        fh.write(f"\n$ {' '.join(map(str, cmd))}  (cwd={cwd})\n")
        fh.flush()
        p = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, timeout=timeout)
    return p.returncode


def http_status(url: str, timeout=3.0) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


class Procs:
    """Background processes, each in its own process group; stop() kills whole groups."""

    def __init__(self):
        self.items: list[tuple[str, subprocess.Popen, object]] = []
        self.cleanups: list = []

    def start(self, name, cmd, cwd, env, log: Path) -> subprocess.Popen:
        fh = open(log, "a")
        fh.write(f"\n$ {' '.join(map(str, cmd))}  (cwd={cwd})\n")
        fh.flush()
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        self.items.append((name, p, fh))
        return p

    def wait_http(self, name, p, url, timeout_s, ok=lambda s: s is not None and s < 500):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if p.poll() is not None:
                raise StartError(f"{name} exited with {p.returncode} before it was ready")
            if ok(http_status(url)):
                return round(time.time() - t0, 1)
            time.sleep(0.5)
        raise StartError(f"{name} not ready at {url} after {timeout_s}s")

    def stop(self) -> list[str]:
        notes = []
        for name, p, fh in reversed(self.items):
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.wait(timeout=5)
                    notes.append(f"{name}: SIGKILL")
            # children that outlived the group leader
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            fh.close()
        self.items.clear()
        for fn in reversed(self.cleanups):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                notes.append(f"cleanup failed: {e}")
        self.cleanups.clear()
        return notes


# ---------------------------------------------------------------- worktree guard

def git(wt: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True, check=True).stdout


def snapshot(wt: Path) -> dict:
    tracked = {}
    for rel in git(wt, "ls-files", "-z").split("\0"):
        if not rel:
            continue
        p = wt / rel
        if p.is_symlink():
            tracked[rel] = ("link", os.readlink(p))
        elif p.is_file():
            tracked[rel] = ("file", p.read_bytes())
        else:
            tracked[rel] = ("missing", None)
    untracked = set(filter(None, git(wt, "ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    return {"tracked": tracked, "untracked": untracked}


def restore(wt: Path, snap: dict) -> list[str]:
    changed = []
    for rel, (kind, data) in snap["tracked"].items():
        p = wt / rel
        if kind == "file":
            if p.is_symlink() or not p.is_file() or p.read_bytes() != data:
                if p.is_symlink():
                    p.unlink()
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                changed.append(f"restored {rel}")
        elif kind == "link":
            if not p.is_symlink() or os.readlink(p) != data:
                if p.exists() or p.is_symlink():
                    p.unlink()
                os.symlink(data, p)
                changed.append(f"restored link {rel}")
    now = set(filter(None, git(wt, "ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    for rel in sorted(now - snap["untracked"]):
        p = wt / rel
        if p.is_file() or p.is_symlink():
            p.unlink()
            changed.append(f"removed new file {rel}")
    return changed


# ---------------------------------------------------------------- app starters

def start_nextjs(wt: Path, args, procs: Procs, logs: Path, info: dict) -> str:
    (port,) = pick_ports(1)
    info["ports"] = {"web": port}
    env = base_env()
    if not (wt / "node_modules").is_dir():
        cmd = ["npm", "ci", "--no-audit", "--no-fund"] if (wt / "package-lock.json").exists() \
            else ["npm", "install", "--no-audit", "--no-fund"]
        if run(cmd, wt, env, logs / "install.log") != 0:
            raise StartError("npm install failed (logs/install.log)")
    if args.mode == "build":
        t0 = time.time()
        rc = run(["npx", "--no-install", "next", "build"], wt, env, logs / "build.log", timeout=args.timeout)
        info["build"] = {"rc": rc, "s": round(time.time() - t0, 1)}
        if rc != 0:
            raise StartError("next build failed (logs/build.log)")
        cmd = ["npx", "--no-install", "next", "start", "-p", str(port), "-H", "127.0.0.1"]
    else:
        cmd = ["npx", "--no-install", "next", "dev", "-p", str(port), "-H", "127.0.0.1"]
    p = procs.start("next", cmd, wt, env, logs / "server.log")
    base = f"http://127.0.0.1:{port}"
    info["ready_s"] = procs.wait_http("next", p, base + "/", args.timeout)
    return base


def read_dotenv(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if m and not line.lstrip().startswith("#"):
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def start_fastapi_frontend(wt: Path, args, procs: Procs, logs: Path, info: dict) -> str:
    pg_port, api_port, web_port = pick_ports(3)
    info["ports"] = {"postgres": pg_port, "api": api_port, "web": web_port}
    pgbin = Path(args.pgbin)
    # Unix socket is disabled below (macOS caps socket paths at 103 bytes), so any temp dir works
    tmp = Path(tempfile.mkdtemp(prefix="shot-"))
    procs.cleanups.append(lambda: shutil.rmtree(tmp, ignore_errors=True))
    env0 = base_env()

    # Postgres
    pw = tmp / "pw"
    pw.write_text("changethis\n")
    if run([pgbin / "initdb", "-D", tmp / "pg", "-U", "postgres", f"--pwfile={pw}", "-A", "scram-sha-256"],
           tmp, env0, logs / "postgres.log") != 0:
        raise StartError("initdb failed (logs/postgres.log)")
    if run([pgbin / "pg_ctl", "-D", tmp / "pg", "-w", "-l", tmp / "pg.log", "-o",
            f"-p {pg_port} -c unix_socket_directories='' -c listen_addresses=127.0.0.1", "start"],
           tmp, env0, logs / "postgres.log", timeout=60) != 0:
        raise StartError("pg_ctl start failed (logs/postgres.log)")
    procs.cleanups.append(lambda: subprocess.run(
        [pgbin / "pg_ctl", "-D", tmp / "pg", "-m", "fast", "-w", "stop"], capture_output=True, timeout=60))
    if run([pgbin / "psql", "-h", "127.0.0.1", "-p", str(pg_port), "-U", "postgres", "-c", "CREATE DATABASE app;"],
           tmp, base_env({"PGPASSWORD": "changethis"}), logs / "postgres.log") != 0:
        raise StartError("createdb failed (logs/postgres.log)")

    # backend
    web_origin = f"http://127.0.0.1:{web_port}"
    api = f"http://127.0.0.1:{api_port}"
    benv = base_env({"DATABASE_URL": f"postgresql://postgres:changethis@127.0.0.1:{pg_port}/app",
                     "FASTAPI_ENV": "development", "FRONTEND_HOST": web_origin,
                     "SMTP_HOST": "", "EMAILS_FROM_EMAIL": ""})
    backend = wt / "backend"
    if not (wt / ".venv").is_dir():
        if run(["uv", "sync", "--frozen", "-q"], wt, env0, logs / "install.log") != 0 and \
                run(["uv", "sync", "-q"], wt, env0, logs / "install.log") != 0:
            raise StartError("uv sync failed (logs/install.log)")
    for cmd in (["uv", "run", "alembic", "upgrade", "head"], ["uv", "run", "python", "app/initial_data.py"]):
        if run(cmd, backend, benv, logs / "backend-setup.log", timeout=300) != 0:
            raise StartError(f"{' '.join(cmd)} failed (logs/backend-setup.log)")
    pb = procs.start("backend", ["uv", "run", "fastapi", "run", "app/main.py", "--host", "127.0.0.1",
                                 "--port", str(api_port)], backend, benv, logs / "backend.log")
    info["backend_ready_s"] = procs.wait_http("backend", pb, api + "/api/v1/utils/health-check/", args.timeout,
                                              ok=lambda s: s == 200)

    # frontend
    if not (wt / "node_modules").is_dir():
        if run(["bun", "install", "--frozen-lockfile"], wt, env0, logs / "install.log") != 0 and \
                run(["bun", "install"], wt, env0, logs / "install.log") != 0:
            raise StartError("bun install failed (logs/install.log)")
    fe = wt / "frontend"
    fenv = base_env({"VITE_API_URL": api})
    if args.mode == "build":
        dist = tmp / "dist"
        t0 = time.time()
        rc = run(["bunx", "tsc", "-p", "tsconfig.build.json"], fe, fenv, logs / "build.log", timeout=args.timeout)
        rc2 = run(["bunx", "vite", "build", "--outDir", dist, "--emptyOutDir"], fe, fenv, logs / "build.log",
                  timeout=args.timeout) if rc == 0 else None
        info["build"] = {"tsc_rc": rc, "vite_rc": rc2, "s": round(time.time() - t0, 1)}
        if rc != 0 or rc2 != 0:
            raise StartError("frontend build failed (logs/build.log)")
        cmd = ["bunx", "vite", "preview", "--outDir", str(dist), "--host", "127.0.0.1", "--port", str(web_port),
               "--strictPort"]
    else:
        cmd = ["bunx", "vite", "--host", "127.0.0.1", "--port", str(web_port), "--strictPort"]
    pf = procs.start("frontend", cmd, fe, fenv, logs / "server.log")
    info["ready_s"] = procs.wait_http("frontend", pf, web_origin + "/", args.timeout)

    # login + seed
    dot = read_dotenv(wt / ".env")
    user, pwd = dot.get("FIRST_SUPERUSER"), dot.get("FIRST_SUPERUSER_PASSWORD")
    data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
    with urllib.request.urlopen(urllib.request.Request(api + "/api/v1/login/access-token", data=data),
                                timeout=10) as r:
        token = json.loads(r.read())["access_token"]
    info["auth_user"] = user
    for i in range(1, args.seed_items + 1):
        body = json.dumps({"title": f"Seed item {i}", "description": f"Seeded by screenshot.py ({i})"}).encode()
        req = urllib.request.Request(api + "/api/v1/items/", data=body, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).close()
    info["seeded_items"] = args.seed_items
    info["_token"] = token
    return web_origin


# ---------------------------------------------------------------- screenshots

def ensure_chromium(pw):
    try:
        b = pw.chromium.launch()
        return b
    except Exception as e:  # noqa: BLE001
        if "Executable doesn't exist" not in str(e) and "playwright install" not in str(e):
            raise
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    return pw.chromium.launch()


def capture(base: str, routes: list[str], out: Path, args, token: str | None) -> list[dict]:
    from playwright.sync_api import sync_playwright

    w, h = (int(x) for x in args.viewport.split("x"))
    results = []
    with sync_playwright() as pw:
        browser = ensure_chromium(pw)
        try:
            for route in routes:
                anon = route.endswith("@anon")
                path = route[:-5] if anon else route
                ctx = browser.new_context(viewport={"width": w, "height": h})
                if token and not anon:
                    ctx.add_init_script(f"window.localStorage.setItem('access_token', {json.dumps(token)});")
                page = ctx.new_page()
                console, page_errors, http_errors = [], [], []
                page.on("console", lambda m, c=console: c.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e, c=page_errors: c.append(str(e)))
                page.on("response", lambda r, c=http_errors: c.append({"url": r.url, "status": r.status})
                        if r.status >= 400 else None)
                rec = {"route": route, "url": base + path, "file": None}
                try:
                    resp = page.goto(base + path, wait_until="networkidle", timeout=args.nav_timeout * 1000)
                    page.wait_for_timeout(args.settle_ms)
                    rec["status"] = resp.status if resp else None
                    rec["final_url"] = page.url
                    rec["title"] = page.title()
                    # DOM facts for automatic checks (text, links, <html lang>) next to the picture
                    rec["html_lang"] = page.evaluate("document.documentElement.getAttribute('lang')")
                    rec["text"] = page.evaluate("document.body ? document.body.innerText : ''")[:20000]
                    rec["links"] = page.evaluate("""Array.from(document.querySelectorAll('a')).slice(0, 200).map(a => ({
                        href: a.getAttribute('href'), text: a.innerText.trim().slice(0, 120),
                        aria_current: a.getAttribute('aria-current')}))""")
                    f = out / f"{slug(route)}.png"
                    page.screenshot(path=str(f), full_page=True)
                    rec["file"] = f.name
                except Exception as e:  # noqa: BLE001
                    rec["error"] = f"{type(e).__name__}: {e}".splitlines()[0][:300]
                rec["console_errors"] = console
                rec["page_errors"] = page_errors
                rec["http_errors"] = http_errors
                results.append(rec)
                ctx.close()
        finally:
            browser.close()
    return results


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worktree", required=True, type=Path)
    ap.add_argument("--kind", required=True, choices=["nextjs", "fastapi-frontend"])
    ap.add_argument("--routes", required=True, nargs="+", help='e.g. / /about /users/101 ("/login@anon" = no auth)')
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mode", choices=["build", "dev"], default="build")
    ap.add_argument("--timeout", type=int, default=300, help="build / readiness timeout, seconds")
    ap.add_argument("--nav-timeout", type=int, default=30, help="per-route navigation timeout, seconds")
    ap.add_argument("--settle-ms", type=int, default=500, help="wait after networkidle before the shot")
    ap.add_argument("--viewport", default="1280x800")
    ap.add_argument("--seed-items", type=int, default=3, help="fastapi-frontend only")
    ap.add_argument("--pgbin", default=os.environ.get("PGBIN", PGBIN_DEFAULT), help="fastapi-frontend only")
    args = ap.parse_args()

    wt = args.worktree.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir(exist_ok=True)
    for old in list(out.glob("*.png")) + list(logs.glob("*.log")):
        old.unlink()

    def on_signal(signum, _frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, on_signal)

    info = {"kind": args.kind, "worktree": str(wt), "mode": args.mode, "routes": args.routes,
            "git_head": git(wt, "rev-parse", "HEAD").strip(),
            "git_status": git(wt, "status", "--porcelain").splitlines(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    snap = snapshot(wt)
    procs = Procs()
    screens, rc = [], 0
    try:
        starter = start_nextjs if args.kind == "nextjs" else start_fastapi_frontend
        base = starter(wt, args, procs, logs, info)
        info["base_url"] = base
        screens = capture(base, args.routes, out, args, info.pop("_token", None))
        rc = 0 if all(s.get("file") and (s.get("status") or 0) < 500 for s in screens) else 1
    except StartError as e:
        info["start_error"] = str(e)
        rc = 2
    except BaseException as e:  # noqa: BLE001 - always fall through to cleanup + manifest
        info["start_error"] = f"{type(e).__name__}: {e}"
        rc = 2
    finally:
        info["stop_notes"] = procs.stop()
        info["worktree_restored"] = restore(wt, snap)
        info.pop("_token", None)
        info["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        info["screens"] = screens
        (out / "screens.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"out": str(out), "rc": rc, "start_error": info.get("start_error"),
                      "shots": [(s["route"], s.get("status"), s.get("file")) for s in screens]}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
