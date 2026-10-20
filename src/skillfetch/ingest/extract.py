"""Constraint extraction through the Claude API (index-format.md §1.5, constraints.md §2).

The only stage that calls a model. `anthropic` is imported lazily in `make_client`, so the
rest of the package (and every test) runs without it; tests pass a client that replays
recorded responses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from skillfetch.ingest.skillfile import SKILL_FILE, read_text
from skillfetch.resolve.models import Constraint
from skillfetch.resolve.vocabulary import VOCABULARY

# Bump EXTRACT_VERSION whenever the prompt or the response schema changes; it is part of the
# cache key. tests/ingest/test_extract.py pins PROMPT_SHA256 so a change cannot slip through.
EXTRACT_VERSION = 1
PROMPT_SHA256 = "11867143327050c97fadde99ad8fa1f07910061038dd5547a71b7e033a3d5a64"

DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000
MAX_SKILL_TOKENS = 12000  # index-format §1.5 cost guard, estimated as chars / 4

# Models that still accept sampling parameters. Current models (Sonnet 5, Opus 5, ...)
# reject `temperature` with a 400, so determinism there comes from the extract cache.
TEMPERATURE_ZERO_MODELS = frozenset({"claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"})

# USD per million tokens (input, output), Anthropic first-party list prices as of 2026-06-24.
# Cache writes bill at 1.25x input, cache reads at 0.1x input.
PRICES: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-opus-5": (5.00, 25.00),
}

ARTIFACTS = [
    "code",
    "tests",
    "commit-message",
    "pr-description",
    "markdown",
    "response",
    "plan",
    "any",
]
PHASES = ["plan", "implement", "test", "review", "format", "any"]
TAG_PHASES = [p for p in PHASES if p != "any"]


# --- prompt and schema --------------------------------------------------------------------


def _render_vocabulary() -> str:
    groups: dict[str, list[str]] = {}
    for term in VOCABULARY:
        label = f"`{term.name}`"
        if term.exclusive:
            choices = "; ".join(
                f"{eco.name}: {', '.join(sorted(eco.choices))}" for eco in term.ecosystems
            )
            label += f" (one tool per ecosystem — {choices})"
        groups.setdefault(term.group, []).append(label)
    return "\n".join(f"- {group}: {', '.join(labels)}" for group, labels in groups.items())


@cache
def system_prompt() -> str:
    template = resources.files("skillfetch.ingest").joinpath("prompts/extract.md").read_text()
    return template.replace("{{VOCABULARY}}", _render_vocabulary())


def _string_or_null() -> dict:
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


def _object(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _strings() -> dict:
    return {"type": "array", "items": {"type": "string"}}


@cache
def response_schema() -> dict:
    """Strict JSON schema for `output_config.format` (mirrors ExtractResult)."""
    constraint = _object(
        {
            "subject": {"type": "string"},
            "directive": {
                "type": "string",
                "enum": ["require", "forbid", "prefer", "avoid", "order"],
            },
            "object": _string_or_null(),
            "direction": {
                "anyOf": [{"type": "string", "enum": ["before", "after"]}, {"type": "null"}]
            },
            "scope": _object(
                {
                    "artifact": {"type": "string", "enum": ARTIFACTS},
                    "phase": {"type": "string", "enum": PHASES},
                    "condition": _string_or_null(),
                }
            ),
            "strength": {"type": "string", "enum": ["must", "should"]},
            "evidence": _object({"line_no": {"type": "integer"}, "text": {"type": "string"}}),
        }
    )
    return _object(
        {
            "summary": {"type": "string"},
            "keywords": _strings(),
            "tags": _object(
                {
                    "languages": _strings(),
                    "frameworks": _strings(),
                    "phase": {"type": "array", "items": {"type": "string", "enum": TAG_PHASES}},
                    "domain": _strings(),
                }
            ),
            "synthetic_queries": _strings(),
            "constraints": {"type": "array", "items": constraint},
            "consumes": _strings(),
            "produces": _strings(),
            "requires_tools": _strings(),
        }
    )


def prompt_fingerprint() -> str:
    """sha256 over the rendered system prompt and the response schema."""
    payload = system_prompt() + "\n" + json.dumps(response_schema(), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def numbered(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    width = len(str(len(lines)))
    return "\n".join(f"{i:>{width}}| {line}" for i, line in enumerate(lines, 1))


def build_request(model: str, messages: list[dict]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": [
            {"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}
        ],
        "messages": messages,
        "output_config": {"format": {"type": "json_schema", "schema": response_schema()}},
    }
    if model in TEMPERATURE_ZERO_MODELS:
        request["temperature"] = 0
    return request


# --- result types -----------------------------------------------------------------------------


class ExtractTags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    languages: list[str]
    frameworks: list[str]
    phase: list[Literal["plan", "implement", "test", "review", "format"]]
    domain: list[str]


class ExtractResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    keywords: list[str]
    tags: ExtractTags
    synthetic_queries: list[str]
    constraints: list[Constraint]
    consumes: list[str]
    produces: list[str]
    requires_tools: list[str]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(**{k: getattr(self, k) + getattr(other, k) for k in Usage.model_fields})


class Attempt(BaseModel):
    stop_reason: str | None
    text: str
    usage: Usage
    error: str | None = None


class Dropped(BaseModel):
    constraint: dict
    reason: str


class ExtractRecord(BaseModel):
    """One skill's extraction; also the on-disk cache entry."""

    extract_version: int
    model: str
    content_hash: str
    skill_id: str
    status: Literal["ok", "extract_failed", "too_large"]
    result: ExtractResult | None = None
    error: str | None = None
    dropped: list[Dropped] = []
    repaired: list[str] = []
    attempts: list[Attempt] = []

    @property
    def usage(self) -> Usage:
        total = Usage()
        for a in self.attempts:
            total = total + a.usage
        return total

    @property
    def cost_usd(self) -> float | None:
        return cost_usd(self.model, self.usage)

    def constraints(self) -> list[Constraint]:
        if self.result is None:
            return []
        return [
            c.model_copy(update={"id": f"{self.skill_id}#c{i}"})
            for i, c in enumerate(self.result.constraints, 1)
        ]


