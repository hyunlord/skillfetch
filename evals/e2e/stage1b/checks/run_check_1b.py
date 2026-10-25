#!/usr/bin/env python3
"""Frozen outcome checks for skillfetch e2e stage 1b (one task per call). Reuses the stage-1 Check machinery
(stage1/checks/run_check.py: worktree guard, chk_ databases, screenshot lock) without modifying it.

usage: python3 stage1b/checks/run_check_1b.py <task_id> <worktree> <outdir> --pg postgresql://postgres:changethis@localhost:55432
       [--lock FILE] [--base SHA]
Writes <outdir>/check.json = {task_id, pass, items, visual, info, ...}; pass = all non-null items true.
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "stage1" / "checks"))
import run_check as rc1  # noqa: E402  (stage-1 frozen module, imported read-only)
from run_check import Check, base_env, changed_paths, git, restore, route_rec, snapshot, tail  # noqa: E402

UTILS_BASELINE_PCT = 89.06  # app/utils.py, full upstream suite (57/64 statements)
VIEWPORTS = [("screens", []), ("screens-375", ["--viewport", "375x800"])]


def added_paths(c: Check) -> list[str]:
    base_files = set(git(c.wt, "ls-tree", "-r", "--name-only", c.base).splitlines())
    return [p for p in changed_paths(c) if p not in base_files and (c.wt / p).exists()]


def shot_route(c: Check, kind: str, route: str, extra=()):
    """Desktop + mobile screenshot of one route; items: status 200, no page errors, (optionally) no redirect."""
    out = {}
    for sub, vp in VIEWPORTS:
        rc, m = c.screenshot(sub, kind, [route], [*extra, *vp])
        r = route_rec(m, route)
        err = (m or {}).get("start_error")
        c.add(f"screenshot {sub} {route}", rc == 0, f"rc={rc}" + (f", start_error={err}" if err else ""))
        ok = r.get("status") == 200 and not r.get("page_errors")
        c.add(f"{sub} {route.split('@')[0]}: status 200, no page_errors", ok,
              f"status={r.get('status')} page_errors={(r.get('page_errors') or [])[:2]} final_url={r.get('final_url')}")
        for png in sorted((c.out / sub).glob("*.png")):
            c.visual.append(str(png))
        out[sub] = r
    c.add("visual: landing page (hero, features, CTA[, pricing]); AI-look checklist", None, "blind judging")
    return out


def frontend_prepare(c: Check):
    if not (c.wt / "node_modules").is_dir():
        rc, _ = c.sh("bun install", ["bun", "install", "--frozen-lockfile"], c.wt, timeout=900)
        if rc != 0:
            c.sh("bun install (unfrozen)", ["bun", "install"], c.wt, timeout=900)


def frontend_static(c: Check):
    fe = c.wt / "frontend"
    rc, out = c.sh("tsc", ["bunx", "tsc", "-p", "tsconfig.build.json"], fe, timeout=600)
    c.add("frontend: bunx tsc -p tsconfig.build.json", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
    rc, out = c.sh("biome ci", ["bunx", "biome", "ci", "./"], fe, timeout=600)
    c.add("frontend: bunx biome ci ./", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))


def route_from_file(rel: str) -> str | None:
    """TanStack file route path for frontend/src/routes/<...>.tsx; None for pathless/_layout or generated files."""
    p = rel[len("frontend/src/routes/"):]
    if not re.search(r"\.(tsx|ts)$", p) or p.endswith("routeTree.gen.ts") or p.startswith("-"):
        return None
    segs = re.sub(r"\.(tsx|ts)$", "", p).replace(".", "/").split("/")
    if any(s.startswith("_layout") for s in segs) or segs[0] == "__root":
        return None
    segs = [s for s in segs if not (s.startswith("_") or (s.startswith("(") and s.endswith(")")) or s in ("index", "route"))]
    return "/" + "/".join(segs) if segs else "/"


# ------------------------------------------------------------------ tasks

def nx_landing(c: Check):
    c.nx_prepare()
    c.nx_build()
    shot_route(c, "nextjs", "/landing")


def fa_landing(c: Check):
    frontend_prepare(c)
    frontend_static(c)
    new = [p for p in added_paths(c) if p.startswith("frontend/src/routes/")]
    routes = sorted({r for r in (route_from_file(p) for p in new) if r and r != "/"}, key=len)
    c.add("new public route file under frontend/src/routes (outside _layout)", bool(routes), f"new files={new} routes={routes}")
    c.info["route"] = routes[0] if routes else None
    if routes:
        recs = shot_route(c, "fastapi-frontend", routes[0] + "@anon")
        for sub, r in recs.items():
            path = re.sub(r"^https?://[^/]+", "", r.get("final_url") or "").split("?")[0].rstrip("/") or "/"
            c.add(f"{sub}: visited without login, not redirected", path == routes[0], f"final path={path}")


def fa_tags_plan(c: Check):
    plans = [p for p in git(c.wt, "ls-files", "--others", "--cached", "--exclude-standard").splitlines()
             if Path(p).name == "PLAN.md"]
    c.add("PLAN.md exists", bool(plans), f"{plans}")
    c.info["plan_paths"] = plans
    added = added_paths(c)
    revs = [p for p in added if p.startswith("backend/app/alembic/versions/") and p.endswith(".py")]
    c.add("new alembic revision file", bool(revs), f"{revs}")
    res = c.fa_pytest("suite")
    c.fa_items(res)
    c.add("backend tests: no failures (incl. new ones)", not res["error"] and res["existing"]["failed"] == 0,
          f"passed={res['existing']['passed']} failed={res['existing']['failed']}")
    with c.chk_db() as (_, url):
        rcu, out = c.alembic(url, "upgrade", "head")
        c.add("fresh DB: alembic upgrade head", rcu == 0, "" if rcu == 0 else tail(out, 5))
        rcc, out = c.alembic(url, "check")
        c.add("alembic check (models == migrations)", rcu == 0 and rcc == 0, tail(out, 3))
        code = ("import json; from app.main import app; s=app.openapi()['components']['schemas']; "
                "print(json.dumps(sorted(s.get('ItemPublic', {}).get('properties', {}))))")
        rco, out = c.sh("openapi ItemPublic", ["uv", "run", "python", "-c", code], c.wt / "backend", c.fa_env(url), timeout=300)
        props = json.loads(out.strip().splitlines()[-1]) if rco == 0 and out.strip() else []
        c.add("openapi ItemPublic has a property containing 'tag'", any("tag" in p.lower() for p in props), f"{props}")
    frontend_prepare(c)
    frontend_static(c)
    c.add("plan rubric + plan followed", None, "blind judging (plans-blind)")


def fa_service(c: Check):
    res = c.fa_pytest("suite")
    c.fa_items(res)
    svc = [p for p in added_paths(c) if p.startswith("backend/app/") and "service" in p.lower() and p.endswith(".py")]
    c.add("new module with 'service' in its path under backend/app", bool(svc), f"{svc}")
    items = c.wt / "backend/app/api/routes/items.py"
    src = items.read_text() if items.is_file() else ""
    c.add("items.py imports the service module", bool(re.search(r"^\s*(from|import)\s+\S*service", src, re.M | re.I)), "")
    c.info["items_py_direct_db_calls"] = len(re.findall(r"session\.(exec|get|add|delete|commit|refresh)\(|\bselect\(", src))
    c.info["items_py_lines"] = len(src.splitlines())


def fa_utils_tests(c: Check):
    c.uv_sync()
    added = added_paths(c)
    tests = [p for p in added if p.startswith("backend/tests/") and Path(p).name.startswith("test") and p.endswith(".py")]
    utils_tests = [p for p in tests if re.search(r"app\.utils|from app import .*\butils\b|app/utils", (c.wt / p).read_text(errors="replace"))]
    c.add("new test file under backend/tests that imports app.utils", bool(utils_tests), f"new tests={tests}")
    c.info["new_test_files"] = tests
    covfile = c.out / ".coverage"
    for label, targets in (("suite", ["tests/"]), ("new-only", [p[len("backend/"):] for p in utils_tests])):
        if not targets:
            continue
        with c.chk_db() as (_, url):
            rcu, out = c.alembic(url, "upgrade", "head")
            env = c.fa_env(url)
            env["COVERAGE_FILE"] = str(covfile)
            covfile.unlink(missing_ok=True)
            rc, out = c.sh(f"coverage {label}", ["uv", "run", "coverage", "run", "--source=app", "-m", "pytest", *targets,
                                                 "-q", "-p", "no:cacheprovider"], c.wt / "backend", env, timeout=1800)
            m = re.search(r"(\d+) passed", out)
            f = re.search(r"(\d+) failed", out)
            jf = c.out / f"cov-{label}.json"
            c.sh(f"coverage json {label}", ["uv", "run", "coverage", "json", "-o", str(jf), "--include=app/utils.py"],
                 c.wt / "backend", env, timeout=300)
            pct = None
            if jf.exists():
                d = json.loads(jf.read_text())
                pct = round(d.get("totals", {}).get("percent_covered", 0.0), 2)
        c.info[f"utils_coverage_{label}"] = pct
        c.info[f"pytest_{label}"] = {"rc": rc, "passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0}
        if label == "suite":
            c.add("all backend tests pass (>= 58)", rc == 0 and m and int(m.group(1)) >= 58 and not f, tail(out, 2))
            c.add(f"app/utils.py coverage (full suite) > {UTILS_BASELINE_PCT}%", pct is not None and pct > UTILS_BASELINE_PCT,
                  f"{pct}%")
    covfile.unlink(missing_ok=True)


TASKS = {"s1b-nx-landing": nx_landing, "s1b-fa-landing": fa_landing, "s1b-fa-tags-plan": fa_tags_plan,
         "s1b-fa-service": fa_service, "s1b-fa-utils-tests": fa_utils_tests}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id", choices=sorted(TASKS))
    ap.add_argument("worktree", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--pg")
    ap.add_argument("--lock")
    ap.add_argument("--base")
    ap.add_argument("--pgbin", default="/opt/homebrew/opt/postgresql@16/bin")
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, rc1.on_signal)
    signal.signal(signal.SIGHUP, rc1.on_signal)
    wt, out = a.worktree.resolve(), a.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    c = Check(a.task_id, wt, out, a.pg, a.lock, a.base, a.pgbin)
    c.info = {}
    snap = snapshot(wt)
    error = None
    try:
        TASKS[a.task_id](c)
    except BaseException as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
        c.add("check ran to completion", False, error)
    finally:
        restored = restore(wt, snap)
        res = {"task_id": a.task_id,
               "pass": error is None and all(i["pass"] is not False for i in c.items) and any(i["pass"] for i in c.items),
               "items": c.items, "visual": c.visual, "info": c.info, "duration_s": round(time.time() - t0, 1),
               "worktree": str(wt), "base": c.base, "worktree_restored": restored,
               "git_status_unchanged": git(wt, "status", "--porcelain") == snap["status"]}
        (out / "check.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"task_id": a.task_id, "pass": res["pass"], "failed": [i["name"] for i in c.items if i["pass"] is False]},
                     ensure_ascii=False))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
