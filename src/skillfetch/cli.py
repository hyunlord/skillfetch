"""Command line: `skillfetch scan|ingest|judge|obedience|sync|serve|eval|discover`."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from skillfetch.index import sync as index_sync
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index, IndexLoadError, tilde
from skillfetch.ingest import backends, credentials, extract
from skillfetch.ingest import discover as discover_mod
from skillfetch.ingest import judge as judge_mod
from skillfetch.ingest.build import build_index, render_summary, write_pairs
from skillfetch.ingest.build_report import write_reports
from skillfetch.ingest.calibrate import calibrate, render_calibration
from skillfetch.ingest.extract_cache import DEFAULT_CACHE_DIR, ExtractCache
from skillfetch.ingest.holdout import load_holdout, measure_holdout, render_holdout
from skillfetch.ingest.ingest import extract_dir, render_cost_log
from skillfetch.ingest.local_scan import (
    Lookup,
    fail_counts,
    render_markdown,
    render_report,
    scan_target,
)
from skillfetch.ingest.remote import RemoteError, checkout, is_remote, parse_github_url
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR, SnapshotError
from skillfetch.ingest.sources import load_sources
from skillfetch.ingest.upstream_licenses import GhCli
from skillfetch.resolve import relation

FAIL_ON = ("conflict", "scan", "lint")


def _fail_on(value: str) -> list[str]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    unknown = [p for p in parts if p not in FAIL_ON]
    if unknown or not parts:
        raise argparse.ArgumentTypeError(
            f"invalid choice {', '.join(unknown) or value!r} (choose from {', '.join(FAIL_ON)})"
        )
    return parts


def _scan(args: argparse.Namespace):
    """scan_target with the CLI's lookup (index, extract cache, optional extractor)."""
    if not is_remote(args.dir) and not Path(args.dir).is_dir():
        raise NotADirectoryError(args.dir)
    if is_remote(args.dir):
        parse_github_url(args.dir)  # refuse a bad URL before loading the index
    lookup, how = _scan_lookup(args)
    report = scan_target(
        args.dir, lookup, args.conflict_cap, parse=parse_github_url, checkout_fn=checkout
    )
    report.extraction = how
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skillfetch", description="Zero-install skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser(
        "scan",
        help="check skills before you install them: lint, injection scan, size, dated claims, "
        "license and contradictions, for a local folder or a GitHub repository",
    )
    scan.add_argument(
        "dir",
        help="a skills directory or a single skill folder, or a GitHub URL "
        "(https://github.com/<owner>/<repo>[/tree/<ref>[/<path>]]): shallow-cloned into a "
        "temporary folder, scanned and deleted; nothing is installed or run",
    )
    scan.add_argument("--json", action="store_true", help="print the report as JSON")
    scan.add_argument(
        "--markdown",
        action="store_true",
        help="print the report as a pull-request comment (Markdown; used by the GitHub Action)",
    )
    scan.add_argument(
        "--fail-on",
        type=_fail_on,
        action="extend",
        default=[],
        metavar="{conflict,scan,lint}",
        help="exit 1 if the scan finds any of these (repeatable or comma-separated): "
        "conflict findings, injection-scan failures, lint failures. Warnings never fail.",
    )
    scan.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="index to take constraints from for skills with the same content "
        "(default: %(default)s, from `skillfetch sync`; skipped if absent)",
    )
    scan.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    extract_how = scan.add_mutually_exclusive_group()
    extract_how.add_argument(
        "--claude-code",
        action="store_true",
        help="extract skills found in neither the index nor the cache with your Claude Code "
        "login: one isolated `claude -p` per skill (no tools, no MCP servers; no API key). "
        "Without it, or without the `claude` CLI, those skills skip the contradiction check",
    )
    extract_how.add_argument(
        "--with-api",
        action="store_true",
        help="extract skills found in neither the index nor the cache with --model "
        "(anthropic/openai/openrouter backends call an API and cost money)",
    )
    scan.add_argument(
        "--model",
        help="extraction key for the cache lookup and --with-api (default: the index's "
        f"extraction model, else {extract.DEFAULT_MODEL})",
    )
    scan.add_argument("--base-url", help="OpenAI-compatible server for openai/<model>")
    scan.add_argument(
        "--send-key",
        action="store_true",
        help="send the OpenAI key to --base-url (default: a placeholder key)",
    )
    scan.add_argument("--creds-file", type=Path, default=credentials.DEFAULT_CREDS_FILE)
    scan.add_argument("--jobs", type=int, default=4, help="parallel extraction requests")

    sync = sub.add_parser(
        "sync",
        help="download the published index from a GitHub release (or pack one for a release)",
    )
    sync.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="where the index goes (default: %(default)s)",
    )
    sync.add_argument("--repo", default=index_sync.DEFAULT_REPO, help="(default: %(default)s)")
    sync.add_argument("--tag", help="a release tag (default: the newest release with an index)")
    sync.add_argument(
        "--from",
        dest="tarball",
        type=Path,
        help="install this index tarball instead of downloading (checked against "
        "<file>.sha256 when present)",
    )
    sync.add_argument(
        "--pack",
        type=Path,
        metavar="INDEX_DIR",
        help="maintainers: write INDEX_DIR as a release tarball + .sha256 into --out",
    )
    sync.add_argument("--out", type=Path, default=Path("dist"), help="with --pack")

    disc = sub.add_parser(
        "discover",
        help="find candidate source repositories and pre-check them (no model; writes a "
        "report, never sources.yaml or an index)",
    )
    disc.add_argument(
        "--config", type=Path, default=discover_mod.DEFAULT_CONFIG, help="(default: %(default)s)"
    )
    disc.add_argument(
        "--sources",
        type=Path,
        default=Path("sources.yaml"),
        help="repositories listed here are left out (default: %(default)s)",
    )
    disc.add_argument(
        "--seen",
        type=Path,
        default=discover_mod.DEFAULT_OUT / discover_mod.SEEN_FILE,
        help="repositories evaluated before, one JSON object per line with `repo`; left out "
        "(default: %(default)s)",
    )
    disc.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="index to measure name and hash overlap against (default: %(default)s)",
    )
    disc.add_argument(
        "--out",
        type=Path,
        default=discover_mod.DEFAULT_OUT,
        help=f"writes {discover_mod.REPORT_FILE} and {discover_mod.ROWS_FILE} "
        "(default: %(default)s)",
    )
    disc.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="shallow clones of the checked candidates (default: %(default)s)",
    )
    disc.add_argument("--max-checks", type=int, help="override the config's max_checks")
    disc.add_argument(
        "--issue",
        type=int,
        help="also put the report on this GitHub issue (between the discover markers in its "
        "body if present, else as a comment), with the gh CLI",
    )

    serve = sub.add_parser("serve", help="run the MCP server over stdio")
    serve.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="index directory (default: %(default)s)",
    )
    serve.add_argument(
        "--auto-profile",
        action="store_true",
        help="#26 option, off by default: when search_skills gets no profile, use the "
        "profile of the server's working directory (the repository Claude Code started it "
        "in), so the router can skip profile_repo",
    )
    serve.add_argument(
        "--summary-chars",
        type=int,
        default=160,
        help="#26 option: cut each compact search summary to this many characters "
        "(default: %(default)s)",
    )
    serve.add_argument(
        "--vet",
        action="store_true",
        help="serve scan_skill and find_skills only (no routing), for the vet skill "
        "(assets/vet-skill); starts without an index, and uses it when there is one",
    )

    setup = sub.add_parser(
        "setup",
        help="set up Claude Code: the MCP server, the vet skill (check before install, find on "
        "request) and the index; --auto adds per-task routing. Shows every change and asks first",
    )
    where = setup.add_mutually_exclusive_group()
    where.add_argument(
        "--user", dest="scope", action="store_const", const="user", help="~/.claude (default)"
    )
    where.add_argument(
        "--project",
        dest="scope",
        action="store_const",
        const="project",
        help="this repository: .claude/skills and .mcp.json",
    )
    setup.set_defaults(scope="user")
    setup.add_argument(
        "--auto",
        action="store_true",
        help="also install the router skill and serve the routing tools (auto-apply; off by "
        "default, see numbers.md §26)",
    )
    setup.add_argument(
        "--client",
        choices=["claude-code", "codex", "cursor"],
        default="claude-code",
        help="the agent to set up (default: %(default)s); codex: ~/.codex/config.toml and "
        "~/.agents/skills, cursor: ~/.cursor/mcp.json (project scope: the same under .)",
    )
    setup.add_argument("--remove", action="store_true", help="undo what setup installed")
    setup.add_argument("-y", "--yes", action="store_true", help="do not ask before changing")
    setup.add_argument("--no-sync", action="store_true", help="do not sync the index")
    setup.add_argument(
        "--from",
        dest="source",
        default="git+https://github.com/hyunlord/skillfetch",
        help="where uvx installs skillfetch from for the MCP server (default: %(default)s)",
    )

    find = sub.add_parser(
        "find",
        help="search the index for a skill you want: top matches with summary, tier, size, "
        "license and install advice (no model, nothing installed)",
    )
    find.add_argument("want", help='what the skill should do, e.g. "write Playwright tests"')
    find.add_argument("-k", type=int, default=10, help="how many results (default: %(default)s)")
    find.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="index directory (default: %(default)s)",
    )
    find.add_argument("--json", action="store_true", help="print the results as JSON")

    ev = sub.add_parser("eval", help="offline benchmarks (no model calls)")
    ev_sub = ev.add_subparsers(dest="benchmark", required=True)
    ev_retrieval = ev_sub.add_parser(
        "retrieval",
        help="recall@10/@50 of search_skills on the 380-task set in evals/retrieval/",
    )
    ev_retrieval.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help="index directory (default: %(default)s)",
    )
    ev_retrieval.add_argument(
        "--evals",
        type=Path,
        default=None,
        help="tasks/oracle/queries directory (default: the repo's)",
    )
    ev_retrieval.add_argument(
        "--minilm",
        action="store_true",
        help="also all-MiniLM-L6-v2 alone and fused with BM25 (needs sentence-transformers)",
    )

    ingest = sub.add_parser(
        "ingest",
        help="lint, injection-scan and extract constraints for a skills directory",
    )
    ingest.add_argument(
        "dir",
        type=Path,
        nargs="?",
        help="skills directory to extract (with --calibrate: dir with skills/, expected.yaml); "
        "omit it and pass --sources to build an index",
    )
    ingest.add_argument("--sources", type=Path, help="build an index from this sources.yaml")
    ingest.add_argument(
        "--holdout",
        type=Path,
        help="with --sources: measure extraction + rules on this hand-labelled holdout "
        "instead of building an index; exit 1 if any extracted conflict is false",
    )
    ingest.add_argument(
        "--only", action="append", default=[], metavar="ID", help="build only these sources"
    )
    ingest.add_argument(
        "--sample",
        action="append",
        default=[],
        metavar="ID=N",
        help="take a seeded random sample of N skills from source ID",
    )
    ingest.add_argument("--seed", type=int, default=42, help="sampling seed (default: 42)")
    ingest.add_argument(
        "--upstream-licenses",
        action="store_true",
        help="read upstream repos' license files through the GitHub API (`gh`), cached in "
        "~/.skillfetch/upstream-licenses/",
    )
    ingest.add_argument("--out", type=Path, default=Path("data/index"), help="index directory")
    ingest.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="snapshots")
    ingest.add_argument(
        "--carry-verdicts",
        type=Path,
        metavar="INDEX",
        help="with --sources: keep this index's judge verdicts (pairs.jsonl) whose two skill "
        "ids are both in the new index; pairs without a verdict keep their warnings",
    )
    ingest.add_argument(
        "--with-api",
        action="store_true",
        help="extract skills not in the cache with --model: claude-code (default) queues the "
        "requests for Claude Code; openrouter/anthropic/openai backends call an API (costs money)",
    )
    ingest.add_argument(
        "--cached-only",
        action="store_true",
        help="with --calibrate: calibrate on the fixture skills in the extract cache and the "
        "pairs among them (no API); the others are listed",
    )
    ingest.add_argument(
        "--calibrate",
        action="store_true",
        help="compare extraction with the hand labels; exit 1 if any extracted conflict is "
        "false (hard gate), report the 0.85 informative-accuracy soft target",
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
        "--send-key",
        action="store_true",
        help="send the OpenAI key to --base-url (default: a placeholder key)",
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
    judge = sub.add_parser(
        "judge",
        help="LLM judge over the pairs the rules left open (needs_review, tension)",
    )
    target = judge.add_mutually_exclusive_group(required=True)
    target.add_argument("--calibrate", type=Path, metavar="FIXTURES", help="fixture dir")
    target.add_argument("--index", type=Path, help="a built index (with its -reports dir)")
    target.add_argument(
        "--import",
        dest="import_from",
        type=Path,
        metavar="JUDGMENTS",
        help="store an earlier judge report's judgments.jsonl as the pairs.jsonl of --into",
    )
    judge.add_argument("--into", type=Path, help="with --import: the index to store them in")
    judge.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="snapshots")
    judge.add_argument("--model", default=judge_mod.DEFAULT_JUDGE_MODEL)
    judge.add_argument(
        "--with-api",
        action="store_true",
        help="judge uncached pairs with --model (claude-code queues them; API backends cost money)",
    )
    judge.add_argument("--jobs", type=int, default=8)
    judge.add_argument("--creds-file", type=Path, default=credentials.DEFAULT_CREDS_FILE)
    judge.add_argument("--limit", type=int, help="judge only the first N pairs")

    obey = sub.add_parser(
        "obedience",
        help="obedience split test over the judge's conflict / ambiguous pairs",
    )
    obey.add_argument("--index", type=Path, required=True, help="a judged index")
    obey.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR, help="snapshots")
    obey.add_argument("--pairs", type=int, default=30, help="pairs to test (default 30)")
    obey.add_argument("--model", default=judge_mod.DEFAULT_JUDGE_MODEL, help="task writer")
    obey.add_argument(
        "--with-api",
        action="store_true",
        help="write uncached tasks with --model (claude-code queues them; API backends cost money)",
    )
    obey.add_argument("--creds-file", type=Path, default=credentials.DEFAULT_CREDS_FILE)
    obey.add_argument(
        "--run",
        type=Path,
        metavar="TASKS",
        help="run the trials for an approved tasks.json: each run is an isolated Claude Code "
        "session; classifications go to --model (claude-code: queued for Claude Code)",
    )
    obey.add_argument("--trials", type=int, default=5)
    obey.add_argument("--agent-model", default="sonnet", help="Claude Code model for the runs")
    obey.add_argument("--jobs", type=int, default=6)
    obey.add_argument(
        "--precedence",
        choices=("none", "ab", "ba", "resolved-a", "resolved-b", "strip-a", "strip-b"),
        action="append",
        help="with --run: none (default; no rule, alternating order); ab / ba (the "
        "load_skills precedence header on top, skills in that order); resolved-a / "
        "resolved-b (a Resolved rule conflicts block naming A or B the winner, skills "
        "A then B); strip-a / strip-b (no header or block; the loser's evidence lines "
        "replaced by an 'overridden by' comment, skills A then B); repeatable",
    )
    obey.add_argument(
        "--judgments",
        type=Path,
        help="judgments.jsonl with each pair's evidence lines, for resolved-a/b "
        "(default: <index>-reports/judgments.jsonl)",
    )

    for p in (scan, ingest):
        p.add_argument(
            "--conflict-cap",
            choices=relation.CAP_MODES,
            default=None,
            help="which rules without an object may conflict (constraints.md §3 row 14d): "
            "'all' reports every such pair as needs_review; 'vocabulary' lets a blanket rule "
            "on a vocabulary term conflict (more recall, less precision). Default: 'all' "
            "(scan: the index's manifest.conflict_cap when it reads an index)",
        )
    args = parser.parse_args(argv)

    if args.command == "scan":
        try:
            report = _scan(args)
        except RemoteError as exc:
            print(f"skillfetch: {exc}", file=sys.stderr)
            return 2
        except NotADirectoryError:
            print(f"skillfetch: not a directory: {args.dir}", file=sys.stderr)
            return 2
        except IndexLoadError as exc:
            print(f"skillfetch: {exc}", file=sys.stderr)
            return 2
        except ImportError:
            print("skillfetch: --with-api needs: pip install 'skillfetch[ingest]'", file=sys.stderr)
            return 2
        except (extract.MissingCredentials, ValueError) as exc:
            print(f"skillfetch: {exc}", file=sys.stderr)
            return 2
        if args.json:
            text = report.model_dump_json(indent=2) + "\n"
        elif args.markdown:
            text = render_markdown(report)
        else:
            text = render_report(report)
        sys.stdout.write(text)
        counts = fail_counts(report)
        triggered = [f"{counts[k]} {k}" for k in FAIL_ON if k in args.fail_on and counts[k]]
        if triggered:
            print(f"skillfetch: --fail-on: {', '.join(triggered)}", file=sys.stderr)
            return 1
        return 0
    if args.command == "ingest":
        return _ingest(args)
    if args.command == "judge":
        return _judge(args)
    if args.command == "obedience":
        return _obedience(args)
    if args.command == "serve":
        return _serve(args)
    if args.command == "find":
        return _find(args)
    if args.command == "setup":
        from skillfetch.setup import Setup
        from skillfetch.setup import main as setup_main

        return setup_main(
            Setup(
                scope=args.scope,
                auto=args.auto,
                client=args.client,
                source=args.source,
                sync=not args.no_sync,
            ),
            remove=args.remove,
            yes=args.yes,
        )
    if args.command == "sync":
        return _sync(args)
    if args.command == "eval":
        return _eval(args)
    if args.command == "discover":
        return _discover(args)
    return 2  # unreachable: argparse rejects unknown commands


