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
    MAX_CHARS,
    MAX_CHUNKS,
    SYSTEM,
    Review,
    request_text,
    review_chunks,
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
        chunk_chars: int = MAX_CHARS,
        max_chunks: int = MAX_CHUNKS,
        skill_md_only: bool = False,
    ):
        self.cache, self.claude, self._run, self.timeout = cache, claude, run, timeout
        self.chunk_chars, self.max_chunks = chunk_chars, max_chunks
        self.skill_md_only = skill_md_only

    def ask(self, prompt: str) -> dict:
        """{findings, model, cost_usd, cached} for one request, from the cache or `claude -p`.
        Raises RuntimeError or ValueError when the reply failed or holds no findings JSON (cut
        off or refused); such a reply is not cached, so a later run asks again."""
        sha = hashlib.sha256(json.dumps([SYSTEM, prompt]).encode()).hexdigest()
        path = self.cache / f"{sha}.json"
        if path.is_file():
            got = json.loads(path.read_text())
            return {**got, "findings": _findings(got["result"]), "cached": True}
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
        try:
            findings = _findings(out["result"])  # raises before anything is cached
        except ValueError as exc:
            raise ReplyError(str(exc), out["cost_usd"]) from exc
        self.cache.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False))
        return {**out, "findings": findings, "cached": False}

    def __call__(self, skill_dir: Path) -> Review:
        chunks, files, left = review_chunks(
            skill_dir, self.chunk_chars, self.max_chunks, self.skill_md_only
        )
        if not chunks:
            return Review(by="claude -p", not_reviewed=left, error="no text files to review")
        raw: list = []
        model, cost, errors = None, 0.0, []
        for i, parts in enumerate(chunks, 1):
            try:
                got = self.ask(request_text(parts, i, len(chunks)))
            except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError) as exc:
                cost += getattr(exc, "cost_usd", None) or 0  # a failed reply is still paid for
                where = f"part {i} of {len(chunks)}: " if len(chunks) > 1 else ""
                errors.append(where + str(exc)[:300])
                continue
            raw += got["findings"]
            model = model or got["model"]
            cost += 0 if got["cached"] else got["cost_usd"] or 0
        findings, dropped = verify(raw, files)
        return Review(
            by=f"claude -p ({model or 'default model'})",
            findings=findings,
            unverified=dropped,
            not_reviewed=left,
            error="; ".join(errors) or None,
            cost_usd=cost or None,
            requests=len(chunks),
        )


class ReplyError(ValueError):
    """A reply that came back but holds no findings; carries what it cost."""

    def __init__(self, message: str, cost_usd: float | None):
        super().__init__(message)
        self.cost_usd = cost_usd


def _findings(result: str) -> list:
    """The findings list of a reply. A reply with no JSON object (cut off by a safety
    classifier, or a refusal in prose) raises ValueError."""
    got = first_json(result).get("findings")
    if got is None:
        raise ValueError("no findings in the reply")
    if not isinstance(got, list):
        raise ValueError("findings is not a list")
    return got
