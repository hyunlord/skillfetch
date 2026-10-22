"""Constraint schema (constraints.md §1) and the resolve/ input and output types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Directive = Literal["require", "forbid", "prefer", "avoid", "order"]
Strength = Literal["must", "should"]
Artifact = Literal[
    "code", "tests", "commit-message", "pr-description", "markdown", "response", "plan", "any"
]
Phase = Literal["plan", "implement", "test", "review", "format", "any"]

_DEFAULT_STRENGTH: dict[str, Strength] = {
    "require": "must",
    "forbid": "must",
    "prefer": "should",
    "avoid": "should",
}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Scope(_Frozen):
    artifact: Artifact = "any"
    phase: Phase = "any"
    condition: str | None = None


class Evidence(_Frozen):
    line_no: int = Field(ge=1)
    text: str

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("evidence text must quote a non-empty source line")
        return v


class Constraint(_Frozen):
    id: str = ""
    subject: str = Field(min_length=1)
    directive: Directive
    object: str | None = None
    # The object in the line's own words, kept even when `object` is null or a vocabulary
    # value. For review only: never part of identity or of any relation.
    object_raw: str | None = None
    direction: Literal["before", "after"] | None = None  # `order` only: subject vs object
    scope: Scope = Scope()
    strength: Strength  # derived from directive when omitted (§1); `order` defaults to must
    evidence: Evidence
    # The markdown heading the evidence line falls under, filled after extraction. Review
    # only: not part of identity.
    section_heading: str | None = None
    # Set over a whole corpus (relation.mark_fan_out): this constraint conflicts with three
    # or more distinct skills, so its conflicts are capped at needs_review. Not identity.
    fan_out: bool = False

    @field_validator("subject", "object")
    @classmethod
    def _stripped(cls, v: str | None, info) -> str | None:
        """Surrounding whitespace is not part of a term; a blank subject or object names
        nothing and is refused (an absent object is null, not "")."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError(f"{info.field_name} is blank")
        return v

    @model_validator(mode="before")
    @classmethod
    def _derive_strength(cls, data):
        if isinstance(data, dict) and data.get("strength") is None:
            data = {**data, "strength": _DEFAULT_STRENGTH.get(data.get("directive"), "must")}
        return data

    @model_validator(mode="after")
    def _check_order(self):
        if self.directive == "order":
            if not self.object:
                raise ValueError("order constraint needs an object (the other side of the order)")
            if self.direction is None:
                raise ValueError("order constraint needs direction 'before' or 'after'")
        elif self.direction is not None:
            raise ValueError("direction is only allowed on order constraints")
        return self


class Skill(_Frozen):
    """The subset of a skill record (index-format.md §3) that resolve/ needs."""

    id: str
    constraints: list[Constraint] = []
    tags: dict[str, list[str]] = {}
    produces: list[str] = []
    consumes: list[str] = []


# --- resolve_set output (every field is evidence-backed, constraints.md §6) -----------


class Quote(_Frozen):
    skill_id: str
    line_no: int
    text: str


class EvidencePair(_Frozen):
    subject: str
    artifact: str
    phase: str
    a: Quote
    b: Quote


FindingKind = Literal["conflict", "tension", "needs_review", "redundant"]


class Finding(_Frozen):
    """A skill-level relation between `a` (earlier / kept) and `b` (later)."""

    kind: FindingKind
    a: str
    b: str
    evidence: list[EvidencePair] = Field(min_length=1)


class Excluded(_Frozen):
    id: str
    reason: Literal["conflict", "redundant_with"]
    conflicts_with: str
    evidence: list[EvidencePair] = Field(min_length=1)

    def to_finding(self) -> Finding:
        kind: FindingKind = "conflict" if self.reason == "conflict" else "redundant"
        return Finding(kind=kind, a=self.conflicts_with, b=self.id, evidence=self.evidence)


class Resolution(_Frozen):
    set_id: str
    included: list[str]
    excluded: list[Excluded]
    warnings: list[Finding]
    precedence: list[str]
    # tension / needs_review warnings dropped because a judge read the pair as independent
    suppressed_by_judge: int = 0


Verdict = Literal["conflict", "carve_out", "situational", "independent", "unclear"]


class PairVerdict(_Frozen):
    """One line of an index's pairs.jsonl: a judge's reading of a pair the rules left open
    (constraints.md §8). Never changes a conflict or an exclusion; an `independent` verdict
    only removes the pair's tension / needs_review warning."""

    a: str
    b: str
    rules: str  # relation from the rules: needs_review | tension
    row: str  # §3 row behind it
    verdict: Verdict
    reason: str
    ambiguous_together: bool
    confidence: float
    judge: str  # backend/model key
    judge_version: int
    input_sha256: str | None = None

    @property
    def key(self) -> frozenset[str]:
        return frozenset((self.a, self.b))
