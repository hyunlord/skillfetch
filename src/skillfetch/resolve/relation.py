"""Pairwise constraint relations and skill-level relations (constraints.md §3, §4).

Pure functions over pre-extracted constraints. No I/O, no model calls.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.terms import normalize_term
from skillfetch.resolve.vocabulary import choice_of, lookup

__all__ = [
    "ConstraintPair",
    "Relation",
    "SkillRelation",
    "complementary",
    "constraint_relation",
    "normalize_term",
    "pair_label",
    "skill_relation",
]


class Relation(StrEnum):
    CONFLICT = "conflict"
    TENSION = "tension"
    NEEDS_REVIEW = "needs_review"
    REDUNDANT = "redundant"
    INDEPENDENT = "independent"


_POSITIVE = frozenset({"require", "prefer"})


def _norm_opt(text: str | None) -> str | None:
    return normalize_term(text) if text is not None else None


def _overlaps(x: str, y: str) -> bool:
    return x == y or "any" in (x, y)


def _broader(x: str, y: str) -> bool:
    return x == "any" and y != "any"


def scopes_overlap(a: Constraint, b: Constraint) -> bool:
    return _overlaps(a.scope.artifact, b.scope.artifact) and _overlaps(a.scope.phase, b.scope.phase)


def _order_edge(c: Constraint) -> tuple[str, str]:
    """(first, second) for an `order` constraint, independent of before/after phrasing."""
    subject, obj = normalize_term(c.subject), normalize_term(c.object or "")
    return (subject, obj) if c.direction == "before" else (obj, subject)


def _opposed(a: Constraint, b: Constraint) -> Relation:
    both_must = a.strength == "must" and b.strength == "must"
    return Relation.CONFLICT if both_must else Relation.TENSION


def _exclusive_choice(a: Constraint, b: Constraint) -> Relation:
    """Two positive constraints naming different objects on the same subject (§3 rows 8-11)."""
    term = lookup(a.subject)
    if term is None or not term.exclusive:
        return Relation.INDEPENDENT
    choice_a, choice_b = choice_of(term, a.object), choice_of(term, b.object)
    if choice_a is None or choice_b is None:
        return Relation.NEEDS_REVIEW  # unknown or ambiguous choice: cannot tell
    (eco_a, pick_a), (eco_b, pick_b) = choice_a, choice_b
    if eco_a != eco_b or pick_a == pick_b:
        return Relation.INDEPENDENT  # different ecosystems, or the same choice reworded
    if _norm_opt(a.scope.condition) != _norm_opt(b.scope.condition):
        return Relation.NEEDS_REVIEW
    return _opposed(a, b)


def constraint_relation(a: Constraint, b: Constraint) -> Relation:
    """Relation of two constraints from different skills. Symmetric."""
    if a.directive == "order" or b.directive == "order":
        if a.directive != b.directive or not scopes_overlap(a, b):
            return Relation.INDEPENDENT
        edge_a, edge_b = _order_edge(a), _order_edge(b)
        if edge_a == edge_b:
            return Relation.REDUNDANT
        if edge_a == edge_b[::-1]:
            if _norm_opt(a.scope.condition) != _norm_opt(b.scope.condition):
                return Relation.NEEDS_REVIEW
            return _opposed(a, b)
        return Relation.INDEPENDENT

    if normalize_term(a.subject) != normalize_term(b.subject) or not scopes_overlap(a, b):
        return Relation.INDEPENDENT

    obj_a, obj_b = _norm_opt(a.object), _norm_opt(b.object)
    if (a.directive in _POSITIVE) == (b.directive in _POSITIVE):
        if obj_a == obj_b:
            return Relation.REDUNDANT
        if a.directive in _POSITIVE and obj_a is not None and obj_b is not None:
            return _exclusive_choice(a, b)
        return Relation.INDEPENDENT

    pos, neg = (a, b) if a.directive in _POSITIVE else (b, a)
    pos_obj, neg_obj = (obj_a, obj_b) if pos is a else (obj_b, obj_a)
    if neg_obj is not None and neg_obj != pos_obj:
        # The ban is narrower than (or unrelated to) the requirement.
        return Relation.NEEDS_REVIEW if pos_obj is None else Relation.INDEPENDENT
    if _broader(pos.scope.artifact, neg.scope.artifact) or _broader(
        pos.scope.phase, neg.scope.phase
    ):
        # Same carve-out, by scope: "use emoji" + "never in markdown".
        return Relation.NEEDS_REVIEW

    if _norm_opt(a.scope.condition) != _norm_opt(b.scope.condition):
        return Relation.NEEDS_REVIEW
    relation = _opposed(a, b)
    if relation == Relation.CONFLICT and None in (obj_a, obj_b):
        # A hard rule without an object is a blanket statement about the whole subject.
        # Extractors produce those from narrower lines ("Don't swallow errors" ->
        # forbid error-handling), and one of them conflicts with every skill that
        # requires the subject in any form, so it never makes a conflict on its own.
        return Relation.NEEDS_REVIEW
    return relation


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
    """Normalized identity of a constraint, used for multiset containment (§4)."""
    if c.directive == "order":
        return (
            "order",
            _order_edge(c),
            c.scope.artifact,
            c.scope.phase,
            _norm_opt(c.scope.condition),
            c.strength,
        )
    return (
        normalize_term(c.subject),
        c.directive,
        _norm_opt(c.object),
        c.scope.artifact,
        c.scope.phase,
        _norm_opt(c.scope.condition),
        c.strength,
    )


def constraint_identity(c: Constraint) -> tuple:
    """Full normalized identity (§4): equal identities are the same rule in the same scope."""
    return _identity(c)


def _core(c: Constraint) -> tuple:
    """Identity without the scope."""
    if c.directive == "order":
        return ("order", _order_edge(c), c.strength)
    return (normalize_term(c.subject), c.directive, _norm_opt(c.object), c.strength)


def _covers(broad: Constraint, narrow: Constraint) -> bool:
    """The same rule, with `broad`'s scope containing `narrow`'s on every dimension:
    artifact/phase `any` contains any value, no condition contains any condition."""
    if _core(broad) != _core(narrow):
        return False
    a, b = broad.scope, narrow.scope
    return (
        a.artifact in ("any", b.artifact)
        and a.phase in ("any", b.phase)
        and (a.condition is None or _norm_opt(a.condition) == _norm_opt(b.condition))
    )


def _subsumed(kept: Skill, cand: Skill) -> list[ConstraintPair] | None:
    """If every constraint of cand is matched one-to-one by a constraint of kept that is the
    same rule over the same or a broader scope, pair them (dropping cand is lossless).
    cand must be non-empty. Exact matches are taken before broader ones."""
    if not cand.constraints or len(cand.constraints) > len(kept.constraints):
        return None
    remaining = list(kept.constraints)
    pairs = []
    for cb in cand.constraints:
        key = _identity(cb)
        match = next((ca for ca in remaining if _identity(ca) == key), None)
        if match is None:
            match = next((ca for ca in remaining if _covers(ca, cb)), None)
        if match is None:
            return None
        remaining.remove(match)
        pairs.append(ConstraintPair(match, cb, Relation.REDUNDANT))
    return pairs


def skill_relation(a: Skill, b: Skill) -> SkillRelation:
    """Relation of skill `b` given skill `a`, with the constraint pairs that justify it.

    Symmetric except for redundancy, which is directional: `redundant` means b ⊆ a
    (b adds no constraint that a lacks). Ranking: conflict > redundant > tension >
    needs_review > independent.
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
    matched = _subsumed(a, b)
    if matched is not None:
        return SkillRelation(Relation.REDUNDANT, matched)
    for relation in (Relation.TENSION, Relation.NEEDS_REVIEW):
        hits = [p for p in pairs if p.relation == relation]
        if hits:
            return SkillRelation(relation, hits)
    return SkillRelation(Relation.INDEPENDENT)


