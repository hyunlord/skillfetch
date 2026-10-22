"""resolve_set: build a conflict-free skill set (constraints.md §5)."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from skillfetch.resolve.models import (
    EvidencePair,
    Excluded,
    Finding,
    FindingKind,
    Quote,
    Resolution,
    Skill,
)
from skillfetch.resolve.relation import ConstraintPair, Relation, SkillRelation, skill_relation

_WARN_ON = (Relation.TENSION, Relation.NEEDS_REVIEW)


def _narrower(x: str, y: str) -> str:
    return y if x == "any" else x


def _subject(pair: ConstraintPair) -> str:
    c = pair.a
    if c.directive == "order":
        first, second = (c.subject, c.object) if c.direction == "before" else (c.object, c.subject)
        return f"order: {first} before {second}"
    return c.subject


def _evidence(rel: SkillRelation, a: Skill, b: Skill) -> list[EvidencePair]:
    return [
        EvidencePair(
            subject=_subject(p),
            artifact=_narrower(p.a.scope.artifact, p.b.scope.artifact),
            phase=_narrower(p.a.scope.phase, p.b.scope.phase),
            a=Quote(skill_id=a.id, line_no=p.a.evidence.line_no, text=p.a.evidence.text),
            b=Quote(skill_id=b.id, line_no=p.b.evidence.line_no, text=p.b.evidence.text),
        )
        for p in rel.pairs
    ]


def make_finding(kind: FindingKind, rel: SkillRelation, a: Skill, b: Skill) -> Finding:
    return Finding(kind=kind, a=a.id, b=b.id, evidence=_evidence(rel, a, b))


def set_id_for(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()[:12]


def resolve_set(
    auto: Sequence[Skill],
    pinned: Sequence[Skill] = (),
    verdicts: Mapping[frozenset[str], str] | None = None,
) -> Resolution:
    """Keep every pinned skill; add auto candidates in order unless they conflict
    with or duplicate a skill already in the set. Never re-ranks, only removes.

    `verdicts` (judge verdict per unordered pair, from the index's pairs.jsonl) only
    suppresses tension / needs_review warnings read as `independent`; they are counted in
    `suppressed_by_judge`. A judge never turns anything into a conflict or an exclusion."""
    verdicts = verdicts or {}
    suppressed = 0
    seen: set[str] = set()
    included: list[Skill] = []
    for skill in pinned:
        if skill.id not in seen:
            seen.add(skill.id)
            included.append(skill)

    warnings: list[Finding] = []
    for i, a in enumerate(included):
        for b in included[i + 1 :]:
            rel = skill_relation(a, b)
            if rel.relation == Relation.CONFLICT:
                warnings.append(make_finding("conflict", rel, a, b))

    excluded: list[Excluded] = []
    for cand in auto:
        if cand.id in seen:
            continue
        seen.add(cand.id)
        rels = [(s, skill_relation(s, cand)) for s in included]
        blocker = next((x for x in rels if x[1].relation == Relation.CONFLICT), None) or next(
            (x for x in rels if x[1].relation == Relation.REDUNDANT), None
        )
        if blocker is not None:
            winner, rel = blocker
            excluded.append(
                Excluded(
                    id=cand.id,
                    reason="conflict" if rel.relation == Relation.CONFLICT else "redundant_with",
                    conflicts_with=winner.id,
                    evidence=_evidence(rel, winner, cand),
                )
            )
            continue
        included.append(cand)
        for s, r in rels:
            if r.relation not in _WARN_ON:
                continue
            if verdicts.get(frozenset((s.id, cand.id))) == "independent":
                suppressed += 1
                continue
            warnings.append(make_finding(r.relation.value, r, s, cand))

    ids = [s.id for s in included]
    return Resolution(
        set_id=set_id_for(ids),
        included=ids,
        excluded=excluded,
        warnings=warnings,
        precedence=list(ids),
        suppressed_by_judge=suppressed,
    )
