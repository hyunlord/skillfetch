"""Constraint extraction through a model API (index-format.md §1.5, constraints.md §2).

The only stage that calls a model. Provider specifics live behind `ExtractBackend`
(`ingest/backends.py`); SDKs are imported lazily there, so the rest of the package (and
every test) runs without them. Tests use backends over clients that replay recorded
responses.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from skillfetch.ingest.sections import record_sections
from skillfetch.ingest.skillfile import SKILL_FILE, read_text
from skillfetch.resolve.models import Constraint
from skillfetch.resolve.terms import normalize_term
from skillfetch.resolve.vocabulary import (
    VOCABULARY,
    condition_is_clause,
    contained_term,
    implied_artifact,
    lookup,
    term_words,
)

# Bump EXTRACT_VERSION whenever the prompt or the response schema changes; it is part of the
# cache key. tests/ingest/test_extract.py pins PROMPT_SHA256 so a change cannot slip through.
EXTRACT_VERSION = 6
PROMPT_SHA256 = "ceddd0e8e1d42afdd6496d1365ed16f134ceae04e518d3bd277a42344634cb75"

DEFAULT_MODEL = "openrouter/openai/gpt-6-luna"  # "provider/model"; see backends.parse_model
REQUEST_TIMEOUT_S = 120  # per HTTP request; the SDK default (600 s) let one stuck call stall a run
MAX_TOKENS = 16000
MAX_SKILL_TOKENS = 12000  # index-format §1.5 cost guard, estimated as chars / 4


@dataclass(frozen=True)
class Price:
    """USD per million tokens."""

    input: float
    output: float
    cache_read: float
    cache_write: float


def _anthropic(price_in: float, price_out: float) -> Price:
    # cache writes bill at 1.25x input, cache reads at 0.1x input
    return Price(price_in, price_out, price_in * 0.1, price_in * 1.25)


# List prices, keyed like ExtractRecord.model. Anthropic first-party prices as of 2026-06-24.
PRICES: dict[str, Price] = {
    "anthropic/claude-sonnet-5": _anthropic(2.00, 10.00),
    "anthropic/claude-sonnet-4-6": _anthropic(3.00, 15.00),
    "anthropic/claude-haiku-4-5": _anthropic(1.00, 5.00),
    "anthropic/claude-opus-5": _anthropic(5.00, 25.00),
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
        if term.objects is not None:
            listed = ", ".join(f'"{o}"' for o in term.objects)
            label += f" (objects: {listed})" if listed else " (no object)"
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
            "object_raw": _string_or_null(),
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


# --- result types -----------------------------------------------------------------------------


class ExtractTags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    languages: list[str]
    frameworks: list[str]
    phase: list[Literal["plan", "implement", "test", "review", "format"]]
    domain: list[str]


MAX_SUBJECT_WORDS = 3
# Words that open a situation inside a subject: "confirmation when the overlap reaches 30%".
_CLAUSE_MARKER = re.compile(
    r"\s+(?=(?:when|whenever|if|unless|once|after|before|while|during|until|wherever)\s)",
    re.IGNORECASE,
)


def _subject_words(subject: str) -> int:
    return len(subject.split())


def split_subject_clause(c: dict) -> str | None:
    """Move a situation out of a raw constraint's subject: the clause becomes the
    condition (when there is none) and is kept in object_raw (when that is empty), since
    it narrows the rule. Vocabulary terms and `order` subjects are left alone. Returns a
    note, or None when nothing was split."""
    subject = c.get("subject")
    if not isinstance(subject, str) or c.get("directive") == "order" or lookup(subject):
        return None
    m = _CLAUSE_MARKER.search(subject)
    if m is None or not subject[: m.start()].strip():
        return None
    head, clause = subject[: m.start()].strip(), subject[m.end() :].strip()
    c["subject"] = head
    scope = c.get("scope") if isinstance(c.get("scope"), dict) else {}
    c["scope"] = scope
    moved = []
    if scope.get("condition") is None:
        scope["condition"] = clause
        moved.append("condition")
    if not c.get("object_raw"):
        c["object_raw"] = clause
        moved.append("object_raw")
    line = (c.get("evidence") or {}).get("line_no", "?")
    to = " and ".join(moved) or "nowhere (condition and object_raw already set)"
    return f"line {line}: subject {subject!r} -> {head!r}, clause {clause!r} -> {to}"


class ExtractResult(BaseModel):
    """Validation context (optional): `notes` (list) collects clause splits;
    `drop_long_subjects` drops constraints whose subject is still over MAX_SUBJECT_WORDS
    into `dropped` (list) instead of failing — used on the last attempt."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    keywords: list[str]
    tags: ExtractTags
    synthetic_queries: list[str]
    constraints: list[Constraint]
    consumes: list[str]
    produces: list[str]
    requires_tools: list[str]

    @model_validator(mode="before")
    @classmethod
    def _split_clauses(cls, data, info: ValidationInfo):
        if not isinstance(data, dict) or not isinstance(data.get("constraints"), list):
            return data
        data = copy.deepcopy(data)
        notes = (info.context or {}).get("notes")
        for c in data["constraints"]:
            if isinstance(c, dict) and (note := split_subject_clause(c)) and notes is not None:
                notes.append(note)
        return data

    @field_validator("constraints")
    @classmethod
    def _short_subjects(cls, constraints: list[Constraint], info: ValidationInfo):
        long = [c for c in constraints if _subject_words(c.subject) > MAX_SUBJECT_WORDS]
        if not long:
            return constraints
        context = info.context or {}
        if context.get("drop_long_subjects"):
            reason = f"subject over {MAX_SUBJECT_WORDS} words after the retry"
            context["dropped"].extend(
                Dropped(constraint=c.model_dump(mode="json"), reason=reason) for c in long
            )
            return [c for c in constraints if c not in long]
        raise ValueError(
            "\n".join(
                f"line {c.evidence.line_no}: subject {c.subject!r} has "
                f"{_subject_words(c.subject)} words; use at most {MAX_SUBJECT_WORDS} words "
                "naming the thing the rule regulates, and keep the rest of the line's "
                "wording in object_raw"
                for c in long
            )
        )


TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    reported_cost_usd: float | None = None  # billed amount, when the provider reports it

    def __add__(self, other: Usage) -> Usage:
        tokens = {k: getattr(self, k) + getattr(other, k) for k in TOKEN_FIELDS}
        a, b = self.reported_cost_usd, other.reported_cost_usd
        return Usage(**tokens, reported_cost_usd=None if a is None or b is None else a + b)


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
    model: str  # backend key, "provider/model"
    content_hash: str
    skill_id: str
    status: Literal["ok", "extract_failed", "too_large"]
    result: ExtractResult | None = None
    error: str | None = None
    dropped: list[Dropped] = []
    repaired: list[str] = []
    adjusted: list[str] = []  # post-processing notes (headings, polarity, artifact, ...)
    attempts: list[Attempt] = []

    @property
    def usage(self) -> Usage:
        if not self.attempts:
            return Usage()
        total = self.attempts[0].usage
        for a in self.attempts[1:]:
            total = total + a.usage
        return total

    @property
    def cost_usd(self) -> float | None:
        """The provider-reported charge when every attempt has one, else list prices."""
        usage = self.usage
        if usage.reported_cost_usd is not None:
            return usage.reported_cost_usd
        return cost_usd(self.model, usage)

    def constraints(self) -> list[Constraint]:
        if self.result is None:
            return []
        return [
            c.model_copy(update={"id": f"{self.skill_id}#c{i}"})
            for i, c in enumerate(self.result.constraints, 1)
        ]


