#!/usr/bin/env python3
"""Check: T6 — pricing tests."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _lib as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree"); ap.add_argument("outdir"); ap.add_argument("--base", required=True)
    a = ap.parse_args()
    w, base = a.worktree, a.base
    rules, funcs = [], []
    rules.append(L.item("T6-R1", *L.check_test_filename(w, base)))
    rules.append(L.item("T6-R2", *L.check_nw_factory_used(w, base)))
    rules.append(L.item("T6-R3", *L.check_contract_marker(w, base)))

    # Functional (convention-independent)
    tests = [f for f in L.get_changed_files(w, base) if f.startswith("tests/") and f.endswith(".py")]
    text = "\n".join(L.read_file(w, f) or "" for f in tests)
    has_calc = bool(re.search(r"\bcalculate_total\s*\(", text))
    has_tax = bool(re.search(r"\bapply_tax\s*\(", text))
    funcs.append(L.item("T6-F1", has_calc, "calculate_total called in new tests" if has_calc else "Missing"))
    funcs.append(L.item("T6-F2", has_tax, "apply_tax called in new tests" if has_tax else "Missing"))
    funcs.append(L.item("T6-F3", *L.run_pytest(w)))
    L.write_result(a.outdir, "T6", rules, funcs)


if __name__ == "__main__":
    main()
