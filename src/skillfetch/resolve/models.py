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
    scope: Scope = Scope()
    strength: Strength  # derived from directive when omitted (§1); `order` defaults to must
    evidence: Evidence

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
            if self.scope.condition not in ("before", "after"):
                raise ValueError("order constraint needs scope.condition 'before' or 'after'")
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
