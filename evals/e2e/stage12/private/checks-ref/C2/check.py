#!/usr/bin/env python3
"""Check: C2 — settings page (control, nw-b)."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L

PAGES = ("pages/settings.tsx", "pages/settings/index.tsx", "pages/settings.jsx", "pages/settings/index.jsx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("C2-R1", *L.check_web_t_usage(w, base)))
    rules.append(L.item("C2-R2", *L.check_web_locale_keys(w, base)))
    rules.append(L.item("C2-R3", *L.check_web_tokens_color(w, base)))
    rules.append(L.item("C2-R4", *L.check_web_tokens_spacing(w, base)))

    # Functional (convention-independent): page exists with a language control and a notification control
    page = next((p for p in PAGES if L.file_exists(w, p)), None)
    code = "\n".join(t for f, t in L.added_text_by_file(w, base).items() if f.endswith((".tsx", ".jsx", ".ts", ".js")))
    has_lang = bool(re.search(r"lang|locale", code, re.I))
    has_notif = bool(re.search(r"notif", code, re.I))
    ok = bool(page) and bool(re.search(r"export\s+default", L.read_file(w, page) or "")) and has_lang and has_notif
    funcs.append(L.item("C2-F1", ok, f"settings page={page} language={has_lang} notifications={has_notif}"))
    funcs.append(L.item("C2-F2", *L.run_next_build(w)))
    L.write_result(a.outdir, "C2", rules, funcs)


if __name__ == "__main__":
    main()
