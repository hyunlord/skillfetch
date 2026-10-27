#!/usr/bin/env python3
"""Check: T3 — refund_reason column."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
code, body = call("POST", "/orders", json={"customer_id": 1, "product": "A", "quantity": 1, "unit_price": 5.0})
out["create"] = [code, body]
oid = body.get("id") if isinstance(body, dict) else None
out["get"] = call("GET", f"/orders/{oid}") if oid is not None else None
out["columns"] = [r["name"] for r in q("PRAGMA table_info(orders)")]
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T3-R1", *L.check_migration_file(w, base)))
    rules.append(L.item("T3-R2", *L.check_migration_rollback(w, base)))
    rules.append(L.item("T3-R3", *L.check_deploy_checklist(w, base)))
    rules.append(L.item("T3-R4", *L.check_changelog(w, base)))
    rules.append(L.item("T3-R5", *L.check_migration_in_dir(w, base)))

    # Functional (convention-independent)
    res, err = L.run_app_script(w, SCRIPT)
    g = (res or {}).get("get")
    ok = bool(g) and 200 <= g[0] < 300 and isinstance(g[1], dict) and "refund_reason" in g[1] \
        and "refund_reason" in res.get("columns", [])
    funcs.append(L.item("T3-F1", ok, f"GET /orders/{{id}} -> {g}; columns={res.get('columns') if res else err}"))
    funcs.append(L.item("T3-F2", *L.run_pytest(w)))
    L.write_result(a.outdir, "T3", rules, funcs)


if __name__ == "__main__":
    main()
