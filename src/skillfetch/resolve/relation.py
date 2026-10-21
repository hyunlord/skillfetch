"""Pairwise constraint relations and skill-level relations (constraints.md §3, §4).

Pure functions over pre-extracted constraints. No I/O, no model calls.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.polarity import polarity_uncertain
from skillfetch.resolve.terms import normalize_term
from skillfetch.resolve.vocabulary import choice_of, lookup

__all__ = [
    "ConstraintPair",
    "candidate_pairs",
    "conflict_cap",
    "fan_out_map",
    "mark_fan_out",
    "Relation",
    "SkillRelation",
    "complementary",
    "constraint_relation",
    "normalize_term",
    "pair_label",
    "skill_relation",
]


# Which object-less hard pairs may conflict (§3 row 14d). "all" (the default) caps every
# object-less pair; "vocabulary" lets a blanket rule about a vocabulary term conflict
# ("never use emoji" vs "always use emoji"), which finds 8 more fixture conflicts but left
# one false conflict on the seed-43 build. Set by `--conflict-cap`.
CAP_MODES = ("all", "vocabulary")
OBJECTLESS_CAP = "all"


def set_objectless_cap(mode: str) -> None:
    global OBJECTLESS_CAP
    if mode not in CAP_MODES:
        raise ValueError(f"conflict cap must be one of {CAP_MODES}, got {mode!r}")
    OBJECTLESS_CAP = mode


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
    """Relation of two constraints from different skills. Symmetric. A conflict that
    `conflict_cap` gives a reason for is reported as needs_review (§3 row 14)."""
    relation = _base_relation(a, b)
    if relation == Relation.CONFLICT and conflict_cap(a, b) is not None:
        return Relation.NEEDS_REVIEW
    return relation


def conflict_cap(a: Constraint, b: Constraint) -> str | None:
    """Why a conflict between a and b must not be reported as one, or None (§3 row 14):

    - `fan-out`: one side conflicts with three or more distinct skills of the corpus
      (`mark_fan_out`); a hub is far more likely an extraction error than a real
      contradiction with that many skills;
    - `polarity`: one side's directive is uncertain (`polarity.polarity_uncertain`: under a
      "don't" heading and negated again on its own line);
    - `narrowed`: an object-less side whose `object_raw` names something narrower;
    - `free-text subject`: an object-less hard pair on a subject outside the vocabulary.
      A blanket rule about a vocabulary term ("never use emoji") is well defined; a blanket
      rule about free text ("Don't assume." -> forbid assumptions) is usually a misread.
    """
    if a.fan_out or b.fan_out:
        return "fan-out"
    if polarity_uncertain(a) or polarity_uncertain(b):
        return "polarity"
    if a.directive != "order" and (a.object is None or b.object is None):
        if _narrowed(a) or _narrowed(b):
            return "narrowed"
        if lookup(a.subject) is None and OBJECTLESS_CAP == "vocabulary":
            return "free-text subject"
        if OBJECTLESS_CAP == "all":
            return "object-less"
    return None


def _base_relation(a: Constraint, b: Constraint) -> Relation:
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
    return _opposed(a, b)


def _narrowed(c: Constraint) -> bool:
    """An object-less rule whose line names something narrower than the subject."""
    if c.object is not None or not c.object_raw or not c.object_raw.strip():
        return False
    return normalize_term(c.object_raw) != normalize_term(c.subject)


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


# --- corpus-level: blocking and fan-out --------------------------------------------------


def _keys(c: Constraint) -> tuple:
    if c.directive == "order":
        return ("order", frozenset(_order_edge(c)))
    return ("subject", normalize_term(c.subject))


def candidate_pairs(skills: list[Skill]) -> list[tuple[int, int]]:
    """Index pairs (i < j) of skills that share a subject (or an order edge). Every other
    pair is independent, so corpus-wide comparisons only need these."""
    by_key: dict[tuple, set[int]] = {}
    for i, s in enumerate(skills):
        for c in s.constraints:
            by_key.setdefault(_keys(c), set()).add(i)
    pairs: set[tuple[int, int]] = set()
    for members in by_key.values():
        ordered = sorted(members)
        pairs.update((x, y) for n, x in enumerate(ordered) for y in ordered[n + 1 :])
    return sorted(pairs)


FAN_OUT_SKILLS = 3


def fan_out_map(skills: Mapping[str, Skill]) -> dict[str, Skill]:
    """mark_fan_out over a {skill id: skill} mapping."""
    ids = list(skills)
    return dict(zip(ids, mark_fan_out([skills[i] for i in ids]), strict=True))


def mark_fan_out(skills: list[Skill], threshold: int = FAN_OUT_SKILLS) -> list[Skill]:
    """The skills with `fan_out` set on every constraint that conflicts with `threshold` or
    more distinct skills of the corpus. Skills with identical constraint multisets count
    once (duplicates, index-format §1.6); skills that merely share the conflicting rule are
    distinct. Flags already set are recomputed."""
    clean = [
        s.model_copy(
            update={"constraints": [c.model_copy(update={"fan_out": False}) for c in s.constraints]}
        )
        for s in skills
    ]
    whole = [tuple(sorted(map(repr, map(_identity, s.constraints)))) for s in clean]
    hits: dict[tuple[int, int], set[tuple]] = {}
    for i, j in candidate_pairs(clean):
        for ka, ca in enumerate(clean[i].constraints):
            for kb, cb in enumerate(clean[j].constraints):
                if _keys(ca) != _keys(cb) or constraint_relation(ca, cb) != Relation.CONFLICT:
                    continue
                hits.setdefault((i, ka), set()).add(whole[j])
                hits.setdefault((j, kb), set()).add(whole[i])
    flagged = {key for key, partners in hits.items() if len(partners) >= threshold}
    return [
        s.model_copy(
            update={
                "constraints": [
                    c.model_copy(update={"fan_out": (i, k) in flagged})
                    for k, c in enumerate(s.constraints)
                ]
            }
        )
        for i, s in enumerate(clean)
    ]
