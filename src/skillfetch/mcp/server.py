"""MCP server over stdio (`skillfetch serve`): the runtime tools of CLAUDE.md.

Built on the `mcp` SDK 2.x (`MCPServer`, formerly FastMCP). Tools are thin wrappers over
Session; every result is a JSON object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.index.search import DEFAULT_K
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
        configs); never reads source. Pass the result to search_skills as `profile`."""
        return session.profile_repo(path)

    @server.tool()
    def search_skills(
        query: str,
        profile: dict[str, Any] | None = None,
        k: int = DEFAULT_K,
        tiers: list[str] | None = None,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Rank indexed skills for a one-sentence task description (BM25). `profile`
        (from profile_repo) boosts matching skills and is never part of the query.
        Returns {query, results: [{id, title, summary, tier, token_estimate}]}, best
        first, 50 by default; `summary` is one line. verbose=true returns the full
        summary plus tags and match_reasons. Tiers default to A and B."""
        return session.search_skills(query, profile, k, tiers, verbose)

    @server.tool()
    def resolve_set(auto_ids: list[str], pinned_ids: list[str] | None = None) -> dict[str, Any]:
        """Build a conflict-free set from candidate ids (in preference order) plus
        user-pinned ids (always kept; `path:/abs/dir` for a local skill). Returns {set_id,
        included, excluded[{id, reason, conflicts_with, evidence}], warnings, precedence,
        suppressed_by_judge, notes, errors}; every exclusion and warning quotes the source
        lines, and suppressed_by_judge counts the warnings dropped because the judge called
        the pair independent."""
        return session.resolve_set(auto_ids, pinned_ids)

    @server.tool()
    def load_skills(set_id: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict[str, Any]:
        """Fetch (or reuse from cache) and verify the bodies of a resolved set and return
        them concatenated in precedence order: {set_id, content, skills, errors}. A skill
        whose files do not match the index hashes, or cannot be fetched, is refused and
        listed in errors; the others still load. Over max_tokens (default 8000) the
        lowest-precedence skills are dropped and listed in errors."""
        return session.load_skills(set_id, max_tokens)

    return server


def serve(index_dir: Path = DEFAULT_INDEX_DIR) -> None:
    build_server(Session(Index.load(index_dir))).run("stdio")
