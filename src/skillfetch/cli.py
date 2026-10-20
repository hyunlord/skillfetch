"""Command line: `skillfetch scan <dir> [--json] [--fail-on ...]`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from skillfetch.ingest.local_scan import fail_counts, render_report, scan_dir

FAIL_ON = ("conflict", "scan", "lint")


def _fail_on(value: str) -> list[str]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    unknown = [p for p in parts if p not in FAIL_ON]
    if unknown or not parts:
        raise argparse.ArgumentTypeError(
            f"invalid choice {', '.join(unknown) or value!r} (choose from {', '.join(FAIL_ON)})"
        )
    return parts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skillfetch", description="Zero-install skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser(
        "scan",
        help="lint, injection-scan and conflict-check a local skills directory",
    )
    scan.add_argument("dir", type=Path, help="a skills directory or a single skill folder")
    scan.add_argument("--json", action="store_true", help="print the report as JSON")
    scan.add_argument(
        "--fail-on",
        type=_fail_on,
        action="extend",
        default=[],
        metavar="{conflict,scan,lint}",
        help="exit 1 if the scan finds any of these (repeatable or comma-separated): "
        "conflict findings, injection-scan failures, lint failures. Warnings never fail.",
    )
    args = parser.parse_args(argv)

    if args.command == "scan":
        if not args.dir.is_dir():
            print(f"skillfetch: not a directory: {args.dir}", file=sys.stderr)
            return 2
        report = scan_dir(args.dir)
        text = report.model_dump_json(indent=2) + "\n" if args.json else render_report(report)
        sys.stdout.write(text)
        counts = fail_counts(report)
        triggered = [f"{counts[k]} {k}" for k in FAIL_ON if k in args.fail_on and counts[k]]
        if triggered:
            print(f"skillfetch: --fail-on: {', '.join(triggered)}", file=sys.stderr)
            return 1
        return 0
    return 2  # unreachable: argparse rejects unknown commands


if __name__ == "__main__":
    sys.exit(main())
