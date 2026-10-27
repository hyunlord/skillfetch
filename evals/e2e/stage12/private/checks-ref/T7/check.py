#!/usr/bin/env python3
"""Check: T7 — order history page."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

PAGES = ("pages/orders.tsx", "pages/orders/index.tsx", "pages/orders.jsx", "pages/orders/index.jsx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T7-R1", *L.check_web_t_usage(w, base)))
    rules.append(L.item("T7-R2", *L.check_web_locale_keys(w, base)))
    rules.append(L.item("T7-R3", *L.check_web_tokens_color(w, base)))
    rules.append(L.item("T7-R4", *L.check_web_tokens_spacing(w, base)))
    rules.append(L.item("T7-R5", *L.check_changelog(w, base)))

    # Functional (convention-independent)
    page = next((p for p in PAGES if L.file_exists(w, p)), None)
    ok = bool(page) and bool(re.search(r"export\s+default", L.read_file(w, page) or ""))
    funcs.append(L.item("T7-F1", ok, f"orders page={page}"))
    funcs.append(L.item("T7-F2", *L.run_next_build(w)))
    L.write_result(a.outdir, "T7", rules, funcs)


if __name__ == "__main__":
    main()
