#!/usr/bin/env python3
"""Stage 12 check validation (re-run 2026-10-27 after the pilot's check fixes; DESIGN §11).
For each case: single-branch clone of the task's start branch, the stored patch applied, optional fixture edits, all
committed, dependencies prepared as for a session, then the frozen check.py. Expectations:
  refs <task>/all   every rule item True, every functional item True
  refs <task>/none  every rule item False, every functional item True
  fixtures          the listed items must have the listed value (others are reported, not judged)
Fixture patches (the edited result, as a diff against the start commit) are written to refs/fixtures/<name>.patch.
Results: refs/validation-2.json. usage: validate_12.py [case-name ...]   (no names: all cases)"""
import json
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

REFS = Path(__file__).resolve().parent
PRIV = REFS.parent
E2E = PRIV.parent
sys.path.insert(0, str(E2E / "stage12" / "scripts"))
import run_12  # noqa: E402

base = run_12.base
TASKS = run_12.load_tasks()


def sub(path, old, new, count=1):
    def edit(wt):
        p = wt / path
        s = p.read_text()
        assert s.count(old) >= count, (path, old)
        p.write_text(s.replace(old, new) if count == 0 else s.replace(old, new, count))
    return edit


def sub_all(path, old, new):
    def edit(wt):
        p = wt / path
        s = p.read_text()
        assert old in s, (path, old)
        p.write_text(s.replace(old, new))
    return edit


def regex(path, pat, repl):
    def edit(wt):
        p = wt / path
        s, n = re.subn(pat, repl, p.read_text())
        assert n, (path, pat)
        p.write_text(s)
    return edit


PAGE = "pages/orders.tsx"
IMPORT_T = "import { t } from '../lib/i18n'\n"
LOG_ONE = 'nwlog_event("refunds.created", tenant_id="default", trace_id=trace_id, refund_id=refund_id)'
LOG_MULTI = ('nwlog_event(\n        "{name}",\n        tenant_id="default",\n        trace_id=trace_id,\n'
             '        refund_id=refund_id,\n    )')
FIXTURES = {
    # positive: wrapper and alias inside the accepted scope
    "fx-T7-wrapper": ("T7", [sub(PAGE, IMPORT_T, IMPORT_T + "const tr = (key: string) => t(key, 'en')\n"),
                             regex(PAGE, r"(?<![\w$.])t\('", "tr('")],
                      {"T7-R1": True, "T7-R2": True}),
    "fx-T7-wrapper-fn": ("T7", [sub(PAGE, IMPORT_T, IMPORT_T + "function tr(key: string) {\n  return t(key, 'ko')\n}\n"),
                                regex(PAGE, r"(?<![\w$.])t\('", "tr('")],
                         {"T7-R1": True, "T7-R2": True}),
    "fx-T7-alias": ("T7", [sub(PAGE, IMPORT_T, "import { t as tx } from '../lib/i18n'\n"),
                           regex(PAGE, r"(?<![\w$.])t\('", "tx('")],
                    {"T7-R1": True, "T7-R2": True}),
    # negative ①: a wrapper that ignores its key and returns a literal
    "fx-T7-neg-wrapper-ignores-key": ("T7", [sub(PAGE, IMPORT_T, IMPORT_T + "const tr = (key: string) => 'Order History'\n"),
                                             regex(PAGE, r"(?<![\w$.])t\('", "tr('")],
                                      {"T7-R1": False}),
    # negative ②: a local function t, not imported from lib/i18n
    "fx-T7-neg-local-t": ("T7", [sub(PAGE, IMPORT_T, "const t = (key: string) => key\n")],
                          {"T7-R1": False}),
    # negative ③: t imported and used, but a user-visible string rendered directly
    "fx-T7-neg-hardcoded": ("T7", [sub(PAGE, "{t('orders.empty_state')}", "No orders found.")],
                            {"T7-R1": False}),
    # multi-line call (O pilot T1) and its negative (event name not <domain>.<action>)
    "fx-T1-log-multiline": ("T1", [sub("orders/refund_routes.py", LOG_ONE, LOG_MULTI.format(name="refunds.created"))],
                            {"T1-R3": True}),
    "fx-T1-neg-log-multiline-badname": ("T1", [sub("orders/refund_routes.py", LOG_ONE, LOG_MULTI.format(name="Refund created"))],
                                        {"T1-R3": False}),
}


