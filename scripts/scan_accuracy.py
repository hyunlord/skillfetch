"""Scan accuracy (evals/scan-accuracy/README.md, numbers.md §30). No network.

uv run python scripts/scan_accuracy.py recall --split dev [--cases]
uv run python scripts/scan_accuracy.py recall --split eval        (totals only)
    The hand-written skills of recall/<split>.yaml, each written to a temporary folder and
    scanned. "Caught" = at least one failure or warning. The eval half prints totals only
    and refuses --cases unless --final is given (after the rules are settled); its file
    must still match recall/FROZEN-eval.sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

import yaml

from skillfetch.ingest.injection import scan_skill

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "evals" / "scan-accuracy"


def load_cases(split: str) -> list[dict]:
    path = HERE / "recall" / f"{split}.yaml"
    if split == "eval":
        want = (HERE / "recall" / "FROZEN-eval.sha256").read_text().split()[0]
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f"eval.yaml changed since it was frozen ({got[:12]} != {want[:12]})")
    return yaml.safe_load(path.read_text())


def scan_case(case: dict, tmp: Path) -> tuple[bool, list[str]]:
    folder = tmp / case["id"]
    folder.mkdir()
    front = f"---\nname: {case['id']}\ndescription: A test skill for the scan ({case['category']}).\n---\n\n"
    (folder / "SKILL.md").write_text(front + case["body"])
    result = scan_skill(folder)
    rules = sorted({h.rule_id for h in result.failures + result.warnings})
    return bool(rules), rules


def recall(split: str, show: bool) -> dict:
    cases = load_cases(split)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in cases:
            caught, rules = scan_case(c, Path(tmp))
            rows.append({**c, "caught": caught, "rules": rules})
    risky = [r for r in rows if r["expect"] == "catch"]
    harmless = [r for r in rows if r["expect"] == "pass"]
    out = {
        "split": split,
        "risky_caught": sum(r["caught"] for r in risky),
        "risky": len(risky),
        "harmless_flagged": sum(r["caught"] for r in harmless),
        "harmless": len(harmless),
    }
    print(
        f"{split}: risky caught {out['risky_caught']}/{out['risky']}, "
        f"harmless flagged {out['harmless_flagged']}/{out['harmless']}"
    )
    if show:
        for r in rows:
            ok = r["caught"] == (r["expect"] == "catch")
            print(
                f"  {'ok ' if ok else 'BAD'} {r['id']:<14} {r['expect']:<5} {','.join(r['rules'])}"
            )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recall")
    r.add_argument("--split", choices=["dev", "eval"], required=True)
    r.add_argument("--cases", action="store_true", help="print each case (dev; eval with --final)")
    r.add_argument(
        "--final", action="store_true", help="the rules are settled: eval cases may show"
    )
    args = p.parse_args(argv)
    if args.cmd == "recall":
        if args.split == "eval" and args.cases and not args.final:
            raise SystemExit("eval cases stay hidden until the rules are settled (--final)")
        recall(args.split, args.cases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
