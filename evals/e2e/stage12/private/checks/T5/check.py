#!/usr/bin/env python3
"""Check: T5 — switchable discount logic."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
from orders.pricing import calculate_total, apply_tax
out["calc"] = calculate_total(10.0, 2, 10.0)
out["tax"] = apply_tax(100.0)
code, body = call("POST", "/orders", json={"customer_id": 1, "product": "A", "quantity": 2, "unit_price": 5.0})
out["create"] = [code, body]
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T5-R1", *L.check_flags_in_new_code(w, base)))
    rules.append(L.item("T5-R2", *L.check_flags_registry(w, base)))
    rules.append(L.item("T5-R3", *L.check_nwlog_in_new_code(w, base)))
    rules.append(L.item("T5-R4", *L.check_no_print_logging(w, base)))
    rules.append(L.item("T5-R5", *L.check_changelog(w, base)))

    # Functional (convention-independent)
    res, err = L.run_app_script(w, SCRIPT)
    res = res or {}
    cr = res.get("create")
    total = cr[1].get("total") if cr and isinstance(cr[1], dict) else None
    ok = res.get("calc") == 18.0 and res.get("tax") == 110.0 and bool(cr) and 200 <= cr[0] < 300 and total in (10.0, 10, None)
    funcs.append(L.item("T5-F1", ok, f"default path: calculate_total(10,2,10)={res.get('calc')} apply_tax(100)={res.get('tax')} order total={total} {err}"))
    pricing_added = [ln for f, ln in L.get_added_lines(w, base) if L._app_code(f)]
    has_branch = any(re.search(r"^\s*(if|elif)\b|\bif\b.+\belse\b", ln) for ln in pricing_added)
    ok_t, d_t = L.run_pytest(w)
    funcs.append(L.item("T5-F2", has_branch and ok_t, f"switch branch in added app code={has_branch}; tests pass={ok_t}"))
    funcs.append(L.item("T5-F3", ok_t, d_t))
    L.write_result(a.outdir, "T5", rules, funcs)


if __name__ == "__main__":
    main()
