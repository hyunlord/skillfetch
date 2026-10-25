#!/usr/bin/env python3
"""Outcome checks for stage 6b bundles (1) and (3), one task per call. Bundle (2) uses stage2/checks/check_s2.py unchanged.
Reuses the stage-1 Check machinery (stage1/checks/run_check.py) and the 1b landing helpers (stage1b/checks/run_check_1b.py),
both imported read-only.

usage: python3 stage6/6b/checks/check_6b.py <task_id> <worktree> <outdir> --pg postgresql://postgres:changethis@localhost:55432
       [--lock FILE] [--base SHA]
Writes <outdir>/check.json = {task_id, pass, items, visual, info, ...}; pass = no item false and at least one true.
Items with pass None are informational (judged blind or not checkable here)."""
from __future__ import annotations

import argparse
import json
import re
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
E2E = HERE.parents[2]
sys.path.insert(0, str(E2E / "stage1" / "checks"))
sys.path.insert(0, str(E2E / "stage1b" / "checks"))
import run_check as rc1  # noqa: E402
from run_check import Check, git, restore, snapshot, tail  # noqa: E402
from run_check_1b import added_paths, frontend_prepare, shot_route  # noqa: E402

SHOT_HTML = HERE / "shot_html.py"
SAMPLE_USER_IDS = (101, 102, 103, 104)  # utils/sample-data.ts at 76de3ce


# ------------------------------------------------------------------ bundle (1) design

def d1_landing(c: Check):
    c.nx_prepare()
    c.nx_build()
    shot_route(c, "nextjs", "/landing")


def d2_redesign(c: Check):
    c.nx_prepare()
    c.nx_build()
    shot_route(c, "nextjs", "/users")
    html = c.wt / ".next" / "server" / "pages" / "users.html"
    if html.exists():
        body = html.read_text(errors="replace")
        missing = [i for i in SAMPLE_USER_IDS if f'href="/users/{i}"' not in body]
        c.add("/users links every sample user to /users/[id] (prerendered HTML)", not missing, f"missing ids={missing}")
    else:
        c.add("/users links every sample user to /users/[id] (prerendered HTML)", None,
              "no .next/server/pages/users.html (page is not statically prerendered); not checked")


def d3_dashboard(c: Check):
    c.nx_prepare()
    c.nx_build()
    shot_route(c, "nextjs", "/dashboard")


