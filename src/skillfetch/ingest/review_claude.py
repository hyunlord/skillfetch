"""`skillfetch scan --review` (docs/design/review.md §3): the checklist applied by an isolated
`claude -p` with the user's own Claude Code login. Kept apart from review.py so the MCP server,
which only hands the checklist to the host agent, imports no model client."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from skillfetch.ingest.claude_code import _clean_env, first_json
from skillfetch.ingest.review import (
    DEFAULT_CACHE,
    SYSTEM,
    Review,
    request_text,
    review_files,
    verify,
)

Runner = Callable[..., subprocess.CompletedProcess]


class ClaudeReviewer:
    """One isolated `claude -p` per skill: no tools, no MCP servers, project settings only, a
    scratch working folder, no API key (ClaudeCliBackend's setup). Replies are cached in
    <cache>/<sha>.json, keyed by the system prompt and the request."""

    def __init__(
        self,
        cache: Path = DEFAULT_CACHE,
        claude: str = "claude",
        run: Runner = subprocess.run,
        timeout: float = 600,
    ):
        self.cache, self.claude, self._run, self.timeout = cache, claude, run, timeout

    def ask(self, prompt: str) -> dict:
        """{result, model, cost_usd, cached} for one request, from the cache or `claude -p`."""
        sha = hashlib.sha256(json.dumps([SYSTEM, prompt]).encode()).hexdigest()
        path = self.cache / f"{sha}.json"
        if path.is_file():
            return {**json.loads(path.read_text()), "cached": True}
        with tempfile.TemporaryDirectory(prefix="skillfetch-review-") as tmp:
            iso = Path(tmp)
            (iso / "mcp.json").write_text('{"mcpServers":{}}')
            (iso / "system.txt").write_text(SYSTEM)
            proc = self._run(
                [
                    self.claude,
                    "-p",
                    prompt,
                    "--system-prompt-file",
                    str(iso / "system.txt"),
                    "--tools",
                    "",
                    "--strict-mcp-config",
                    "--mcp-config",
                    str(iso / "mcp.json"),
                    "--setting-sources",
                    "project",
                    "--output-format",
                    "json",
                    "--no-session-persistence",
                ],
                cwd=iso,
                env=_clean_env(),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                stdin=subprocess.DEVNULL,
            )
        try:
            reply = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"claude -p: no JSON output (exit {proc.returncode})") from exc
        if reply.get("is_error"):
            raise RuntimeError(f"claude -p: {str(reply.get('result'))[:200]}")
        out = {
            "result": reply.get("result") or "",
            "model": next(iter((reply.get("modelUsage") or {}).keys()), None),
            "cost_usd": reply.get("total_cost_usd"),
        }
        self.cache.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False))
        return {**out, "cached": False}

    def __call__(self, skill_dir: Path) -> Review:
        files, left = review_files(skill_dir)
        if not files:
            return Review(by="claude -p", not_reviewed=left, error="no text files to review")
        try:
            got = self.ask(request_text(files))
            raw = first_json(got["result"]).get("findings") or []
        except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError) as exc:
            return Review(by="claude -p", not_reviewed=left, error=str(exc)[:300])
        findings, dropped = verify(raw if isinstance(raw, list) else [], files)
        return Review(
            by=f"claude -p ({got['model'] or 'default model'})",
            findings=findings,
            unverified=dropped,
            not_reviewed=left,
            cost_usd=None if got["cached"] else got["cost_usd"],
        )
