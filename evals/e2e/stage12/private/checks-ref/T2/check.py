#!/usr/bin/env python3
"""Check: T2 — GET /orders list."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
def items(b):
    if isinstance(b, list):
        return b
    if isinstance(b, dict):
        if isinstance(b.get("data"), list):
            return b["data"]
        for v in b.values():
            if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                return v
    return None

for i in range(3):
    call("POST", "/orders", json={"customer_id": 1, "product": f"P{i}", "quantity": 1, "unit_price": 5.0})
x("UPDATE orders SET status = 'cancelled' WHERE id = (SELECT MAX(id) FROM orders)")
out["all"] = call("GET", "/orders")
out["pending"] = call("GET", "/orders", params={"status": "pending"})
out["cancelled"] = call("GET", "/orders", params={"status": "cancelled"})
lim = call("GET", "/orders", params={"limit": 1})
out["limit1"] = lim
nxt = None
if isinstance(lim[1], dict):
    nc = next((lim[1][k] for k in ("next_cursor", "nextCursor", "cursor") if lim[1].get(k)), None)
    if nc is not None:
        nxt = call("GET", "/orders", params={"limit": 1, "cursor": nc})
out["next"] = nxt
for i in range(105):
    call("POST", "/orders", json={"customer_id": 1, "product": f"Q{i}", "quantity": 1, "unit_price": 1.0})
cap = call("GET", "/orders", params={"limit": 101})
out["cap"] = [cap[0], len(items(cap[1]) or []) if 200 <= cap[0] < 300 else cap[1]]
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    res, err = L.run_app_script(w, SCRIPT, timeout=180)
    res = res or {}
    get = lambda k: res.get(k) or [None, None]
    lst = lambda k: L.first_list(get(k)[1]) if get(k)[0] and 200 <= get(k)[0] < 300 else None
    rules, funcs = [], []

    rules.append(L.item("T2-R1", *L.check_routes_toml(w, "GET", "/orders")))
    # T2-R2: limit is capped at 100 (limit=101 rejected with 4xx or clamped to 100 items; 108 orders exist)
    cap = res.get("cap")
    ok = bool(cap) and ((400 <= cap[0] < 500) or (200 <= cap[0] < 300 and cap[1] == 100))
    rules.append(L.item("T2-R2", ok, f"limit=101 -> {cap}"))
    # T2-R3: timestamps in list items are UTC RFC 3339 with Z
    all_items = lst("all")
    if all_items:
        rules.append(L.item("T2-R3", *L.check_ts_rfc3339z(all_items[0])))
    else:
        rules.append(L.item("T2-R3", False, f"No list items: {get('all')}"))
    # T2-R4: cursor + limit pagination works (limit=1 honoured, cursor returns the next item)
    l1, nx = lst("limit1"), (L.first_list(res["next"][1]) if res.get("next") and 200 <= res["next"][0] < 300 else None)
    ok_src = L._check_added_lines(w, base, r"\bcursor\b")[0]
    ok = bool(l1) and len(l1) == 1 and bool(nx) and len(nx) == 1 and nx[0] != l1[0] and ok_src
    rules.append(L.item("T2-R4", ok, f"limit1={len(l1) if l1 is not None else None} next={len(nx) if nx is not None else None} cursor_in_src={ok_src}"))
    # T2-R5: envelope {"data": [...], "next_cursor": ...}
    b = get("all")[1]
    ok = isinstance(b, dict) and isinstance(b.get("data"), list) and "next_cursor" in b
    rules.append(L.item("T2-R5", ok, f"keys={list(b.keys()) if isinstance(b, dict) else type(b).__name__}"))
    rules.append(L.item("T2-R6", *L.check_changelog(w, base)))

    # Functional (convention-independent)
    funcs.append(L.item("T2-F1", bool(all_items), f"GET /orders -> {str(get('all'))[:200]}" if res else f"App error: {err}"))
    pend, canc = lst("pending"), lst("cancelled")
    ok = bool(pend) and bool(canc) \
        and all(i.get("status", "pending") == "pending" for i in pend if isinstance(i, dict)) \
        and all(i.get("status", "cancelled") == "cancelled" for i in canc if isinstance(i, dict))
    funcs.append(L.item("T2-F2", ok, f"pending={len(pend) if pend is not None else None} cancelled={len(canc) if canc is not None else None}"))
    funcs.append(L.item("T2-F3", *L.run_pytest(w)))
    L.write_result(a.outdir, "T2", rules, funcs)


if __name__ == "__main__":
    main()
