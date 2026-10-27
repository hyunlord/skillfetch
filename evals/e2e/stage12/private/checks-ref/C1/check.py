#!/usr/bin/env python3
"""Check: C1 — GET /customers/{id} (control, nw-b)."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

SCRIPT = r'''
import re
NAME, EMAIL = "Check Person", "check.person@example.com"
tables = [r["name"] for r in q("SELECT name FROM sqlite_master WHERE type='table'") if "customer" in r["name"].lower()]
row, source = None, None
for t in tables:
    rows = q(f'SELECT * FROM "{t}" LIMIT 1')
    if rows:
        row, source = rows[0], "app data"
        break
if row is None:
    code, b = call("POST", "/customers", json={"name": NAME, "email": EMAIL})
    if 200 <= code < 300:
        for t in tables:
            rows = q(f'SELECT * FROM "{t}" LIMIT 1')
            if rows:
                row, source = rows[0], "app data (POST /customers)"
                break
if row is None and tables:
    t = tables[0]
    cols = q(f'PRAGMA table_info("{t}")')
    vals = {}
    for cdef in cols:
        n, typ = cdef["name"], (cdef["type"] or "").upper()
        if cdef["pk"] or (cdef["dflt_value"] is not None):
            continue
        ln = n.lower()
        if "email" in ln:
            vals[n] = EMAIL
        elif ln in ("name", "full_name", "display_name") or ln.endswith("name"):
            vals[n] = NAME
        elif any(s in ln for s in ("_at", "date", "time", "joined", "signup", "registered", "created", "updated")):
            vals[n] = "2026-10-01T12:00:00+00:00"
            out["check_set_ts"] = True
        elif "INT" in typ:
            vals[n] = 1
        elif ln.endswith("id"):
            vals[n] = "cust_01jcheck0000000000000000"
        else:
            vals[n] = "x"
    x(f'INSERT INTO "{t}" ({", ".join(chr(34) + k + chr(34) for k in vals)}) VALUES ({", ".join("?" for _ in vals)})', tuple(vals.values()))
    row, source = q(f'SELECT * FROM "{t}" LIMIT 1')[0], "inserted by check"
out["source"], out["row"] = source, row
found = None
if row:
    known = [str(v) for k, v in row.items() if ("name" in k.lower() or "email" in k.lower()) and v]
    cands = [v for k, v in row.items() if v is not None and (k.lower() == "id" or k.lower().endswith(("id", "uid", "uuid")))]
    for v in cands:
        code, b = call("GET", f"/customers/{v}")
        if 200 <= code < 300 and any(s in json.dumps(b) for s in known):
            found = [code, b, v]
            break
out["found"] = found
miss = []
for v in ([999999, "cust_doesnotexist0000000000"] if not (found and isinstance(found[2], str)) else ["cust_doesnotexist0000000000", 999999]):
    code, b = call("GET", f"/customers/{v}")
    miss.append([code, b])
    if code != 422:
        break
out["missing"] = miss[-1]
'''


def customer_obj(body):
    for d in L.dicts_in(body):
        if any("email" in k for k in d) or any("name" in k for k in d):
            return d
    return body if isinstance(body, dict) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    res, err = L.run_app_script(w, SCRIPT)
    res = res or {}
    found, missing = res.get("found"), res.get("missing")
    obj = customer_obj(found[1]) if found else None
    rules, funcs = [], []

    if missing:
        ok = missing[0] == 404 and L.is_nw_error_body(missing[1])
        rules.append(L.item("C1-R1", ok, f"status={missing[0]} body={missing[1]}"))
    else:
        rules.append(L.item("C1-R1", *L.check_nw_error_format_static(w, base)))
    rules.append(L.item("C1-R2", *L.check_new_catalog_entry(w, base)))
    rules.append(L.item("C1-R3", *L.check_routes_toml(w, "GET", "/customers/{id}")))
    ok_s, d_s = L.check_nwids_in_new_code(w, base)
    if obj is not None:
        cid = next((obj[k] for k in ("id", "customer_id", "public_id") if k in obj), None)
        ok = isinstance(cid, str) and bool(L.PUBLIC_ID.match(cid)) and ok_s
        rules.append(L.item("C1-R4", ok, f"response id={cid!r}; {d_s}"))
    else:
        rules.append(L.item("C1-R4", False, f"No customer response; {d_s}"))
    if obj is not None:
        rules.append(L.item("C1-R5", *L.check_ts_at_suffix(obj)))
        if res.get("check_set_ts"):
            rules.append(L.item("C1-R6", None, "Undecidable: no app-created customer data; the check had to set the timestamp value"))
        else:
            rules.append(L.item("C1-R6", *L.check_ts_rfc3339z(obj)))
    else:
        rules.append(L.item("C1-R5", False, "No customer response"))
        rules.append(L.item("C1-R6", False, "No customer response"))

    # Functional (convention-independent)
    ok = bool(found) and obj is not None and any("email" in k for k in obj) and any("name" in k for k in obj) \
        and bool(L.timestamp_fields(obj))
    funcs.append(L.item("C1-F1", ok, f"source={res.get('source')} found={found}" if res else f"App error: {err}"))
    ok = bool(missing) and 400 <= missing[0] < 500 and missing[0] != 422
    funcs.append(L.item("C1-F2", ok, f"missing customer -> {missing}"))
    funcs.append(L.item("C1-F3", *L.run_pytest(w)))
    L.write_result(a.outdir, "C1", rules, funcs)


if __name__ == "__main__":
    main()
