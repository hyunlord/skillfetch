"""LLM judge for the pairs the rules could not settle (needs_review, tension).

A second model, not the extractor, reads the original lines — each evidence line with five
lines of context and its section heading — and never the extracted constraints, so it does
not inherit the extractor's mistakes. It returns a verdict (conflict / carve_out /
situational / independent / unclear), one sentence of reasoning, whether an agent given both
skills would be confused (`ambiguous_together`), and a confidence.

Calibration first: the 34 informative fixture pairs have hand labels (vocabulary-cap labels,
i.e. the real relations); agreement must reach JUDGE_TARGET before the corpus run.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from skillfetch.ingest.extract import Completion, ExtractBackend
from skillfetch.ingest.sections import section_headings

JUDGE_VERSION = 1
DEFAULT_JUDGE_MODEL = "openrouter/anthropic/claude-sonnet-5.5"
DEFAULT_CACHE = Path("~/.skillfetch/judge-cache").expanduser()
CONTEXT_LINES = 5
MAX_EVIDENCE = 2  # evidence lines per side
JUDGE_TARGET = 0.8
Verdict = Literal["conflict", "carve_out", "situational", "independent", "unclear"]
VERDICTS: tuple[str, ...] = ("conflict", "carve_out", "situational", "independent", "unclear")

# Hand label -> verdicts that agree with it (calibration).
ACCEPT: dict[str, frozenset[str]] = {
    "conflict": frozenset({"conflict"}),
    "tension": frozenset({"conflict"}),  # soft opposition: still opposite instructions
    "needs_review": frozenset({"carve_out", "situational"}),
    "redundant": frozenset({"independent"}),  # the same instruction twice
    "subsumes": frozenset({"independent"}),
}


@cache
def judge_prompt() -> str:
    return resources.files("skillfetch.ingest").joinpath("prompts/judge.md").read_text()


@cache
def judge_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": list(VERDICTS)},
            "reason": {"type": "string"},
            "ambiguous_together": {"type": "boolean"},
            "confidence": {"type": "number"},
        },
        "required": ["verdict", "reason", "ambiguous_together", "confidence"],
        "additionalProperties": False,
    }


class Judgment(BaseModel):
    verdict: Verdict
    reason: str
    ambiguous_together: bool
    confidence: float = Field(ge=0, le=1)


class JudgeRecord(BaseModel):
    """One judged pair; also the cache entry."""

    judge_version: int
    model: str
    input_sha256: str
    judgment: Judgment | None = None
    error: str | None = None
    cost_usd: float | None = None


@dataclass(frozen=True)
class Side:
    skill_id: str
    name: str
    description: str
    text: str  # the SKILL.md
    lines: tuple[int, ...]  # evidence line numbers (1-based)


def excerpt(side: Side, context: int = CONTEXT_LINES) -> str:
    lines = side.text.split("\n")
    headings = section_headings(lines)
    marked = sorted(set(side.lines))[:MAX_EVIDENCE]
    shown: set[int] = set()
    for n in marked:
        shown.update(range(max(1, n - context), min(len(lines), n + context) + 1))
    out = [f"skill: {side.name}", f"description: {side.description.strip()}"]
    for n in marked:
        out.append(f"section heading of line {n}: {headings[n - 1] or '(none)'}")
    prev = None
    for n in sorted(shown):
        if prev is not None and n != prev + 1:
            out.append("   …")
        out.append(f"{'>' if n in marked else ' '}{n:>5}| {lines[n - 1]}")
        prev = n
    return "\n".join(out)


def pair_input(a: Side, b: Side) -> str:
    return f"## Skill A\n\n{excerpt(a)}\n\n## Skill B\n\n{excerpt(b)}\n"


class Judge:
    def __init__(self, backend: ExtractBackend, cache_dir: Path = DEFAULT_CACHE):
        self.backend = backend
        self.cache_dir = cache_dir

    @property
    def model(self) -> str:
        return self.backend.key

    def _path(self, sha: str) -> Path:
        return self.cache_dir / f"v{JUDGE_VERSION}" / self.model / f"{sha}.json"

    def judge(self, user_text: str) -> tuple[JudgeRecord, bool]:
        """(record, fresh). API errors propagate; model-output errors are recorded."""
        sha = hashlib.sha256((judge_prompt() + "\0" + user_text).encode()).hexdigest()
        path = self._path(sha)
        if path.is_file():
            return JudgeRecord.model_validate_json(path.read_text()), False
        reply: Completion = self.backend.complete(
            judge_prompt(), [{"role": "user", "content": user_text}], judge_schema()
        )
        record = JudgeRecord(
            judge_version=JUDGE_VERSION,
            model=self.model,
            input_sha256=sha,
            cost_usd=reply.usage.reported_cost_usd,
        )
        try:
            record.judgment = Judgment.model_validate(json.loads(reply.text))
        except (json.JSONDecodeError, ValidationError) as exc:
            record.error = str(exc)[:500]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json())
        return record, True


@dataclass
class Item:
    key: str  # "a|b"
    text: str


@dataclass
class Outcome:
    key: str
    record: JudgeRecord | None
    fresh: bool
    error: str | None = None  # an API error: not cached, retried on the next run


def run_judge(
    items: Iterable[Item],
    judge: Judge,
    jobs: int = 8,
    progress: Callable[[int], None] | None = None,
) -> list[Outcome]:
    """Judge items in parallel. One failing request is recorded and the run continues."""

    def one(item: Item) -> Outcome:
        try:
            record, fresh = judge.judge(item.text)
            return Outcome(item.key, record, fresh)
        except Exception as exc:  # network / provider errors: isolate per pair
            return Outcome(item.key, None, False, f"{type(exc).__name__}: {str(exc)[:200]}")

    items = list(items)
    out: list[Outcome] = []
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        for n, outcome in enumerate(pool.map(one, items), 1):
            out.append(outcome)
            if progress and n % 100 == 0:
                progress(n)
    return out


def agrees(label: str, verdict: str) -> bool:
    return verdict in ACCEPT[label.split(":", 1)[0]]
