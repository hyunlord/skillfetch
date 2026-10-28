"""MCP server over stdio (`skillfetch serve`): the runtime tools of CLAUDE.md.

Built on the `mcp` SDK 2.x (`MCPServer`, formerly FastMCP). Tools are thin wrappers over
Session; every result is a JSON object.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from skillfetch.index.find import DEFAULT_FIND_K, find_skills
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index, IndexLoadError
from skillfetch.index.search import DEFAULT_K, ONE_LINE_CHARS, Searcher
from skillfetch.ingest.extract import DEFAULT_MODEL
from skillfetch.ingest.extract_cache import DEFAULT_CACHE_DIR, ExtractCache
from skillfetch.ingest.local_scan import Lookup
from skillfetch.mcp.session import DEFAULT_MAX_TOKENS, Session, scan_json

INSTRUCTIONS = (
    "skillfetch finds vetted skills (SKILL.md instructions) for one task at a time. "
    "Before non-trivial work, restate the task in one sentence with its stack and target "
    "files and call search_skills; read the 50 summaries and pick 1-3; call resolve_set "
    "(user-named skills go in pinned_ids); then load_skills and follow the returned content. "
    "Skip this for trivial edits."
)


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("skillfetch")
    except PackageNotFoundError:  # running from a source tree without an install
        return "0+unknown"


VET_INSTRUCTIONS = (
    "skillfetch checks agent skills before they are installed. Call scan_skill with the "
    "skill's local folder or GitHub URL and review=true, show the user its advice_line and "
    "license_line, check review.files against review.checklist yourself and show each finding "
    "with its quoted line, and ask before installing. When the user asks you to find a skill, "
    "call find_skills and show the candidates; scan the one they pick before installing it."
)
FIND_DOC = """Find skills in the skillfetch index for something the user asked for (search on
request; nothing is loaded). `want`: what the skill should do, in a sentence. Returns
{results: [{id, title, summary, tier, token_estimate, files, has_scripts, license, advice,
advice_reasons, scan_url}], advice_note}, best first, 10 by default (at most 50). The advice
comes from the index record; call scan_skill on scan_url for the full check before installing.
Uses no model."""
SCAN_DOC = """Check a skill (or a folder of skills) before installing it: a local path or a
GitHub URL (https://github.com/<owner>/<repo>[/tree/<ref>[/<path>]], shallow-cloned into a
temporary folder and deleted; nothing is installed or run). The same JSON as
`skillfetch scan --json`: advice_line (RECOMMENDED / CAUTION / NOT RECOMMENDED with reasons),
license_line, and per skill the lint, injection-scan, size, script, dated-line and license
findings, each with its file, line number and line; contradictions between skills quote both
lines. Uses no model. {error} for a missing folder or a refused URL.
`review=true` adds, per skill, `review.checklist` and `review.files` (the skill's text files with
line numbers): read them against the checklist yourself and show each finding with its file,
line and quoted line before asking to install. The server does not review; it calls no model."""


def _add_scan_tool(server: MCPServer, scan: Callable[[str, bool], dict]) -> None:
    def scan_skill(target: str, review: bool = False) -> dict[str, Any]:
        return scan(target, review)

    scan_skill.__doc__ = SCAN_DOC
    server.tool()(scan_skill)


def _add_find_tool(server: MCPServer, find: Callable[[str, int], dict]) -> None:
    def find_skills(want: str, k: int = DEFAULT_FIND_K) -> dict[str, Any]:
        return find(want, k)

    find_skills.__doc__ = FIND_DOC
    server.tool()(find_skills)


NO_INDEX = {"error": "no skillfetch index: run `skillfetch sync` (or `skillfetch setup`)"}


def build_vet_server(index: Index | None, extract_cache: ExtractCache | None = None) -> MCPServer:
    """`serve --vet`: scan_skill and find_skills, no routing, for the vet skill
    (assets/vet-skill). The index is optional: without one find_skills returns an error and
    scan_skill skips the index lookup for contradictions."""
    server = MCPServer("skillfetch", instructions=VET_INSTRUCTIONS, version=_version())
    model = (index.manifest.get("extract_model") if index else None) or DEFAULT_MODEL
    lookup = Lookup(index, extract_cache or ExtractCache(DEFAULT_CACHE_DIR), model)
    _add_scan_tool(server, lambda target, review: scan_json(target, lookup, review=review))
    searcher = Searcher(index) if index is not None else None
    _add_find_tool(
        server,
        lambda want, k: find_skills(index, searcher, want, k) if index is not None else NO_INDEX,
    )
    return server


def build_server(session: Session) -> MCPServer:
    server = MCPServer("skillfetch", instructions=INSTRUCTIONS, version=_version())
    _add_scan_tool(server, session.scan_skill)
    _add_find_tool(server, session.find_skills)

    @server.tool()
    def profile_repo(path: str) -> dict[str, Any]:
        """Languages, frameworks and package managers of a repo, from its manifest files
        only (package.json, pyproject.toml, go.mod, Cargo.toml, lockfiles, framework
        configs); never reads source. Pass the result to search_skills as `profile`."""
        return session.profile_repo(path)

    @server.tool()
    def search_skills(
        query: str | None = None,
        queries: list[str] | None = None,
        profile: dict[str, Any] | None = None,
        k: int = DEFAULT_K,
        tiers: list[str] | None = None,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Rank indexed skills for a task (BM25). Pass `queries`: 1-4 short sentences, e.g.
        what the task builds, how the user asked to work (if they did), and the stack and
        files; each is searched and the rankings are merged by reciprocal rank fusion (k=60).
        `query` (one sentence) still works; `queries` wins when both are given. `profile`
        (from profile_repo) boosts matching skills and is never part of a query.
        Returns {results: [{id, title, summary, tier, token_estimate}]}, best first, 50 by
        default (at most 200); `summary` is one line. verbose=true returns the full summary
        plus tags and match_reasons. Tiers default to A and B. A query over 2,000 characters
        is cut and the result carries truncated: true; a malformed profile returns
        {error, details}."""
        return session.search_skills(query, profile, k, tiers, verbose, queries=queries)

    @server.tool()
    def resolve_set(auto_ids: list[str], pinned_ids: list[str] | None = None) -> dict[str, Any]:
        """Build a conflict-free set from candidate ids (in preference order, at most 20) plus
        user-pinned ids (always kept; `path:/abs/dir` for a local skill, pinned only).
        Returns {set_id, included, excluded[{id, reason, conflicts_with, evidence}],
        warnings, precedence, suppressed_by_judge, notes, errors}; every exclusion and
        warning quotes the source lines, and suppressed_by_judge counts the warnings dropped
        because the judge called the pair independent."""
        return session.resolve_set(auto_ids, pinned_ids)

    @server.tool()
    def load_skills(set_id: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict[str, Any]:
        """Fetch (or reuse from cache) and verify the bodies of a resolved set and return
        them concatenated in precedence order: {set_id, content, skills, errors}. A skill
        whose files do not match the index hashes, or cannot be fetched, is refused and
        listed in errors; the others still load. Over max_tokens (default 8000) the
        lowest-precedence skills are dropped and listed in errors."""
        return session.load_skills(set_id, max_tokens)

    @server.tool()
    def resolve_and_load(
        auto_ids: list[str],
        pinned_ids: list[str] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict[str, Any]:
        """resolve_set and load_skills in one call, with the same inputs and rules: candidate
        ids (in preference order, at most 20) plus user-pinned ids (always kept; `path:` ids
        pinned only), then the included skills' verified bodies in precedence order.
        Returns {set_id, included, excluded[{id, reason, conflicts_with, evidence}],
        warnings, notes, content, errors}; excluded skills are not loaded, and errors lists
        both resolve and load problems. Over max_tokens (default 8000) the lowest-precedence
        skills are dropped and listed in errors."""
        return session.resolve_and_load(auto_ids, pinned_ids, max_tokens)

    return server


def serve(
    index_dir: Path = DEFAULT_INDEX_DIR,
    profile_root: Path | None = None,
    summary_chars: int = ONE_LINE_CHARS,
) -> None:
    session = Session(Index.load(index_dir), profile_root=profile_root, summary_chars=summary_chars)
    build_server(session).run("stdio")


def serve_vet(index_dir: Path = DEFAULT_INDEX_DIR) -> None:
    try:
        index = Index.load(index_dir)
    except IndexLoadError:  # scanning needs no index; find_skills then says to sync
        index = None
    build_vet_server(index).run("stdio")
