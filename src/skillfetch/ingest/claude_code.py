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
