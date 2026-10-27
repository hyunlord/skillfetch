"""The scan rules of `skillfetch scan` over every skill of an index (no model calls).

  uv run python scripts/index_scan.py rows [--index DIR] [--work DIR] [--out ROWS]
      Reads each record's folder from the source snapshots (`skillfetch ingest` work dir,
      <work>/<source_id>/<commit>/<path>) and writes one derived row per skill: flags and
      counts only, no skill text.
  uv run python scripts/index_scan.py report [--rows ROWS]
      The rates of numbers.md §25, for all indexed skills and for canonical ones only.

Per skill: lint (lint_skill), the injection scan (scan_skill, current rules), size
(skill_size), dated lines (dated_lines), scripts (the scan's has_scripts) and license as
`skillfetch scan` decides it on the snapshot (index-format.md §5.1): the skill folder's own
LICENSE file or frontmatter (`no_own_license` when neither), else the nearest license file up
to the repository root outside an aggregator (`no_license` when that finds none either). The
scan's last step, an indexed copy's license, is left out: every skill here is in the index.
Advice per skill uses §5.1 (safety and quality only; the license is not part of it) without
the pair checks (CONFLICT, REDUNDANT), which need a set of skills.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR
from skillfetch.ingest.injection import load_rules, scan_skill
from skillfetch.ingest.licenses import skill_license
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.repo_license import RepoLicenses
from skillfetch.ingest.skill_checks import dated_lines, skill_size
from skillfetch.ingest.skillfile import read_skill
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR

ROOT = Path(__file__).resolve().parent.parent
ROWS = ROOT / "evals" / "index-scan" / "rows.jsonl"


def skill_row(record: dict, folder: Path, repo: RepoLicenses) -> dict:
    lint = lint_skill(folder)
    scan = scan_skill(folder)
    size = skill_size(folder)
    dated = dated_lines(folder)
    warn_rules = sorted({h.rule_id for h in scan.warnings})
    frontmatter = read_skill(folder).frontmatter if lint.ok else None
    own = skill_license(folder, frontmatter, "per-skill")
    inherited = repo.inherited(folder, frontmatter) if own.origin == "none" else None
    if not lint.ok or not scan.ok:
        advice = "not_recommended"
    elif scan.warnings or size.warnings or scan.has_scripts:
        advice = "caution"
    else:
        advice = "recommended"
    return {
        "id": record["id"],
        "source_id": record["source_id"],
        "canonical": record.get("canonical_id", record["id"]) == record["id"],
        "tier": record.get("tier"),
        "lint_failed": not lint.ok,
        "scan_failed": not scan.ok,
        "fail_rules": sorted({h.rule_id for h in scan.failures}),
        "scan_warning": bool(scan.warnings),
        "warn_rules": warn_rules,
        "remote_instructions": "network.remote-instructions" in warn_rules,
        "size_warning": bool(size.warnings),
        "skill_md_tokens": size.skill_md_tokens,
        "files": size.files,
        "total_bytes": size.total_bytes,
        "over_tokens": any(w.startswith("SKILL.md") for w in size.warnings),
        "over_files": any(w.endswith(" files (over 20)") for w in size.warnings),
        "over_bytes": any(" MB in total" in w for w in size.warnings),
        "has_scripts": scan.has_scripts,
        "no_own_license": own.origin == "none",
        "no_license": own.origin == "none" and inherited is None,
        "license": own.license if inherited is None else inherited[1],
        "license_from_repo": inherited[0] if inherited else None,
        "aggregator": repo.aggregator,
        "dated": bool(dated),
        "dated_lines": len(dated),
        "advice": advice,
    }


def rows(index: Path, work: Path, out: Path) -> None:
    records = [json.loads(line) for line in (index / "skills.jsonl").open()]
    result, missing = [], 0
    repos: dict[Path, RepoLicenses] = {}
    for r in records:
        root = work / r["source_id"] / r["commit"]
        folder = root / r["path"]
        if not (folder / "SKILL.md").is_file():
            missing += 1
            continue
        repo = repos.setdefault(root, RepoLicenses(root))
        result.append(skill_row(r, folder, repo))
    out.parent.mkdir(parents=True, exist_ok=True)
    # compact rows: false flags, empty lists and nulls are left out (read as false / empty)
    out.write_text(
        "".join(
            json.dumps(
                {k: v for k, v in x.items() if v not in (False, [], None)}, separators=(",", ":")
            )
            + "\n"
            for x in result
        )
    )
    manifest = json.loads((index / "manifest.json").read_text())
    meta = {
        "index_built_at": manifest.get("built_at"),
        "records": len(records),
        "rows": len(result),
        "missing_snapshot": missing,
        "scan_rules_version": load_rules().version,
        # skills the build rejected before indexing (manifest counts, the rules of that build)
        "rejected_at_build": {
            k: manifest.get("counts", {}).get(k, 0) for k in ("lint_failed", "scan_failed")
        },
        "build_scan_rules_version": manifest.get("scan_rules_version"),
    }
    (out.parent / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


FLAGS = (
    ("scan_failed", "fails the injection scan"),
    ("scan_warning", "injection-scan warning (any)"),
    ("remote_instructions", "  of which: remote instructions (network.remote-instructions)"),
    ("size_warning", "size warning (any)"),
    ("over_tokens", "  SKILL.md over 8,000 tokens"),
    ("over_files", "  more than 20 files"),
    ("over_bytes", "  more than 1 MB"),
    ("has_scripts", "bundles scripts"),
    ("no_own_license", "no license in the skill itself (folder LICENSE or frontmatter)"),
    ("no_license", "no license after the repo-root rule"),
    ("dated", "states a year or version (DATED)"),
    ("lint_failed", "fails lint"),
)


def _pct(n: int, d: int) -> str:
    return f"{n:,} ({100 * n / d:.1f}%)"


def report(rows_path: Path) -> None:
    keys = (
        "scan_failed",
        "scan_warning",
        "remote_instructions",
        "size_warning",
        "over_tokens",
        "over_files",
        "over_bytes",
        "has_scripts",
        "no_own_license",
        "no_license",
        "dated",
        "lint_failed",
        "canonical",
        "aggregator",
    )
    data = []
    for line in rows_path.open():
        x = json.loads(line)
        data.append(
            {
                **{k: False for k in keys},
                "warn_rules": [],
                "fail_rules": [],
                "license_from_repo": None,
                "license": "unknown",
                **x,
            }
        )
    groups = {"all indexed": data, "canonical": [x for x in data if x["canonical"]]}
    n = {k: len(v) for k, v in groups.items()}
    print(f"| check | all indexed (n={n['all indexed']:,}) | canonical (n={n['canonical']:,}) |")
    print("|---|---:|---:|")
    for key, label in FLAGS:
        cells = [_pct(sum(x[key] for x in g), len(g)) for g in groups.values()]
        print(f"| {label} | {cells[0]} | {cells[1]} |")
    print()
    print("| advice (per skill) | all indexed | canonical |")
    print("|---|---:|---:|")
    for level in ("recommended", "caution", "not_recommended"):
        cells = [_pct(sum(x["advice"] == level for x in g), len(g)) for g in groups.values()]
        print(f"| {level.replace('_', ' ')} | {cells[0]} | {cells[1]} |")
    print()
    for name, g in groups.items():
        inherited = Counter(x["license"] for x in g if x["license_from_repo"])
        print(f"{name}: licenses taken from the repository {dict(inherited.most_common())}")
        lic = Counter(x["license"] for x in g)
        print(f"{name}: licenses after the rule {dict(lic.most_common())}")
        warn = Counter(r for x in g for r in x["warn_rules"])
        fail = Counter(r for x in g for r in x["fail_rules"])
        print(f"{name}: warning rules {dict(warn.most_common())}; failure rules {dict(fail)}")
        dated = sorted(x["dated_lines"] for x in g if x["dated"])
        if dated:
            print(
                f"  dated lines per dated skill: median {dated[len(dated) // 2]}, max {dated[-1]}"
            )
        print(
            "  by source (skills, no own license, no license after the rule, aggregator): "
            + ", ".join(
                f"{s} {len(xs)}/{sum(x['no_own_license'] for x in xs)}/"
                f"{sum(x['no_license'] for x in xs)}/{xs[0]['aggregator']}"
                for s in sorted({x["source_id"] for x in g})
                if (xs := [x for x in g if x["source_id"] == s])
            )
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rows")
    r.add_argument("--index", type=Path, default=DEFAULT_INDEX_DIR)
    r.add_argument("--work", type=Path, default=DEFAULT_WORK_DIR)
    r.add_argument("--out", type=Path, default=ROWS)
    s = sub.add_parser("report")
    s.add_argument("--rows", type=Path, default=ROWS)
    args = p.parse_args(argv)
    if args.cmd == "rows":
        rows(args.index, args.work, args.out)
    else:
        report(args.rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
