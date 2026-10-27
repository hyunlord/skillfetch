#!/usr/bin/env python3
"""Check: T1 — POST /refunds endpoint."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
code, body = call("POST", "/orders", json={"customer_id": 1, "product": "X", "quantity": 1, "unit_price": 10.0})
out["order"] = [code, body]
oid = body.get("id") if isinstance(body, dict) else None
# Any reasonable amount field name is accepted; extra fields are ignored by default models.
base = {"amount": 5.0, "amount_minor": 500, "amount_cents": 500, "refund_amount": 5.0,
        "currency": "USD", "reason": "test", "refund_reason": "test"}
attempts, ok = [], None
for oval in ([oid, str(oid)] if oid is not None else [1, "1"]):
    p = dict(base, order_id=oval)
    code, b = call("POST", "/refunds", json=p)
    attempts.append([code, b])
    if 200 <= code < 300:
        ok = [code, b, p]
        break
out["create_attempts"] = attempts
out["create"] = ok
tables = [r["name"] for r in q("SELECT name FROM sqlite_master WHERE type='table'")]
stored = 0
for t in tables:
    if "refund" in t.lower():
        stored += q(f'SELECT COUNT(*) AS n FROM "{t}"')[0]["n"]
for col in [r["name"] for r in q("PRAGMA table_info(orders)")]:
    if "refund" in col.lower():
        stored += q(f'SELECT COUNT(*) AS n FROM orders WHERE "{col}" IS NOT NULL')[0]["n"]
out["stored_rows"] = stored
missing = []
cands = ([999999, "999999"] if not isinstance(oid, str) else ["ord_doesnotexist000000", 999999])
for oval in cands:
    p = dict(ok[2] if ok else base, order_id=oval)
    code, b = call("POST", "/refunds", json=p)
    missing.append([code, b])
    if code != 422:
        break
out["missing"] = missing[-1]
'''


def refund_obj(body):
    for d in L.dicts_in(body):
        if any(k in d for k in ("reason", "refund_reason", "order_id")) or any("amount" in k for k in d):
            return d
    return body if isinstance(body, dict) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    res, err = L.run_app_script(w, SCRIPT)
    res = res or {}
    create, missing = res.get("create"), res.get("missing")
    obj = refund_obj(create[1]) if create else None
    rules, funcs = [], []

    # T1-R1: missing-order error body uses the NW error envelope
    if missing:
        ok = missing[0] == 404 and L.is_nw_error_body(missing[1])
        rules.append(L.item("T1-R1", ok, f"status={missing[0]} body={missing[1]}"))
    else:
        rules.append(L.item("T1-R1", *L.check_nw_error_format_static(w, base)))
    rules.append(L.item("T1-R2", *L.check_new_catalog_entry(w, base)))
    rules.append(L.item("T1-R3", *L.check_nwlog_in_new_code(w, base)))
    rules.append(L.item("T1-R4", *L.check_no_print_logging(w, base)))
    rules.append(L.item("T1-R5", *L.check_routes_toml(w, "POST", "/refunds")))
    # T1-R6: integer amount_minor + currency (response if available, else source)
    ok_s, d_s = L.check_money_minor(w, base)
    if obj is not None:
        ok = isinstance(obj.get("amount_minor"), int) and not isinstance(obj.get("amount_minor"), bool) \
            and isinstance(obj.get("currency"), str) and ok_s
        rules.append(L.item("T1-R6", ok, f"response amount_minor={obj.get('amount_minor')!r} currency={obj.get('currency')!r}; {d_s}"))
    else:
        rules.append(L.item("T1-R6", ok_s, d_s))
    # T1-R7: refund id is a prefixed public id generated with nwids
    ok_s, d_s = L.check_nwids_in_new_code(w, base)
    if obj is not None:
        rid = next((obj[k] for k in ("id", "refund_id", "public_id") if k in obj), None)
        ok = isinstance(rid, str) and bool(L.PUBLIC_ID.match(rid)) and ok_s
        rules.append(L.item("T1-R7", ok, f"response id={rid!r}; {d_s}"))
    else:
        rules.append(L.item("T1-R7", ok_s, d_s))
    rules.append(L.item("T1-R8", *L.check_changelog(w, base)))

    # Functional (convention-independent)
    if not res:
        funcs.append(L.item("T1-F1", False, f"App error: {err}"))
        funcs.append(L.item("T1-F2", False, f"App error: {err}"))
    else:
        ok = bool(create) and isinstance(create[1], (dict, list)) and bool(create[1]) and res.get("stored_rows", 0) > 0
        funcs.append(L.item("T1-F1", ok, f"create={create[:2] if create else res.get('create_attempts')} stored_rows={res.get('stored_rows')}"))
        ok = bool(missing) and 400 <= missing[0] < 500 and missing[0] != 422
        funcs.append(L.item("T1-F2", ok, f"missing order -> {missing}"))
    funcs.append(L.item("T1-F3", *L.run_pytest(w)))
    L.write_result(a.outdir, "T1", rules, funcs)


if __name__ == "__main__":
    main()
