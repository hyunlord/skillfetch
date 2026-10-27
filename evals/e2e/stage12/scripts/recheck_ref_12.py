#!/usr/bin/env python3
"""Stage 12b T8 reference check (stage12b/DESIGN.md §4): the frozen check stays the gate; this re-measures stored
outputs with stage12-private/checks-ref/, a copy of checks/ with two changes: _lib.WEB_SKIP no longer drops "lib/"
(the user's request), and T8-F1 also counts a call with TypeScript type arguments, fetchApi<T>(...) (the cause of the six
T8-F1 failures in Stage 12: each session's only API calls were fetchApi<Order[]>(...) / fetchApi<void>(...)). Same
procedure as recheck_12.py: single-branch clone of the session's branch at its base, the stored diff applied, deps
prepared, snapshot commit, then checks-ref/<task>/check.py. Nothing in meta.json changes; results go to
runs/<cond>/<task>-<tag>.check-ref/check.json (sessions) or refs/validation-ref/<case>/check.json (validation).
Validation cases (--validate): T8 all, T8 none, and fixture fx-T8-cancel-in-lib (T8 all with the cancel call moved
from pages/orders.tsx into a new lib/orders.ts as fetchApi<void>(...); frozen check: T8-F1 False, reference: True).
usage: recheck_ref_12.py --validate | <cond>/<task>-<tag> [...]"""
import json
import secrets
import shutil
import sys
from pathlib import Path

import run_12

base = run_12.base
PRIV = run_12.PRIV
REF = PRIV / "checks-ref"


def ref_check(task, wt, b, outdir):
    base.rs.strip_env_noise(wt)
    run_12.snapshot_commit(wt)
    outdir.mkdir(parents=True, exist_ok=True)
    p = base.sh(["python3", str(REF / task["id"] / "check.py"), str(wt), str(outdir), "--base", b], env=base.env_s11(),
                timeout=3600)
    (outdir / "run_check.log").write_text((p.stdout + p.stderr).replace(str(wt), "<wt>"))
    cj = outdir / "check.json"
    return json.loads(cj.read_text()) if cj.exists() else {"error": f"rc={p.returncode}"}


def in_clone(cond, task_id, apply, outdir, want_base=None):
    run_12.configure(cond, task_id)
    task = run_12.load_tasks()[task_id]
    sid = secrets.token_hex(4)
    wt = base.WT_ROOT / f"refchk-{sid}"
    try:
        base.clone(task, cond, wt)
        b = base.git(wt, "rev-parse", "HEAD")
        assert want_base is None or b == want_base, "clone head != session base"
        apply(wt)
        base.prepare(task, wt, sid)
        return ref_check(task, wt, b, outdir)
    finally:
        shutil.rmtree(wt, ignore_errors=True)


def apply_patch(path):
    def f(wt):
        if Path(path).read_text().strip():
            base.sh(["git", "apply", "--whitespace=nowarn", str(path)], cwd=wt, check=True)
    return f


def cancel_in_lib(wt):
    apply_patch(PRIV / "refs" / "T8" / "all.patch")(wt)
    page = wt / "pages" / "orders.tsx"
    s = page.read_text()
    old = "    await fetchApi(`/orders/${cancelTarget}/cancel`, { method: 'POST' })\n"
    assert old in s
    s = s.replace(old, "    await cancelOrder(cancelTarget)\n").replace(
        "import { fetchApi } from '../lib/api'\n", "import { fetchApi } from '../lib/api'\nimport { cancelOrder } from '../lib/orders'\n")
    page.write_text(s)
    s2 = page.read_text().replace("import { fetchApi } from '../lib/api'\n", "")
    page.write_text(s2)
    (wt / "lib" / "orders.ts").write_text("import { fetchApi } from './api'\n\nexport function cancelOrder(id: string) {\n"
                                         "  return fetchApi<void>(`/orders/${id}/cancel`, { method: 'POST' })\n}\n")


def items(res):
    return {i["id"]: i["pass"] for i in res.get("rule_items", []) + res.get("functional_items", [])}


def validate():
    out, ok = {}, True
    for name, apply, exp in (("T8-all", apply_patch(PRIV / "refs" / "T8" / "all.patch"), "all"),
                             ("T8-none", apply_patch(PRIV / "refs" / "T8" / "none.patch"), "none"),
                             ("fx-T8-cancel-in-lib", cancel_in_lib, {"T8-F1": True})):
        res = in_clone("A", "T8", apply, PRIV / "refs" / "validation-ref" / name)
        it = items(res)
        rules = {k: v for k, v in it.items() if "-R" in k}
        funcs = {k: v for k, v in it.items() if "-F" in k}
        holds = (all(rules.values()) and all(funcs.values())) if exp == "all" else \
            (not any(rules.values()) and all(funcs.values())) if exp == "none" else all(it.get(k) is v for k, v in exp.items())
        ok &= holds
        out[name] = {"expected": exp, "holds": holds, "items": it}
        print(name, "HOLDS" if holds else "FAILS", it)
    (PRIV / "refs" / "validation-ref.json").write_text(json.dumps(out, indent=1))
    return ok


def session(key):
    cond, rest = key.split("/")
    task_id, tag = rest.rsplit("-", 1)
    out = PRIV / "runs" / cond / f"{task_id}-{tag}"
    m = json.loads(Path(str(out) + ".meta.json").read_text())
    res = in_clone(cond, task_id, apply_patch(Path(str(out) + ".diff")), Path(str(out) + ".check-ref"), m["base"])
    print(key, {k: v for k, v in items(res).items()})


if __name__ == "__main__":
    if sys.argv[1:] == ["--validate"]:
        sys.exit(0 if validate() else 1)
    for k in sys.argv[1:]:
        session(k)