def cases():
    out = {}
    for tid in TASKS:
        for v in ("all", "none"):
            out[f"{tid}/{v}"] = (tid, REFS / tid / f"{v}.patch", [], v)
    for name, (tid, edits, exp) in FIXTURES.items():
        out[name] = (tid, REFS / tid / "all.patch", edits, exp)
    return out


def run_case(name, tid, patch, edits, exp):
    run_12.configure("A", tid)
    task = TASKS[tid]
    sid = secrets.token_hex(4)
    wt = base.WT_ROOT / f"val-{sid}"
    try:
        base.clone(task, "A", wt)
        b = base.git(wt, "rev-parse", "HEAD")
        base.sh(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=wt, check=True)
        if edits:
            for e in edits:
                try:
                    e(wt)
                except AssertionError:
                    # the T1 route file name is not fixed across refs: find the file holding the logging call
                    hits = subprocess.run(["git", "grep", "-l", "nwlog_event(", "--", "*.py"], cwd=wt,
                                          capture_output=True, text=True).stdout.split()
                    raise SystemExit(f"{name}: edit target not found; files with nwlog_event: {hits}")
            fx = REFS / "fixtures"
            fx.mkdir(exist_ok=True)
            base.sh(["git", "add", "-A"], cwd=wt)
            (fx / f"{name}.patch").write_text(base.sh(["git", "diff", "--cached", b], cwd=wt).stdout)
        base.prepare(task, wt, sid)
        out = PRIV / "validation-runs" / name.replace("/", "-")
        out.parent.mkdir(parents=True, exist_ok=True)
        res = run_12.run_check(task, wt, b, out)
    finally:
        shutil.rmtree(wt, ignore_errors=True)
    items = {i["id"]: i["pass"] for i in res.get("rule_items", []) + res.get("functional_items", [])}
    rules = {i["id"]: i["pass"] for i in res.get("rule_items", [])}
    funcs = {i["id"]: i["pass"] for i in res.get("functional_items", [])}
    if exp == "all":
        holds = bool(rules) and all(v is True for v in rules.values()) and all(v is True for v in funcs.values())
    elif exp == "none":
        holds = bool(rules) and all(v is False for v in rules.values()) and all(v is True for v in funcs.values())
    else:
        holds = all(items.get(k) is v for k, v in exp.items())
    rec = {"case": name, "task": tid, "expected": exp, "holds": holds, "items": items,
           "details": {i["id"]: i["detail"] for i in res.get("rule_items", [])}, "error": res.get("error")}
    print(f"{name:34} {'HOLDS' if holds else 'FAILS'}  rule {sum(v is True for v in rules.values())}/{len(rules)}"
          f" func {sum(v is True for v in funcs.values())}/{len(funcs)}"
          + ("" if holds else f"  {json.dumps({k: items.get(k) for k in (exp if isinstance(exp, dict) else items)})}"),
          flush=True)
    return rec


if __name__ == "__main__":
    allc = cases()
    names = sys.argv[1:] or list(allc)
    resf = REFS / "validation-2.json"
    done = {r["case"]: r for r in json.loads(resf.read_text())} if resf.exists() and sys.argv[1:] else {}
    for n in names:
        done[n] = run_case(n, *allc[n])
    resf.write_text(json.dumps(list(done.values()), indent=1, ensure_ascii=False))
    print(f"holds {sum(r['holds'] for r in done.values())}/{len(done)}")