def _eval(args: argparse.Namespace) -> int:
    from skillfetch import evals
    from skillfetch.mcp.session import Session

    folder = args.evals or evals.DEFAULT_EVALS
    if not (folder / "tasks.jsonl").is_file():
        print(f"skillfetch: eval: no tasks.jsonl in {folder}; pass --evals", file=sys.stderr)
        return 2
    try:
        session = Session(Index.load(args.index))
    except IndexLoadError as exc:
        print(f"skillfetch: eval: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(evals.retrieval(session, folder, minilm=args.minilm))
    except ImportError as exc:
        print(f"skillfetch: eval: --minilm needs sentence-transformers ({exc})", file=sys.stderr)
        return 2
    return 0


def _discover(args: argparse.Namespace) -> int:
    from datetime import date

    try:
        cfg = discover_mod.load_config(args.config)
        known = discover_mod.known_repos(load_sources(args.sources), args.seen)
    except (OSError, ValueError) as exc:
        print(f"skillfetch: discover: {exc}", file=sys.stderr)
        return 2
    if args.max_checks is not None:
        cfg.max_checks = args.max_checks
    run = discover_mod.discover(
        cfg,
        discover_mod.GhApi(),
        discover_mod.http_fetch,
        known,
        discover_mod.git_checkout(args.work_dir),
        discover_mod.IndexView.load(args.index),
        date.today(),
    )
    report, rows = discover_mod.write_outputs(run, args.out)
    checked = sum(r["status"] != "not_checked" for r in run.rows)
    print(f"{len(run.rows)} candidates, {checked} pre-checked: {report}, {rows}")
    code = 0
    if args.issue is not None:
        code = _post_issue(args.issue, report.read_text())
    if run.partial:  # the report (and the issue) went out; the exit code still says so
        print(f"skillfetch: discover: partial result: {'; '.join(run.partial)}", file=sys.stderr)
        return 1
    return code


def _post_issue(number: int, report: str) -> int:
    def gh(*cmd: str, stdin: str | None = None) -> str:
        proc = subprocess.run(["gh", *cmd], input=stdin, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip())
        return proc.stdout

    text = discover_mod.fit_issue(report)
    try:
        body = gh("issue", "view", str(number), "--json", "body", "-q", ".body")
        new = discover_mod.issue_body(body, text)
        if new is None:
            gh("issue", "comment", str(number), "--body-file", "-", stdin=text)
            print(f"commented on issue #{number}")
        else:
            gh("issue", "edit", str(number), "--body-file", "-", stdin=new)
            print(f"updated the report in issue #{number}")
    except (OSError, RuntimeError) as exc:
        print(f"skillfetch: discover: issue #{number}: {exc}", file=sys.stderr)
        return 1
    return 0


def _sync(args: argparse.Namespace) -> int:
    try:
        if args.pack is not None:
            tarball, checksum = index_sync.pack(args.pack, args.out)
            print(f"{tarball} ({tarball.stat().st_size} bytes)\n{checksum}")
            return 0
        # a token only raises the API rate limit; it is sent to api.github.com, never printed
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        result = index_sync.sync(args.index, args.repo, args.tag, args.tarball, token=token)
    except (index_sync.SyncError, IndexLoadError, OSError) as exc:
        print(f"skillfetch: sync: {exc}", file=sys.stderr)
        return 1
    m = result.index.manifest
    state = "installed" if result.changed else "already up to date"
    print(
        f"{state}: {tilde(result.index.root)} from {result.source} · {len(result.index.records)} "
        f"skills · built {m.get('built_at')} · extraction {m.get('extract_model')}"
    )
    return 0


def _scan_lookup(args: argparse.Namespace) -> tuple[Lookup, str | None]:
    """Index (if there is one), extract cache, and with --claude-code or --with-api an
    extractor; plus a line on how unindexed skills are handled (None: not asked)."""
    index = Index.load(args.index) if (args.index / "manifest.json").is_file() else None
    model = args.model or (index and index.manifest.get("extract_model")) or extract.DEFAULT_MODEL
    extractor, how = None, None
    if args.claude_code:
        import shutil

        from skillfetch.ingest.claude_code import ClaudeCliBackend

        spec = args.model or extract.DEFAULT_MODEL
        provider, name = backends.parse_model(spec)
        if provider != "claude-code":
            raise ValueError(f"--claude-code takes a claude-code/<model> --model, not {spec!r}")
        if shutil.which("claude") is None:
            how = "skipped: --claude-code needs the `claude` CLI on PATH"
        else:
            extractor = extract.Extractor(ClaudeCliBackend(name))
            model = extractor.model
            how = f"extracted with {model} (your Claude Code login, `claude -p`)"
    elif args.with_api:
        backend = backends.make_backend(
            args.model or extract.DEFAULT_MODEL,
            base_url=args.base_url,
            creds_file=args.creds_file,
            send_key=args.send_key,
        )
        extractor = extract.Extractor(backend)
        model = extractor.model
        how = f"extracted with {model} (--with-api)"
    return Lookup(index, ExtractCache(args.cache_dir), model, extractor, args.jobs), how


def _find(args: argparse.Namespace) -> int:
    from skillfetch.index.find import find_skills, render_find
    from skillfetch.index.search import Searcher

    try:
        index = Index.load(args.index)
    except IndexLoadError as exc:
        print(f"skillfetch: {exc}; run `skillfetch sync` first", file=sys.stderr)
        return 2
    found = find_skills(index, Searcher(index), args.want, args.k)
    if args.json:
        import json as _json

        print(_json.dumps(found, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(render_find(args.want, found))
    return 2 if "error" in found else 0


def _serve(args: argparse.Namespace) -> int:
    from skillfetch.mcp.server import serve, serve_vet

    if args.vet:
        serve_vet(args.index)
        return 0
    try:
        serve(
            args.index,
            profile_root=Path.cwd() if args.auto_profile else None,
            summary_chars=args.summary_chars,
        )
    except IndexLoadError as exc:
        print(f"skillfetch: {exc}", file=sys.stderr)
        return 2
    return 0


_SDK_NAMES = {"anthropic": "Anthropic", "openai": "OpenAI"}


def _api_error(exc: Exception) -> str | None:
    """Provider name if exc comes from a model SDK."""
    return _SDK_NAMES.get(type(exc).__module__.split(".")[0])


def _samples(specs: list[str]) -> dict[str, int]:
    out = {}
    for spec in specs:
        sid, _, n = spec.partition("=")
        if not sid or not n.isdigit():
            raise ValueError(f"--sample expects ID=N, got {spec!r}")
        out[sid] = int(n)
    return out


def _build(args: argparse.Namespace, key: str, extractor: extract.Extractor | None) -> int:
    sources = load_sources(args.sources)
    known = {s.id for s in sources}
    samples = _samples(args.sample)
    for sid in [*args.only, *samples]:
        if sid not in known:
            raise ValueError(f"unknown source id: {sid}")
    selected = [s for s in sources if not args.only or s.id in args.only]
    result = build_index(
        selected,
        out_dir=args.out,
        work_dir=args.work_dir,
        cache=ExtractCache(args.cache_dir),
        extractor=extractor,
        model=key,
        samples=samples,
        seed=args.seed,
        jobs=args.jobs,
        github=GhCli() if args.upstream_licenses else None,
        cap=args.conflict_cap or relation.DEFAULT_CAP,
        carry_verdicts=args.carry_verdicts,
    )
    print(render_summary(result))
    report, review = write_reports(result, args.out.with_name(args.out.name + "-reports"))
    print(f"reports: {report} · {review}")
    failed = result.manifest["counts"].get("api_errors", 0)
    if failed:
        print(
            f"skillfetch: {failed} skills hit API errors and were not extracted; rerun to "
            "retry them (finished extractions are cached)",
            file=sys.stderr,
        )
        return 1
    return 0


def _holdout(args: argparse.Namespace, key: str, extractor: extract.Extractor | None) -> int:
    result = measure_holdout(
        load_holdout(args.holdout),
        load_sources(args.sources),
        cache=ExtractCache(args.cache_dir),
        extractor=extractor,
        model=key,
        work_dir=args.work_dir,
        jobs=args.jobs,
        cap=args.conflict_cap or relation.DEFAULT_CAP,
    )
    print(render_holdout(result))
    if result.moved or (result.missing and extractor is None):
        print(
            "skillfetch: holdout incomplete: "
            + ("pinned content moved; " if result.moved else "")
            + (
                "some skills are not in the extract cache; rerun with --with-api"
                if result.missing and extractor is None
                else ""
            ),
            file=sys.stderr,
        )
        return 2
    return 0 if result.hard_pass else 1


class _NoAPI:
    """A judge backend for runs without --with-api: cache hits only."""

    def __init__(self, key: str):
        self.key = key

    def complete(self, *_args, **_kw):
        raise RuntimeError("not in the judge cache (run with --with-api)")


def _judge(args: argparse.Namespace) -> int:
    from skillfetch.ingest import judge_run

    if args.import_from is not None:
        if args.into is None:
            print("skillfetch: --import needs --into <index>", file=sys.stderr)
            return 2
        rows = judge_run.import_judgments(
            args.import_from, backends.backend_key(args.model), judge_mod.JUDGE_VERSION
        )
        path = write_pairs(args.into, rows)
        print(f"{len(rows)} verdicts by {backends.backend_key(args.model)} -> {path}")
        return 0
    if args.calibrate is not None:
        pairs = judge_run.fixture_pairs(args.calibrate)
    else:
        pairs = judge_run.index_pairs(args.index, args.work_dir)
    if args.limit:
        pairs = pairs[: args.limit]
    key = backends.backend_key(args.model)
    backend = (
        backends.make_backend(args.model, creds_file=args.creds_file)
        if args.with_api
        else _NoAPI(key)
    )
    judge = judge_mod.Judge(backend)
    outcomes = judge_mod.run_judge(
        [p.item for p in pairs],
        judge,
        args.jobs,
        progress=lambda n: print(f"  {n}/{len(pairs)} judged", file=sys.stderr),
    )
    cost = sum(o.record.cost_usd or 0 for o in outcomes if o.fresh and o.record)
    failed = [o for o in outcomes if o.record is None]
    summary = (
        f"{len(pairs)} pairs · {sum(o.fresh for o in outcomes)} judged now, "
        f"{sum(not o.fresh and o.record is not None for o in outcomes)} from cache, "
        f"{len(failed)} failed · cost ${cost:.4f} · judge {key}"
    )
    if args.calibrate is not None:
        rate, text = judge_run.calibration_report(pairs, outcomes)
        print(text)
        print(summary)
        ok = rate >= judge_mod.JUDGE_TARGET
        print(
            f"gate: agreement {rate:.3f} (target {judge_mod.JUDGE_TARGET}): "
            f"{'PASS' if ok else 'FAIL'}"
        )
        return 0 if ok and not failed else 1
    report_dir = args.index.with_name(args.index.name + "-reports")
    path = judge_run.write_judge_report(pairs, outcomes, report_dir, summary)
    stored = write_pairs(args.index, judge_run.pair_rows(pairs, outcomes))
    print(f"verdicts: {stored}")
    print(summary)
    print(f"report: {path}")
    return 0 if not failed else 1


def _obedience_run(args: argparse.Namespace) -> int:
    import json as _json
    from concurrent.futures import ThreadPoolExecutor

    from skillfetch.ingest import obedience
    from skillfetch.ingest.skillfile import read_skill

    tasks = [obedience.ObedienceTask.model_validate(t) for t in _json.loads(args.run.read_text())]
    records = {}
    for line in (args.index / "skills.jsonl").open():
        r = _json.loads(line)
        records[r["id"]] = r

    def doc_of(sid: str):
        r = records[sid]
        return read_skill(args.work_dir / r["source_id"] / r["commit"] / r["path"])

    def skill(sid: str) -> tuple[str, str]:
        return records[sid]["name"], "\n".join(doc_of(sid).body_lines).strip()

    stripped_log: dict[tuple[str, str], int] = {}  # (pair, cond) -> lines replaced

    def skills_for(task, cond: str) -> tuple[tuple[str, str], tuple[str, str]]:
        a, b = task.pair.split("|")
        sa, sb = skill(a), skill(b)
        if not cond.startswith("strip-"):
            return sa, sb
        winner = obedience.ranked_first(cond)
        loser_id = b if winner == "a" else a
        doc = doc_of(loser_id)
        c = conflicts[task.pair]
        body, done = obedience.strip_lines(
            doc.body_lines,
            doc.body_start,
            c.lines_b if winner == "a" else c.lines_a,
            (sa if winner == "a" else sb)[0],
        )
        stripped_log[(task.pair, cond)] = done
        return (sa, (sb[0], body)) if winner == "a" else ((sa[0], body), sb)

    agent = obedience.ClaudeSessionAgent(args.agent_model)
    judge = backends.make_backend(args.model, creds_file=args.creds_file)

    conditions = args.precedence or ["none"]
    resolved = [c for c in conditions if c.startswith("resolved-")]
    strip = [c for c in conditions if c.startswith("strip-")]
    if "none" in conditions and len(conditions) > 1:
        print("skillfetch: run --precedence none on its own", file=sys.stderr)
        return 2
    if (resolved and len(resolved) != len(conditions)) or (strip and len(strip) != len(conditions)):
        print("skillfetch: run resolved-a/b and strip-a/b each on their own", file=sys.stderr)
        return 2
    conflicts = {}
    if resolved or strip:
        judgments = (
            args.judgments or args.index.with_name(args.index.name + "-reports") / "judgments.jsonl"
        )
        conflicts = obedience.pair_conflicts(args.index, judgments, [t.pair for t in tasks])

    def run(cond: str) -> list[list]:
        def one(task):
            return obedience.run_trials(
                task,
                skills_for(task, cond),
                agent,
                judge,
                args.trials,
                precedence=cond,
                conflict=conflicts.get(task.pair),
            )

        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            return list(pool.map(one, tasks))

    by_cond = {cond: run(cond) for cond in conditions}
    out_dir = args.run.parent
    rows = [
        {
            "pair": t.pair,
            "precedence": cond,
            "run": tr.run,
            "order": tr.order,
            "followed": tr.followed,
            "reason": tr.reason,
            "output": tr.output,
        }
        for cond, results in by_cond.items()
        for t, trials in zip(tasks, results, strict=True)
        for tr in trials
    ]
    stem = (
        ""
        if conditions == ["none"]
        else "-resolved"
        if resolved
        else "-strip"
        if strip
        else "-precedence"
    )
    (out_dir / f"trials{stem}.jsonl").write_text(
        "".join(_json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    )
    pending = sum(r["followed"] is None for r in rows)
    if conditions == ["none"]:
        report = obedience.render_results(tasks, by_cond["none"])
    elif resolved:  # next to the precedence-header runs and the no-header runs (cached)
        report = obedience.render_precedence(tasks, by_cond, run("none"))
        report = report.replace(
            "# Obedience split test: precedence header", "# Obedience split test: resolved block"
        )
        report += (
            "\n\n## Next to the precedence header (experiment A)\n\n"
            + obedience.render_comparison(tasks, {c: run(c) for c in ("ab", "ba")}, by_cond)
            + "\n\n## The blocks\n\n"
            + "\n\n".join(
                f"`{t.pair}`\n\n```\n"
                + obedience.resolved_block(
                    conflicts[t.pair],
                    records[t.pair.split("|")[0]]["name"],
                    records[t.pair.split("|")[1]]["name"],
                    "a",
                )
                + "\n```"
                for t in tasks
            )
        )
    elif strip:  # next to the header and block runs and the no-header runs (cached)
        report = obedience.render_precedence(tasks, by_cond, run("none"))
        report = report.replace(
            "# Obedience split test: precedence header", "# Obedience split test: stripped lines"
        )
        header = {c: run(c) for c in ("ab", "ba")}
        block = {c: run(c) for c in ("resolved-a", "resolved-b")}
        report += (
            "\n\n## Header, block and stripped lines\n\n"
            + obedience.render_comparison(tasks, header, block, by_cond)
            + "\n\n## Lines replaced\n\n| pair (A ⟷ B) | strip-a: in B | strip-b: in A |\n"
            + "|---|---|---|\n"
            + "\n".join(
                "| {} ⟷ {} | {} | {} |".format(
                    *(x.split("/")[1].split("@")[0] for x in t.pair.split("|")),
                    stripped_log.get((t.pair, "strip-a"), "–"),
                    stripped_log.get((t.pair, "strip-b"), "–"),
                )
                for t in tasks
            )
        )
    else:  # compared with the no-header runs (cached)
        report = obedience.render_precedence(tasks, by_cond, run("none"))
    (out_dir / f"results{stem}.md").write_text(report + "\n")
    print(report.split("\n## ", 1)[0])
    print(f"{len(rows)} runs · {pending} classifications pending · {out_dir}/results{stem}.md")
    return 0 if not pending else 3


def _obedience(args: argparse.Namespace) -> int:
    """Writes the task list for review; the trials run only after it is approved."""
    import json as _json

    from skillfetch.ingest import judge_run, obedience

    if args.run is not None:
        return _obedience_run(args)
    report_dir = args.index.with_name(args.index.name + "-reports")
    rows = [_json.loads(line) for line in (report_dir / "judgments.jsonl").open()]
    selected = obedience.select_pairs(rows, args.pairs)
    wanted = {r["pair"] for r in selected}
    pairs = {p.key: p for p in judge_run.index_pairs(args.index, args.work_dir) if p.key in wanted}
    backend = (
        backends.make_backend(args.model, creds_file=args.creds_file)
        if args.with_api
        else _NoAPI(backends.backend_key(args.model))
    )
    tasks = obedience.generate_tasks(selected, pairs, backend)
    (report_dir / "obedience-tasks.json").write_text(
        _json.dumps([t.model_dump() for t in tasks], indent=2, ensure_ascii=False)
    )
    path = report_dir / "obedience-tasks.md"
    path.write_text(obedience.render_tasks(tasks) + "\n")
    cost = sum(t.cost_usd or 0 for t in tasks)
    print(f"{len(tasks)} tasks · cost ${cost:.4f} · {path}")
    return 0


def _ingest(args: argparse.Namespace) -> int:
    if (args.dir is None) == (args.sources is None):
        print("skillfetch: give either a directory or --sources", file=sys.stderr)
        return 2
    if args.holdout is not None and args.sources is None:
        print("skillfetch: --holdout needs --sources", file=sys.stderr)
        return 2
    if args.dir is not None:
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
                args.model,
                base_url=args.base_url,
                creds_file=args.creds_file,
                send_key=args.send_key,
            )
            extractor = extract.Extractor(backend)
        if args.holdout is not None:
            return _holdout(args, key, extractor)
        if args.sources is not None:
            return _build(args, key, extractor)
        outcomes = extract_dir(skills_dir, cache, extractor, model=key, jobs=args.jobs)
    except ImportError:
        print("skillfetch: --with-api needs: pip install 'skillfetch[ingest]'", file=sys.stderr)
        return 2
    except (extract.MissingCredentials, ValueError) as exc:
        print(f"skillfetch: {exc}", file=sys.stderr)
        return 2
    except SnapshotError as exc:
        print(f"skillfetch: snapshot failed: {exc}", file=sys.stderr)
        return 1
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
    if missing and not args.cached_only:
        print(
            f"skillfetch: cannot calibrate: {len(missing)} fixture skills are not in the "
            "extract cache; rerun with --with-api, or --cached-only to calibrate the others",
            file=sys.stderr,
        )
        return 2
    if missing:
        print(f"\nnot in the cache, left out of this calibration: {', '.join(missing)}")
    cal = calibrate(
        args.dir,
        {o.skill_id: o.record for o in outcomes if o.record is not None},
        args.conflict_cap or relation.DEFAULT_CAP,
        cached_only=args.cached_only,
    )
    print()
    print(render_calibration(cal))
    return 0 if cal.passed else 1


if __name__ == "__main__":
    sys.exit(main())