def cost_usd(model: str, usage: Usage) -> float | None:
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (
        usage.input_tokens * price_in
        + usage.cache_creation_input_tokens * price_in * 1.25
        + usage.cache_read_input_tokens * price_in * 0.1
        + usage.output_tokens * price_out
    ) / 1_000_000


# --- evidence ----------------------------------------------------------------------------------


def verify_evidence(
    result: ExtractResult, lines: list[str]
) -> tuple[ExtractResult, list[Dropped], list[str]]:
    """Keep only constraints whose quote appears on a line of SKILL.md (constraints.md §1).

    A quote found on its cited line is kept. A quote found on exactly one other line is a
    miscounted line number: kept, line corrected, and reported. Anything else is dropped."""
    kept: list[Constraint] = []
    dropped: list[Dropped] = []
    repaired: list[str] = []
    for c in result.constraints:
        text, line_no = c.evidence.text, c.evidence.line_no
        if 1 <= line_no <= len(lines) and text in lines[line_no - 1]:
            kept.append(c)
            continue
        hits = [i for i, line in enumerate(lines, 1) if text in line]
        if len(hits) == 1:
            evidence = c.evidence.model_copy(update={"line_no": hits[0]})
            kept.append(c.model_copy(update={"evidence": evidence}))
            repaired.append(f"line {line_no} -> {hits[0]}: {text!r}")
        else:
            reason = "quote not found in SKILL.md" if not hits else "quote is ambiguous"
            dropped.append(Dropped(constraint=c.model_dump(mode="json"), reason=reason))
    return result.model_copy(update={"constraints": kept}), dropped, repaired


# --- extractor ---------------------------------------------------------------------------------


class MessagesClient(Protocol):
    """The slice of `anthropic.Anthropic` we use: `client.messages.create(**request)`."""

    messages: Any


class MissingCredentials(RuntimeError):
    pass


def make_client() -> MessagesClient:
    import anthropic  # optional dependency: pip install 'skillfetch[ingest]'

    client = anthropic.Anthropic(max_retries=4)
    # Without credentials the SDK only fails when it builds the first request, with a bare
    # TypeError; check up front instead. `credentials` covers `ant auth login` profiles and
    # workload identity federation.
    if not (client.api_key or client.auth_token or getattr(client, "credentials", None)):
        raise MissingCredentials(
            "no Anthropic credentials found: set ANTHROPIC_API_KEY or run `ant auth login`"
        )
    return client


def _response_text(response: Any) -> str:
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def _usage(response: Any) -> Usage:
    u = response.usage
    return Usage(**{k: getattr(u, k, None) or 0 for k in Usage.model_fields})


def _validate(text: str) -> ExtractResult:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc
    try:
        return ExtractResult.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@dataclass
class Extractor:
    client: MessagesClient
    model: str = DEFAULT_MODEL

    def extract(self, skill_dir: Path, skill_id: str, content_hash: str) -> ExtractRecord:
        text = read_text(skill_dir / SKILL_FILE)
        record = ExtractRecord(
            extract_version=EXTRACT_VERSION,
            model=self.model,
            content_hash=content_hash,
            skill_id=skill_id,
            status="extract_failed",
        )
        if len(text) // 4 > MAX_SKILL_TOKENS:
            record.status = "too_large"
            record.error = f"SKILL.md is ~{len(text) // 4} tokens (> {MAX_SKILL_TOKENS})"
            return record

        messages: list[dict] = [{"role": "user", "content": numbered(text)}]
        for attempt_no in (1, 2):
            response = self.client.messages.create(**build_request(self.model, messages))
            out = _response_text(response)
            attempt = Attempt(stop_reason=response.stop_reason, text=out, usage=_usage(response))
            record.attempts.append(attempt)
            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                attempt.error = record.error = (
                    f"refused ({getattr(details, 'category', None) or 'no category'})"
                )
                return record
            try:
                result = _validate(out)
            except ValueError as exc:
                attempt.error = record.error = str(exc)
                if attempt_no == 1:
                    messages += [
                        {"role": "assistant", "content": response.content or "(no output)"},
                        {
                            "role": "user",
                            "content": "That output failed validation:\n"
                            f"{exc}\n\nReturn the complete corrected JSON object.",
                        },
                    ]
                continue
            record.result, record.dropped, record.repaired = verify_evidence(
                result, text.split("\n")
            )
            record.status, record.error = "ok", None
            return record
        return record
