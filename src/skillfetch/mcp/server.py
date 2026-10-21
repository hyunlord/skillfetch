"""MCP server over stdio (`skillfetch serve`): the runtime tools of CLAUDE.md.

Built on the `mcp` SDK 2.x (`MCPServer`, formerly FastMCP). Tools are thin wrappers over
Session; every result is a JSON object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

INSTRUCTIONS = (
    "skillfetch finds vetted skills (SKILL.md instructions) for one task at a time. "
    "Before non-trivial work, restate the task in one sentence with its stack and target "
    "files and call search_skills; pick 1-3 candidates from the summaries; call resolve_set "
    "(user-named skills go in pinned_ids); then load_skills and follow the returned content "
    "in precedence order. Skip this for trivial edits."
)


def build_server(session: Session) -> MCPServer:
    server = MCPServer("skillfetch", instructions=INSTRUCTIONS)

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
        k: int = 10,
        tiers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Rank indexed skills for a one-sentence task description (BM25). `profile`
        (from profile_repo) boosts matching skills and is never part of the query.
        Returns {query, results: [{id, title, summary, tier, tags, match_reasons,
        token_estimate}]}; tiers default to A and B."""
        return session.search_skills(query, profile, k, tiers)

    @server.tool()
    def resolve_set(auto_ids: list[str], pinned_ids: list[str] | None = None) -> dict[str, Any]:
        """Build a conflict-free set from candidate ids (in preference order) plus
        user-pinned ids (always kept; `path:/abs/dir` for a local skill). Returns {set_id,
        included, excluded[{id, reason, conflicts_with, evidence}], warnings, precedence,
        notes, errors}; every exclusion and warning quotes the source lines."""
        return session.resolve_set(auto_ids, pinned_ids)

    @server.tool()
    def load_skills(set_id: str) -> dict[str, Any]:
        """Fetch (or reuse from cache) and verify the bodies of a resolved set and return
        them concatenated in precedence order: {set_id, content, skills, errors}. A skill
        whose files do not match the index hashes is refused and listed in errors."""
        return session.load_skills(set_id)

    return server


def serve(index_dir: Path = DEFAULT_INDEX_DIR) -> None:
    build_server(Session(Index.load(index_dir))).run("stdio")
