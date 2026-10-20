"""Pairwise constraint relations and skill-level relations (constraints.md §3, §4).

Pure functions over pre-extracted constraints. No I/O, no model calls.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from skillfetch.resolve.models import Constraint, Skill


class Relation(StrEnum):
    CONFLICT = "conflict"
    TENSION = "tension"
    NEEDS_REVIEW = "needs_review"
    REDUNDANT = "redundant"
    INDEPENDENT = "independent"


_POSITIVE = frozenset({"require", "prefer"})
_WORD = re.compile(r"[a-z0-9]+")


def _singular(word: str) -> str:
    if len(word) <= 3 or word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s"):
        return word[:-1]
    return word


def normalize_term(text: str) -> str:
    """Lowercase, collapse whitespace, naive per-word singular, strip edge punctuation."""
    text = re.sub(r"\s+", " ", text.lower()).strip()
    text = _WORD.sub(lambda m: _singular(m.group()), text)
    return text.strip(" .,;:!?")


def _norm_opt(text: str | None) -> str | None:
    return normalize_term(text) if text is not None else None


def _overlaps(x: str, y: str) -> bool:
    return x == y or "any" in (x, y)


def scopes_overlap(a: Constraint, b: Constraint) -> bool:
    return _overlaps(a.scope.artifact, b.scope.artifact) and _overlaps(a.scope.phase, b.scope.phase)


def _order_edge(c: Constraint) -> tuple[str, str]:
    """(first, second) for an `order` constraint, independent of before/after phrasing."""
    subject, obj = normalize_term(c.subject), normalize_term(c.object or "")
    return (subject, obj) if c.scope.condition == "before" else (obj, subject)


def _opposed(a: Constraint, b: Constraint) -> Relation:
    both_must = a.strength == "must" and b.strength == "must"
    return Relation.CONFLICT if both_must else Relation.TENSION


def constraint_relation(a: Constraint, b: Constraint) -> Relation:
    """Relation of two constraints from different skills. Symmetric."""
    if a.directive == "order" or b.directive == "order":
        if a.directive != b.directive or not scopes_overlap(a, b):
            return Relation.INDEPENDENT
        edge_a, edge_b = _order_edge(a), _order_edge(b)
        if edge_a == edge_b:
            return Relation.REDUNDANT
        if edge_a == edge_b[::-1]:
            return _opposed(a, b)
        return Relation.INDEPENDENT

    if normalize_term(a.subject) != normalize_term(b.subject) or not scopes_overlap(a, b):
        return Relation.INDEPENDENT

    obj_a, obj_b = _norm_opt(a.object), _norm_opt(b.object)
    if (a.directive in _POSITIVE) == (b.directive in _POSITIVE):
        return Relation.REDUNDANT if obj_a == obj_b else Relation.INDEPENDENT

    pos_obj, neg_obj = (obj_a, obj_b) if a.directive in _POSITIVE else (obj_b, obj_a)
    if neg_obj is not None and neg_obj != pos_obj:
        # The ban is narrower than (or unrelated to) the requirement.
        return Relation.NEEDS_REVIEW if pos_obj is None else Relation.INDEPENDENT

    if _norm_opt(a.scope.condition) != _norm_opt(b.scope.condition):
        return Relation.NEEDS_REVIEW
    return _opposed(a, b)


@dataclass(frozen=True)
class ConstraintPair:
    a: Constraint
    b: Constraint
    relation: Relation


@dataclass(frozen=True)
class SkillRelation:
    relation: Relation
    pairs: list[ConstraintPair] = field(default_factory=list)


def _identity(c: Constraint) -> tuple:
    """Normalized identity of a constraint, used for multiset equality (§4)."""
    if c.directive == "order":
        return ("order", _order_edge(c), c.scope.artifact, c.scope.phase, c.strength)
    return (
        normalize_term(c.subject),
        c.directive,
        _norm_opt(c.object),
        c.scope.artifact,
        c.scope.phase,
        _norm_opt(c.scope.condition),
        c.strength,
    )


def _multiset_match(a: Skill, b: Skill) -> list[ConstraintPair] | None:
    """Pair up constraints one-to-one if the normalized multisets are equal and non-empty."""
    if not a.constraints or len(a.constraints) != len(b.constraints):
        return None
    remaining = list(b.constraints)
    pairs = []
    for ca in a.constraints:
        key = _identity(ca)
        match = next((cb for cb in remaining if _identity(cb) == key), None)
        if match is None:
            return None
        remaining.remove(match)
        pairs.append(ConstraintPair(ca, match, Relation.REDUNDANT))
    return pairs


def skill_relation(a: Skill, b: Skill) -> SkillRelation:
    """Skill-level relation with the constraint pairs that justify it.

    Ranking: conflict > redundant > tension > needs_review > independent.
    """
    pairs = [
        ConstraintPair(ca, cb, rel)
        for ca in a.constraints
        for cb in b.constraints
        if (rel := constraint_relation(ca, cb)) != Relation.INDEPENDENT
    ]
    conflicts = [p for p in pairs if p.relation == Relation.CONFLICT]
    if conflicts:
        return SkillRelation(Relation.CONFLICT, conflicts)
    matched = _multiset_match(a, b)
    if matched is not None:
        return SkillRelation(Relation.REDUNDANT, matched)
    for relation in (Relation.TENSION, Relation.NEEDS_REVIEW):
        hits = [p for p in pairs if p.relation == relation]
        if hits:
            return SkillRelation(relation, hits)
    return SkillRelation(Relation.INDEPENDENT)


def _terms(values: Iterable[str]) -> set[str]:
    return {normalize_term(v) for v in values}


def complementary(a: Skill, b: Skill) -> bool:
    """Hint only (§4): one feeds the other, or same domain at different phases."""
    if _terms(a.produces) & _terms(b.consumes) or _terms(b.produces) & _terms(a.consumes):
        return True
    domains = _terms(a.tags.get("domain", [])) & _terms(b.tags.get("domain", []))
    phase_a, phase_b = _terms(a.tags.get("phase", [])), _terms(b.tags.get("phase", []))
    return bool(domains and phase_a and phase_b and not phase_a & phase_b)
