"""The `claude-code` backend: model requests answered inside a Claude Code session, not by
an API. No network and no API cost (the default since the "no external API" rule).

`complete()` hashes the request. If `<queue>/answers/<sha>.json` exists, its text is the
completion; otherwise the request is written to `<queue>/pending/<sha>.json` (the system
prompt once, under `systems/`) and `PendingAnswer` is raised. Callers already isolate
per-item failures, so a run records the item as not done and goes on; after the answers
are written, a rerun picks them up and caches them in the usual format, keyed
`claude-code/<model>` (the cache records that backend).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from skillfetch.ingest.extract import Completion, Usage

DEFAULT_QUEUE = Path("~/.skillfetch/claude-code-queue").expanduser()


class PendingAnswer(RuntimeError):
    """The request is queued for Claude Code; rerun once it is answered."""


def request_sha(system: str, messages: list[dict[str, str]], schema: dict) -> str:
    payload = json.dumps({"system": system, "messages": messages, "schema": schema}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class ClaudeCodeBackend:
    def __init__(self, model: str, queue: Path = DEFAULT_QUEUE):
        self.model = model
        self.queue = queue

    @property
    def key(self) -> str:
        return f"claude-code/{self.model}"

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        sha = request_sha(system, messages, schema)
        answer = self.queue / "answers" / f"{sha}.json"
        if answer.is_file():
            data = json.loads(answer.read_text())
            text = data["text"] if isinstance(data, dict) and "text" in data else json.dumps(data)
            return Completion(text=text, stop_reason="end_turn", usage=Usage(reported_cost_usd=0.0))
        system_sha = hashlib.sha256(system.encode()).hexdigest()
        systems = self.queue / "systems"
        systems.mkdir(parents=True, exist_ok=True)
        (systems / f"{system_sha}.txt").write_text(system)
        pending = self.queue / "pending"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / f"{sha}.json").write_text(
            json.dumps(
                {
                    "model": self.key,
                    "system_sha256": system_sha,
                    "messages": messages,
                    "schema": schema,
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        raise PendingAnswer(f"queued for Claude Code: {pending / f'{sha}.json'}")


def _clean_env() -> dict[str, str]:
    """The environment for a nested `claude -p`: without the variables that tell it it runs
    inside another Claude Code session."""
    env = dict(os.environ)
    for key in list(env):
        if key == "CLAUDECODE" or key.startswith("CLAUDE_CODE_"):
            env.pop(key)
    return env


def first_json(text: str) -> dict:
    """The first JSON object in a reply (inside a ```json fence when there is one)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    start = body.find("{")
    if start < 0:
        raise ValueError("no JSON object in the reply")
    return json.JSONDecoder().raw_decode(body[start:])[0]


def _prompt(messages: list[dict[str, str]], schema: dict) -> str:
    if len(messages) == 1:
        convo = messages[0]["content"]
    else:  # a correction round: the request, the earlier answer, the validation feedback
        parts = []
        for m in messages:
            label = (
                "Your earlier answer"
                if m["role"] == "assistant"
                else "Request"
                if not parts
                else "Feedback"
            )
            parts.append(f"[{label}]\n{m['content']}")
        convo = "\n\n".join(parts)
    return (
        f"{convo}\n\nReply with one JSON object that matches this JSON schema, and nothing "
        f"else:\n{json.dumps(schema, ensure_ascii=False)}"
    )


class ClaudeCliBackend(ClaudeCodeBackend):
    """The claude-code backend answered at once: a request with no stored answer is sent to
    an isolated `claude -p` (the user's own Claude Code login and plan; no API key, no
    tools, no MCP servers, no user settings, a scratch working directory), and the answer is
    stored in the queue like any other, so a rerun reads it from there."""

    def __init__(
        self,
        model: str,
        queue: Path = DEFAULT_QUEUE,
        claude: str = "claude",
        run=subprocess.run,
        timeout: float = 900,
    ):
        super().__init__(model, queue)
        self.claude, self._run, self.timeout = claude, run, timeout

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        try:
            return super().complete(system, messages, schema)
        except PendingAnswer:
            pass
        sha = request_sha(system, messages, schema)
        with tempfile.TemporaryDirectory(prefix="skillfetch-claude-") as tmp:
            iso = Path(tmp)
            (iso / "mcp.json").write_text('{"mcpServers":{}}')
            (iso / "system.txt").write_text(system)
            cmd = [
                self.claude,
                "-p",
                _prompt(messages, schema),
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
            ]
            proc = self._run(
                cmd,
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
        text = json.dumps(first_json(reply.get("result") or ""), ensure_ascii=False)
        answers = self.queue / "answers"
        answers.mkdir(parents=True, exist_ok=True)
        (answers / f"{sha}.json").write_text(json.dumps({"text": text}, ensure_ascii=False))
        (self.queue / "pending" / f"{sha}.json").unlink(missing_ok=True)
        return Completion(text=text, stop_reason="end_turn", usage=Usage(reported_cost_usd=0.0))
