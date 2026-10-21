"""Command line: `skillfetch scan|ingest`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from skillfetch.ingest import backends, credentials, extract
from skillfetch.ingest.calibrate import calibrate, render_calibration
from skillfetch.ingest.extract_cache import DEFAULT_CACHE_DIR, ExtractCache
from skillfetch.ingest.ingest import extract_dir, render_cost_log
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

    ingest = sub.add_parser(
        "ingest",
        help="lint, injection-scan and extract constraints for a skills directory",
    )
    ingest.add_argument(
        "dir",
        type=Path,
        help="skills directory (with --calibrate: dir with skills/, expected.yaml)",
    )
    ingest.add_argument(
        "--with-api",
        action="store_true",
        help="call the model API for skills not in the extract cache (costs money)",
    )
    ingest.add_argument(
        "--calibrate",
        action="store_true",
        help="compare extraction with the hand labels; exit 1 below the 0.90 gate",
    )
    ingest.add_argument(
        "--model",
        default=extract.DEFAULT_MODEL,
        help="provider/model, e.g. anthropic/claude-sonnet-5 (default: %(default)s)",
    )
    ingest.add_argument(
        "--base-url",
        help="OpenAI-compatible server for openai/<model> (vLLM, Ollama, ...); "
        "for OpenRouter use --model openrouter/<vendor>/<model>",
    )
    ingest.add_argument(
        "--creds-file",
        type=Path,
        default=credentials.DEFAULT_CREDS_FILE,
        help="dotenv file holding OPEN_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY "
        "(default: %(default)s)",
    )
    ingest.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    ingest.add_argument("--jobs", type=int, default=4, help="parallel API requests")
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
    if args.command == "ingest":
        return _ingest(args)
    return 2  # unreachable: argparse rejects unknown commands


_SDK_NAMES = {"anthropic": "Anthropic", "openai": "OpenAI"}


def _api_error(exc: Exception) -> str | None:
    """Provider name if exc comes from a model SDK."""
    return _SDK_NAMES.get(type(exc).__module__.split(".")[0])


def _ingest(args: argparse.Namespace) -> int:
    skills_dir = args.dir / "skills" if args.calibrate else args.dir
    if not skills_dir.is_dir():
        print(f"skillfetch: not a directory: {skills_dir}", file=sys.stderr)
        return 2
    cache = ExtractCache(args.cache_dir)
    try:
        key = backends.backend_key(args.model, args.base_url)
    except ValueError as exc:
        print(f"skillfetch: {exc}", file=sys.stderr)
        return 2
    try:
        extractor = None
        if args.with_api:
            backend = backends.make_backend(
                args.model, base_url=args.base_url, creds_file=args.creds_file
            )
            extractor = extract.Extractor(backend)
        outcomes = extract_dir(skills_dir, cache, extractor, model=key, jobs=args.jobs)
    except ImportError:
        print("skillfetch: --with-api needs: pip install 'skillfetch[ingest]'", file=sys.stderr)
        return 2
    except (extract.MissingCredentials, ValueError) as exc:
        print(f"skillfetch: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        sdk = _api_error(exc)
        if sdk is None:
            raise
        hint = ""
        if type(exc).__name__ in ("AuthenticationError", "AnthropicError"):
            hint = {
                "Anthropic": " (set ANTHROPIC_API_KEY, or run `ant auth login`)",
                "OpenAI": f" (check OPENAI_API_KEY or OPEN_API_KEY in {args.creds_file})",
            }[sdk]
        # providers echo (masked) keys in auth errors: never print key material
        message = credentials.redact(str(exc), *credentials.known_keys(args.creds_file))
        print(f"skillfetch: {sdk} API error: {message}{hint}", file=sys.stderr)
        print("skillfetch: finished extractions are cached; rerun to resume", file=sys.stderr)
        return 1
    print(render_cost_log(outcomes))
    if not args.calibrate:
        return 0
    missing = [o.skill_id for o in outcomes if o.record is None]
    if missing:
        print(
            f"skillfetch: cannot calibrate: {len(missing)} fixture skills are not in the "
            "extract cache; rerun with --with-api",
            file=sys.stderr,
        )
        return 2
    cal = calibrate(args.dir, {o.skill_id: o.record for o in outcomes})
    print()
    print(render_calibration(cal))
    return 0 if cal.passed else 1


if __name__ == "__main__":
    sys.exit(main())
