#!/usr/bin/env python3
"""Check: T4 — payment timeout setting."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
out["create"] = call("POST", "/orders", json={"customer_id": 1, "product": "A", "quantity": 2, "unit_price": 5.0})
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T4-R1", *L.check_settings_get(w, base)))
    rules.append(L.item("T4-R2", *L.check_env_md(w, base)))
    rules.append(L.item("T4-R3", *L.check_deploy_checklist(w, base)))
    rules.append(L.item("T4-R4", *L.check_changelog(w, base)))
    ok_imp = L._check_added_lines(w, base, r"from lib\.settings import|from lib import settings|import lib\.settings")[0]
    ok_env, d_env = L.check_no_direct_environ(w, base)
    rules.append(L.item("T4-R5", ok_imp and ok_env, f"lib.settings imported={ok_imp}; {d_env}"))

    # Functional (convention-independent): a timeout setting with default 30 is added to app code,
    # and order creation still works.
    added = "\n".join(ln for f, ln in L.get_added_lines(w, base) if L._app_code(f))
    has_setting = bool(re.search(r"timeout", added, re.I)) and bool(re.search(r"\b30\b", added))
    res, err = L.run_app_script(w, SCRIPT)
    cr = (res or {}).get("create")
    ok = has_setting and bool(cr) and 200 <= cr[0] < 300
    funcs.append(L.item("T4-F1", ok, f"timeout+30 in added app code={has_setting}; POST /orders -> {cr[0] if cr else err}"))
    funcs.append(L.item("T4-F2", *L.run_pytest(w)))
    L.write_result(a.outdir, "T4", rules, funcs)


if __name__ == "__main__":
    main()