def cost_usd(model: str, usage: Usage) -> float | None:
    price = PRICES.get(model)
    if price is None:
        return None
    return (
        usage.input_tokens * price.input
        + usage.cache_creation_input_tokens * price.cache_write
        + usage.cache_read_input_tokens * price.cache_read
        + usage.output_tokens * price.output
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


_REMOVAL = re.compile(
    r"\b(strip|strips|stripped|remove|removes|removed|delete|deletes|deleted|trim|trims|"
    r"trimmed|drop|drops|eliminate|eliminates|avoid|avoids|get rid of)\b",
    re.IGNORECASE,
)
_FLIP = {"require": ("forbid", "must"), "prefer": ("avoid", "should")}


def _normalized_subject(c: Constraint) -> str | None:
    found = contained_term(c.subject)
    if found is None:
        return None
    term, rest = found
    scope = c.scope
    covered = set().union(
        *(term_words(v) for v in (scope.artifact, scope.phase, scope.condition, c.object) if v)
    )
    if not rest <= covered:
        return None
    allowed = {normalize_term(o) for o in term.objects or ()}
    if (
        c.object is not None
        and term.objects is not None
        and normalize_term(c.object) not in allowed
    ):
        return None
    return term.name


def apply_vocabulary(constraints: list[Constraint]) -> tuple[list[Constraint], list[str]]:
    """Deterministic fixes from the vocabulary (resolve/vocabulary.py), with a note each.

    - Negative subject + positive directive + a removal verb on the evidence line ("Strip
      trailing whitespace") is a misread ban: require -> forbid, prefer -> avoid. Without a
      removal verb the directive is kept: "Always begin by restating the question" really
      requires a preamble. Negations are not cues ("don't skip the preamble").
    - Artifact `any` becomes the subject's (or subject + object's) implied artifact; an
      explicit artifact is never overridden.
    - A condition that reads like a clause ("when fixing a bug", "if they make the output
      friendlier") becomes null; other conditions are kept.
    - A free-text subject that contains a vocabulary term becomes the term when its other
      words are already in the scope or object ("test logging" with artifact `tests` ->
      `logging`). Otherwise it stays free text: "request body logging" is narrower than
      `logging`, and normalizing it would turn it into a blanket ban."""
    out, notes = [], []
    for c in constraints:
        line = c.evidence.line_no
        if (normalized := _normalized_subject(c)) is not None:
            notes.append(
                f"line {line}: subject {c.subject!r} -> `{normalized}` "
                "(remaining words are in the scope)"
            )
            c = c.model_copy(update={"subject": normalized})
        term = lookup(c.subject)
        condition = c.scope.condition
        if condition is not None and condition_is_clause(condition):
            notes.append(f"line {line}: condition {condition!r} -> null (reads like a clause)")
            c = c.model_copy(update={"scope": c.scope.model_copy(update={"condition": None})})
        negative = term is not None and term.polarity == "negative"
        if negative and c.directive in _FLIP and (cue := _REMOVAL.search(c.evidence.text)):
            directive, strength = _FLIP[c.directive]
            notes.append(
                f"line {line}: {c.directive} -> {directive} "
                f"(`{term.name}` is negative; {cue.group(0).lower()!r})"
            )
            c = c.model_copy(update={"directive": directive, "strength": strength})
        artifact = implied_artifact(term, c.object)
        if artifact is not None and c.scope.artifact == "any":
            on = f" {c.object}" if c.object and term.object_artifacts else ""
            notes.append(f"line {line}: artifact any -> {artifact} (implied by `{term.name}`{on})")
            c = c.model_copy(update={"scope": c.scope.model_copy(update={"artifact": artifact})})
        out.append(c)
    return out, notes


def merge_per_line(constraints: list[Constraint]) -> tuple[list[Constraint], list[Dropped]]:
    """At most one constraint per evidence line. Exact duplicates collapse; otherwise the
    constraint about a vocabulary term wins, else the first one emitted. Order is kept.

    Splitting one line into several constraints breaks duplicate detection (the extra
    constraint makes two equal skills unequal) and invents relations."""
    by_line: dict[int, list[Constraint]] = {}
    for c in constraints:
        by_line.setdefault(c.evidence.line_no, []).append(c)
    keep: dict[int, Constraint] = {}
    for line_no, group in by_line.items():
        keep[line_no] = next((c for c in group if lookup(c.subject) is not None), group[0])
    kept, dropped, seen = [], [], set()
    for c in constraints:
        line_no = c.evidence.line_no
        primary = keep[line_no]
        if c is primary and line_no not in seen:
            kept.append(c)
            seen.add(line_no)
        elif c.model_dump(exclude={"id"}) == primary.model_dump(exclude={"id"}):
            reason = f"merged: duplicate of the constraint kept on line {line_no}"
            dropped.append(Dropped(constraint=c.model_dump(mode="json"), reason=reason))
        else:
            reason = f"merged: one constraint per line; kept `{primary.subject}` on line {line_no}"
            dropped.append(Dropped(constraint=c.model_dump(mode="json"), reason=reason))
    return kept, dropped


# --- extractor ---------------------------------------------------------------------------------


@dataclass
class Completion:
    """One provider-neutral model response. `stop_reason` is normalized to `end_turn`,
    `max_tokens` or `refusal` where the provider has an equivalent."""

    text: str
    stop_reason: str | None
    usage: Usage
    refusal: str | None = None  # refusal category or message, when stop_reason == "refusal"


class ExtractBackend(Protocol):
    """A model API behind the extractor (implementations in ingest/backends.py)."""

    @property
    def key(self) -> str:
        """ "provider/model": the extract cache key and the PRICES key."""
        ...

    def complete(self, system: str, messages: list[dict[str, str]], schema: dict) -> Completion:
        """Send system + user/assistant text messages; constrain output to `schema`."""
        ...


class MissingCredentials(RuntimeError):
    pass


def constraint_vocabulary_errors(constraints: list[Constraint]) -> list[str]:
    """Objects outside a closed vocabulary term's allowed list (§1.1)."""
    errors = []
    for i, c in enumerate(constraints):
        term = lookup(c.subject)
        if term is None or term.objects is None or c.object is None:
            continue
        if normalize_term(c.object) in {normalize_term(o) for o in term.objects}:
            continue
        allowed = ", ".join(f'"{o}"' for o in term.objects) or "(none)"
        errors.append(
            f"constraints[{i}] (line {c.evidence.line_no}): object {c.object!r} is not allowed "
            f"for subject `{term.name}`. Allowed objects: {allowed}, or null. If the rule "
            f"targets something narrower than these, use a more specific free-text subject "
            f"instead of `{term.name}`."
        )
    return errors


def vocabulary_errors(result: ExtractResult) -> list[str]:
    return constraint_vocabulary_errors(result.constraints)


def _validate(text: str, last_attempt: bool = False) -> tuple[ExtractResult, list[str], list]:
    """(result, clause-split notes, constraints dropped for long subjects)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON: {exc}") from exc
    context: dict = {"notes": [], "dropped": [], "drop_long_subjects": last_attempt}
    try:
        result = ExtractResult.model_validate(data, context=context)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    if errors := vocabulary_errors(result):
        raise ValueError("\n".join(errors))
    return result, context["notes"], context["dropped"]


@dataclass
class Extractor:
    backend: ExtractBackend

    @property
    def model(self) -> str:
        return self.backend.key

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

        messages: list[dict[str, str]] = [{"role": "user", "content": numbered(text)}]
        for attempt_no in (1, 2):
            reply = self.backend.complete(system_prompt(), messages, response_schema())
            out = reply.text
            attempt = Attempt(stop_reason=reply.stop_reason, text=out, usage=reply.usage)
            record.attempts.append(attempt)
            if reply.stop_reason == "refusal":
                attempt.error = record.error = f"refused ({reply.refusal or 'no category'})"
                return record
            try:
                result, split, too_long = _validate(out, last_attempt=attempt_no == 2)
            except ValueError as exc:
                attempt.error = record.error = str(exc)
                if attempt_no == 1:
                    messages += [
                        {"role": "assistant", "content": out or "(no output)"},
                        {
                            "role": "user",
                            "content": "That output failed validation:\n"
                            f"{exc}\n\nReturn the complete corrected JSON object.",
                        },
                    ]
                continue
            lines = text.split("\n")
            result, record.dropped, record.repaired = verify_evidence(result, lines)
            adjusted, record.adjusted = apply_vocabulary(record_sections(result.constraints, lines))
            record.adjusted = split + record.adjusted
            kept, merged = merge_per_line(adjusted)
            record.result = result.model_copy(update={"constraints": kept})
            record.dropped = too_long + record.dropped + merged
            record.status, record.error = "ok", None
            return record
        return record
