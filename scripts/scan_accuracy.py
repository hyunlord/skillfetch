"""Scan accuracy (evals/scan-accuracy/README.md, numbers.md §30). No network.

uv run python scripts/scan_accuracy.py recall --split dev [--cases]
uv run python scripts/scan_accuracy.py recall --split eval        (totals only)
    The hand-written skills of recall/<split>.yaml, each written to a temporary folder and
    scanned. "Caught" = at least one failure or warning. The eval half prints totals only
    and refuses --cases unless --final is given (after the rules are settled); its file
    must still match recall/FROZEN-eval.sha256.

uv run python scripts/scan_accuracy.py independent --set DIR --rules vN --out FILE
    The independent set (written by another model without seeing the rules; README.md
    here): each case folder scanned as it is, references included. DIR must match
    independent/FROZEN.sha256. Run once per rules version, each under that version's code
    (scripts/scan_accuracy_versions.sh). Writes case id, label, caught and rule ids only.
    `independent --advice` counts by the install advice instead (each case folder through
    `scan`'s checks, no index, no model): flagged = CAUTION or NOT RECOMMENDED.

uv run python scripts/scan_accuracy.py independent-summary
    Markdown tables for numbers.md §30 from independent/results-vN.json, advice-vN.json and
    categories.yaml.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
    front = (
        f"---\nname: {case['id']}\n"
        f"description: A test skill for the scan ({case['category']}).\n---\n\n"
    )
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
    sub.add_parser("precision")
    sub.add_parser("independent-summary")
    ind = sub.add_parser("independent")
    ind.add_argument("--set", type=Path, required=True)
    ind.add_argument("--rules", required=True, help="the rules version being run, e.g. v8")
    ind.add_argument("--out", type=Path, required=True)
    ind.add_argument("--frozen", type=Path, default=HERE / "independent" / "FROZEN.sha256")
    ind.add_argument("--advice", action="store_true", help="count by the install advice")
    args = p.parse_args(argv)
    if args.cmd == "precision":
        print(json.dumps(precision(), indent=1))
        return 0
    if args.cmd == "independent-summary":
        print(independent_summary())
        return 0
    if args.cmd == "independent":
        independent(args.set, args.rules, args.out, args.frozen, args.advice)
        return 0
    if args.cmd == "recall":
        if args.split == "eval" and args.cases and not args.final:
            raise SystemExit("eval cases stay hidden until the rules are settled (--final)")
        recall(args.split, args.cases)
    return 0


LABELS = {"위험": "catch", "무해": "pass", "risky": "catch", "harmless": "pass"}


def _advice(case_dir: Path) -> tuple[bool, list[str]]:
    from skillfetch.ingest.local_scan import install_advice, scan_dir

    level, reasons = install_advice(scan_dir(case_dir))
    return level != "recommended", [level, *reasons]


def independent(folder: Path, version: str, out_path: Path, frozen: Path, advice: bool) -> dict:
    """Scan every case folder of the frozen independent set with the installed rules."""
    from skillfetch.ingest.injection import load_rules

    sums = folder / "SHA256SUMS"
    want = frozen.read_text().split()[0]
    if hashlib.sha256(sums.read_bytes()).hexdigest() != want:
        raise SystemExit(f"SHA256SUMS differs from {frozen.name}")
    for line in sums.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{name} differs from SHA256SUMS")
    loaded = load_rules()
    got = f"v{loaded.version}" if getattr(loaded, "version", None) is not None else version
    if got != version:
        raise SystemExit(f"installed rules are {got}, not {version}")
    rows = []
    for line in (folder / "cases.jsonl").open():
        case = json.loads(line)
        case_dir = folder / Path(case["path"]).parent
        if advice:
            caught, why = _advice(case_dir)
            row = {"caught": caught, "advice": why}
        else:
            result = scan_skill(case_dir)
            rules = sorted({h.rule_id for h in result.failures + result.warnings})
            row = {"caught": bool(rules), "rules": rules, "fails": bool(result.failures)}
        rows.append({"case": case_dir.name, "expect": LABELS[case["label"]], **row})
    risky = [r for r in rows if r["expect"] == "catch"]
    harmless = [r for r in rows if r["expect"] == "pass"]
    out = {
        "rules": version,
        "count": "advice" if advice else "warning",
        "risky_caught": sum(r["caught"] for r in risky),
        "risky": len(risky),
        "harmless_flagged": sum(r["caught"] for r in harmless),
        "harmless": len(harmless),
        "cases": rows,
    }
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(
        f"independent ({version}, {out['count']}): "
        f"risky caught {out['risky_caught']}/{out['risky']}, "
        f"harmless flagged {out['harmless_flagged']}/{out['harmless']}"
    )
    return out


VERSIONS = ("v6", "v7", "v8")


def independent_summary() -> str:
    here = HERE / "independent"
    load = lambda name: json.loads((here / name).read_text())  # noqa: E731
    warn = {v: load(f"results-{v}.json") for v in VERSIONS}
    adv = {v: load(f"advice-{v}.json") for v in VERSIONS}
    cats = yaml.safe_load((here / "categories.yaml").read_text())
    of = {f"case-{n + k:03d}": c for c, ns in cats.items() for n in ns for k in (0, 1)}
    lines = [
        "| count | v6 | v7 | v8 |",
        "|---|---:|---:|---:|",
    ]
    for name, res in (("advice (CAUTION or above)", adv), ("warning (fail or warn)", warn)):
        cells = [
            f"{res[v]['risky_caught']}/{res[v]['risky']} · "
            f"{res[v]['harmless_flagged']}/{res[v]['harmless']}"
            for v in VERSIONS
        ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += ["", "| category | risky | caught v6 | v7 | v8 | harmless flagged (v8) |"]
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cat in cats:
        row = []
        for v in VERSIONS:
            cases = [r for r in adv[v]["cases"] if of[r["case"]] == cat]
            row.append(sum(r["caught"] for r in cases if r["expect"] == "catch"))
        risky = sum(
            1 for r in adv["v8"]["cases"] if of[r["case"]] == cat and r["expect"] == "catch"
        )
        fp = sum(
            r["caught"]
            for r in adv["v8"]["cases"]
            if of[r["case"]] == cat and r["expect"] == "pass"
        )
        lines.append(f"| {cat} | {risky} | " + " | ".join(map(str, row)) + f" | {fp} |")
    lines += ["", "Caught or flagged, per case (rule ids, v8):"]
    for r in warn["v8"]["cases"]:
        if r["caught"]:
            lines.append(f"- {r['case']} ({r['expect']}, {of[r['case']]}): {', '.join(r['rules'])}")
    return "\n".join(lines)


def precision() -> dict:
    """Per stratum and half: items flagged under the sampled rules (before) and under the current
    rules (after: still flagged, plus the warnings the current rules add), and how many of them
    both judges called worth a look. Disagreements are counted apart, never as either."""
    pre = HERE / "precision"
    items = [json.loads(x) for x in (pre / "sample.jsonl").open()]
    items += [json.loads(x) for x in (pre / "new.jsonl").open()]
    now = {x["item_id"]: x["now"] for x in map(json.loads, (pre / "flagged-now.jsonl").open())}
    verdicts: dict[str, dict[int, str]] = {}
    for name in ("verdicts.jsonl", "verdicts-new.jsonl"):
        for x in map(json.loads, (pre / name).open()):
            verdicts.setdefault(x["item_id"], {})[x["judge"]] = x["verdict"]
    new_ids = {json.loads(x)["item_id"] for x in (pre / "new.jsonl").open()}
    out: dict = {}
    for it in items:
        v = verdicts.get(it["item_id"], {})
        agree = v.get(1) if v.get(1) == v.get(2) else "split"
        for when, flagged in (
            ("before", it["item_id"] not in new_ids),
            ("after", now.get(it["item_id"], it["item_id"] in new_ids)),
        ):
            if not flagged:
                continue
            c = (
                out.setdefault(it["stratum"], {})
                .setdefault(it["split"], {})
                .setdefault(when, {"n": 0, "worth_a_look": 0, "false_positive": 0, "split": 0})
            )
            c["n"] += 1
            c[agree] += 1
    return out


if __name__ == "__main__":
    sys.exit(main())