def d4_email(c: Check):
    frontend_prepare(c)  # root bun workspace install (covers packages/react-email)
    pkg = c.wt / "packages" / "react-email"
    rc, out = c.sh("email build", ["npm", "run", "build"], pkg, timeout=900)
    c.add("packages/react-email: npm run build", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
    rc, out = c.sh("email export", ["npm", "run", "export"], pkg, timeout=600)
    c.add("packages/react-email: npm run export", rc == 0, f"rc={rc}" + ("" if rc == 0 else "\n" + tail(out, 8)))
    html = c.wt / "backend" / "app" / "email-templates" / "new_account.html"
    c.add("export wrote backend/app/email-templates/new_account.html", rc == 0 and html.exists(), str(html.exists()))
    src = (pkg / "emails" / "new_account.tsx")
    text = src.read_text() if src.exists() else ""
    m = re.search(r"type\s+NewAccountProps\s*=\s*\{([^}]*)\}", text) or re.search(r"interface\s+NewAccountProps\s*\{([^}]*)\}", text)
    fields = sorted(set(re.findall(r"^\s*([A-Za-z_]\w*)\??\s*:", m.group(1), re.M))) if m else []
    c.add("NewAccountProps fields unchanged (project_name, username, password, link)",
          fields == ["link", "password", "project_name", "username"], f"fields={fields}")
    if html.exists():
        snap_html = html.read_bytes()
        for sub, width in (("screens", 600), ("screens-375", 375)):
            out_dir = c.out / sub
            out_dir.mkdir(parents=True, exist_ok=True)
            rcs, outs = c.sh(f"shot html {width}", ["uv", "run", "-q", str(SHOT_HTML), str(html), str(out_dir / "new_account.png"),
                                                     str(width)], c.out, timeout=600)
            res = json.loads(outs.strip().splitlines()[-1]) if rcs == 0 and outs.strip() else {}
            c.add(f"{sub}: email HTML renders at {width}px, no page errors", rcs == 0 and not res.get("page_errors"),
                  f"rc={rcs} page_errors={res.get('page_errors')}")
            for png in sorted(out_dir.glob("*.png")):
                c.visual.append(str(png))
        html.write_bytes(snap_html)
    c.add("visual: welcome email; AI-look checklist", None, "blind judging")


# ------------------------------------------------------------------ bundle (3) no-skill tasks

def backend_suite(c: Check):
    res = c.fa_pytest("suite")
    e = res["existing"]
    c.add("backend tests (incl. new ones): >= 58 passed, 0 failed", not res["error"] and e["failed"] == 0 and e["passed"] >= 58,
          f"passed={e['passed']} failed={e['failed']} rc={res['rc']}" + (f"; {res['error']}" if res["error"] else "")
          + (f"; failed: {res['failed_names'][:6]}" if res["failed_names"] else ""))


def fresh_db_migrations(c: Check):
    with c.chk_db() as (_, url):
        rcu, out = c.alembic(url, "upgrade", "head")
        c.add("fresh DB: alembic upgrade head", rcu == 0, "" if rcu == 0 else tail(out, 5))
        rcc, out = c.alembic(url, "check")
        c.add("alembic check (models == migrations)", rcu == 0 and rcc == 0, tail(out, 3))


def t004(c: Check):
    c.uv_sync()
    py = (c.wt / "backend" / "pyproject.toml").read_text()
    c.add("backend/pyproject.toml depends on celery", bool(re.search(r'"celery\b', py)), "")
    tasks = c.wt / "backend" / "app" / "tasks.py"
    body = tasks.read_text() if tasks.exists() else ""
    c.add("backend/app/tasks.py exists with a periodic schedule (beat_schedule / add_periodic_task / crontab)",
          bool(body) and bool(re.search(r"beat_schedule|add_periodic_task|crontab\(|periodic_task", body)), f"exists={tasks.exists()}")
    models = (c.wt / "backend" / "app" / "models.py").read_text()
    item = models[models.find("class Item(ItemBase, table=True)"):][:1500] if "class Item(ItemBase, table=True)" in models else models
    c.add("Item table model has due_date and reminder_sent_at", "due_date" in item and "reminder_sent_at" in item, "")
    revs = [p for p in added_paths(c) if p.startswith("backend/app/alembic/versions/") and p.endswith(".py")]
    c.add("new alembic revision file", bool(revs), f"{revs}")
    tpl = c.wt / "backend" / "app" / "email-templates" / "item_due_reminder.html"
    c.add("email template backend/app/email-templates/item_due_reminder.html", tpl.exists(), "")
    fresh_db_migrations(c)
    backend_suite(c)


def t133(c: Check):
    df = c.wt / "Dockerfile"
    text = df.read_text() if df.exists() else ""
    c.add("Dockerfile at repo root", df.exists(), "")
    lines = [l.strip() for l in re.sub(r"\\\s*\n", " ", text).splitlines()]  # join `\` continuations
    def idx(pred):
        return next((i for i, l in enumerate(lines) if pred(l)), None)
    i_lock = idx(lambda l: l.upper().startswith("COPY") and ("package-lock.json" in l or "package*.json" in l))
    i_ci = idx(lambda l: l.upper().startswith("RUN") and "npm ci" in l)
    i_all = idx(lambda l: re.match(r"COPY\s+(--\S+\s+)*\.\s+\.?", l, re.I) is not None)
    c.add("package.json + package-lock.json copied before `npm ci`", i_lock is not None and i_ci is not None and i_lock < i_ci,
          f"copy-lock line={i_lock} npm-ci line={i_ci}")
    c.add("rest of the source copied after `npm ci`", i_ci is not None and i_all is not None and i_all > i_ci, f"COPY . line={i_all}")
    c.add("BuildKit cache mount for /root/.npm on npm ci",
          i_ci is not None and bool(re.search(r"--mount=type=cache,[^\s]*target=/root/\.npm", lines[i_ci])), lines[i_ci] if i_ci is not None else "")
    cmd = " ".join(l for l in lines if re.match(r"(CMD|ENTRYPOINT)\b", l, re.I))
    c.add("entry point runs the start script (npm start / next start)", bool(re.search(r"npm[\"',\s]+(run[\"',\s]+)?start|next[\"',\s]+start", cmd)), cmd)
    di = c.wt / ".dockerignore"
    dtext = di.read_text() if di.exists() else ""
    c.add(".dockerignore lists node_modules and .next", bool(re.search(r"^/?node_modules", dtext, re.M)) and bool(re.search(r"^/?\.next", dtext, re.M)), "")
    c.add("docker build", None, "Docker daemon not running on the harness machine; not checked")
    c.nx_prepare()
    c.nx_build()


SEED = """
WITH u AS (SELECT id FROM "user" LIMIT 1)
INSERT INTO item (id, title, description, owner_id, created_at)
SELECT gen_random_uuid(), v.title, v.tag, u.id, v.ts::timestamp FROM u, (VALUES
  ('x', 'x-1', '2026-10-01 09:00'), ('x', 'x-2', '2026-10-02 09:00'), ('x', 'x-3', '2026-10-03 09:00'),
  ('y', 'y-1', '2026-10-02 10:00'),
  ('z', 'z-1', '2026-10-01 11:00'), ('z', 'z-2', '2026-10-03 11:00')) AS v(title, tag, ts);
"""


def t179(c: Check):
    c.uv_sync()
    mod = c.wt / "backend" / "app" / "dedupe_items.py"
    c.add("backend/app/dedupe_items.py exists", mod.exists(), "")
    base_py = git(c.wt, "show", f"{c.base}:backend/pyproject.toml")
    dep = lambda s: sorted(re.findall(r'^\s*"([A-Za-z0-9_.\-\[\]]+)', s.split("dependencies", 1)[1].split("]", 1)[0], re.M)) if "dependencies" in s else []  # noqa: E731
    now_py = (c.wt / "backend" / "pyproject.toml").read_text()
    c.add("no new dependencies in backend/pyproject.toml", dep(now_py) == dep(base_py), f"added={sorted(set(dep(now_py)) - set(dep(base_py)))}")
    if mod.exists():
        with c.chk_db() as (db, url):
            rcu, out = c.alembic(url, "upgrade", "head")
            rci, out2 = c.sh("initial_data", ["uv", "run", "python", "app/initial_data.py"], c.wt / "backend", c.fa_env(url), timeout=300)
            rcs, out3 = c.psql(SEED, db)
            ok_setup = rcu == 0 and rci == 0 and rcs == 0
            c.add("functional setup: migrate, initial_data, seed 6 items (x×3, y×1, z×2)", ok_setup, tail(out + out2 + out3, 4))
            if ok_setup:
                rcd, outd = c.sh("dedupe", ["uv", "run", "python", "app/dedupe_items.py"], c.wt / "backend", c.fa_env(url), timeout=300)
                if rcd != 0:
                    rcd, outd = c.sh("dedupe -m", ["uv", "run", "python", "-m", "app.dedupe_items"], c.wt / "backend", c.fa_env(url), timeout=300)
                c.add("dedupe runs like initial_data (python app/dedupe_items.py or -m app.dedupe_items)", rcd == 0, tail(outd, 4))
                rcq, rows = c.psql("SELECT title || ':' || description FROM item ORDER BY title", db)
                kept = rows.strip().splitlines() if rcq == 0 else []
                c.add("keeps the earliest row per (owner, title): x-1, y-1, z-1", kept == ["x:x-1", "y:y-1", "z:z-1"], f"kept={kept}")
                c.add("prints per-day counts (output has YYYY-MM-DD dates)", bool(re.search(r"2026-10-0[123]", outd)), tail(outd, 6))
    backend_suite(c)


def t354(c: Check):
    c.uv_sync()
    db_py = (c.wt / "backend" / "app" / "core" / "db.py").read_text()
    base_db = git(c.wt, "show", f"{c.base}:backend/app/core/db.py")
    new_funcs = sorted(set(re.findall(r"^def (\w+)", db_py, re.M)) - set(re.findall(r"^def (\w+)", base_db, re.M)))
    c.add("a new function in backend/app/core/db.py", bool(new_funcs), f"{new_funcs}")
    init_src = (c.wt / "backend" / "app" / "initial_data.py").read_text()
    body = init_src[init_src.find("def init"):init_src.find("def main")] if "def init" in init_src else ""
    called = [f for f in new_funcs if f in body]
    order_ok = bool(called) and body.find(called[0]) < body.find("init_db(") if called and "init_db(" in body else False
    c.add("init() calls it before init_db", order_ok, f"called={called}")
    run = lambda url: c.sh("initial_data", ["uv", "run", "python", "app/initial_data.py"], c.wt / "backend", c.fa_env(url), timeout=300)  # noqa: E731
    with c.chk_db() as (_, url):
        rcu, out = c.alembic(url, "upgrade", "head")
        rc, out = run(url)
        c.add("DB at head: initial_data succeeds", rcu == 0 and rc == 0, tail(out, 4))
    with c.chk_db() as (db, url):  # schema at head, but alembic_version names a revision that is not the head
        rcu, out = c.alembic(url, "upgrade", "head")
        rcs, outs = c.psql("UPDATE alembic_version SET version_num = '0000deadbeef'", db)
        rc2, out2 = run(url)
        c.add("DB revision != head (schema intact, alembic_version set to an unknown id): initial_data aborts (non-zero exit)",
              rcu == 0 and rcs == 0 and rc2 != 0, tail(outs + out2, 4))
    backend_suite(c)


TASKS = {"d1-landing": d1_landing, "d2-redesign": d2_redesign, "d3-dashboard": d3_dashboard, "d4-email": d4_email,
         "s6b-t004": t004, "s6b-t133": t133, "s6b-t179": t179, "s6b-t354": t354}


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
