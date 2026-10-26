"""MCP server over stdio (`skillfetch serve`): the runtime tools of CLAUDE.md.

Built on the `mcp` SDK 2.x (`MCPServer`, formerly FastMCP). Tools are thin wrappers over
Session; every result is a JSON object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.index.search import DEFAULT_K, ONE_LINE_CHARS
from skillfetch.mcp.session import DEFAULT_MAX_TOKENS, Session

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


def build_server(session: Session) -> MCPServer:
    server = MCPServer("skillfetch", instructions=INSTRUCTIONS, version=_version())

    @server.tool()
    def profile_repo(path: str) -> dict[str, Any]:
        """Languages, frameworks and package managers of a repo, from its manifest files
        only (package.json, pyproject.toml, go.mod, Cargo.toml, lockfiles, framework
        configs); never reads source. Pass the result to search_skills as `profile`.
        When the repo root has a `.skillfetch.yaml`, the result also carries `org` (the
        organisation's index source) and `baseline` (ids of skills to pin on every task;
        names that match no skill, or several, are in `baseline_unresolved`)."""
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
        (from profile_repo) boosts matching skills and is never part of a query; when it
        has an `org`, results from that source carry org: true.
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
