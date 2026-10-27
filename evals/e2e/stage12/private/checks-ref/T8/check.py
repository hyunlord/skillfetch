#!/usr/bin/env python3
"""Check: T8 — order cancel button with confirmation."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T8-R1", *L.check_web_t_usage(w, base)))
    rules.append(L.item("T8-R2", *L.check_web_locale_keys(w, base)))
    rules.append(L.item("T8-R3", *L.check_web_track_call(w, base)))
    rules.append(L.item("T8-R4", *L.check_web_event_declared(w, base)))
    ok_c, d_c = L.check_web_tokens_color(w, base)
    ok_s, d_s = L.check_web_tokens_spacing(w, base)
    rules.append(L.item("T8-R5", ok_c and ok_s, f"color: {d_c}; spacing: {d_s}"))

    # Functional (convention-independent): a cancel button, a confirmation step, and an API call
    code = "\n".join(t for f, t in L.added_text_by_file(w, base).items()
                     if f.endswith((".tsx", ".jsx", ".ts", ".js")) and not f.startswith("node_modules/"))
    has_button = bool(re.search(r"<button\b|<Button\b", code))
    has_cancel = bool(re.search(r"cancel", code, re.I))
    has_confirm = bool(re.search(r"\bconfirm\s*\(|modal|dialog|confirm", code, re.I))
    # checks-ref: also a call with TypeScript type arguments, fetchApi<T>(...) (stage12b DESIGN §4)
    has_api = bool(re.search(r"\bfetch(?:Api)?\s*(?:<[^()]*?>)?\s*\(|\baxios\b|\bapi\.\w+\s*(?:<[^()]*?>)?\s*\(", code))
    ok = has_button and has_cancel and has_confirm and has_api
    funcs.append(L.item("T8-F1", ok, f"button={has_button} cancel={has_cancel} confirm={has_confirm} api_call={has_api}"))
    funcs.append(L.item("T8-F2", *L.run_next_build(w)))
    L.write_result(a.outdir, "T8", rules, funcs)


if __name__ == "__main__":
    main()
