"""Command line: `skillfetch scan <dir> [--json]`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from skillfetch.ingest.local_scan import render_report, scan_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skillfetch", description="Zero-install skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser(
        "scan",
        help="lint, injection-scan and conflict-check a local skills directory",
    )
    scan.add_argument("dir", type=Path, help="a skills directory or a single skill folder")
    scan.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    if args.command == "scan":
        if not args.dir.is_dir():
            print(f"skillfetch: not a directory: {args.dir}", file=sys.stderr)
            return 2
        report = scan_dir(args.dir)
        sys.stdout.write(
            report.model_dump_json(indent=2) + "\n" if args.json else render_report(report)
        )
        return 0
    return 2  # unreachable: argparse rejects unknown commands


if __name__ == "__main__":
    sys.exit(main())