def pair_label(a: Skill, b: Skill) -> str:
    """Unordered label of a pair, in the vocabulary of tests/fixtures/expected.yaml:
    a symmetric relation's value, or `subsumes:<superset id>` when redundancy holds in one
    direction only."""
    forward, backward = skill_relation(a, b).relation, skill_relation(b, a).relation
    if forward == backward:
        return forward.value
    if (forward, backward) == (Relation.REDUNDANT, Relation.INDEPENDENT):
        return f"subsumes:{a.id}"
    if (forward, backward) == (Relation.INDEPENDENT, Relation.REDUNDANT):
        return f"subsumes:{b.id}"
    return f"asymmetric:{forward.value}/{backward.value}"


def _terms(values: Iterable[str]) -> set[str]:
    return {normalize_term(v) for v in values}


def complementary(a: Skill, b: Skill) -> bool:
    """Hint only (§4): one feeds the other, or same domain at different phases."""
    if _terms(a.produces) & _terms(b.consumes) or _terms(b.produces) & _terms(a.consumes):
        return True
    domains = _terms(a.tags.get("domain", [])) & _terms(b.tags.get("domain", []))
    phase_a, phase_b = _terms(a.tags.get("phase", [])), _terms(b.tags.get("phase", []))
    return bool(domains and phase_a and phase_b and not phase_a & phase_b)
