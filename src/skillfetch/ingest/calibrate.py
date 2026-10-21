"""Calibration: compare extracted constraints with the hand-labelled fixtures.

Two numbers. Field agreement aligns extracted constraints to labelled ones by evidence line
and compares field by field. Pair-relation accuracy runs the resolve/ rules on the extracted
constraints for every pair of fixture skills and compares the resulting relation with
expected.yaml — the number that matters: fields may differ as long as relations do not.

Gates (constraints.md §2):
- hard: conflict precision must be 1.0 — one false conflict fails calibration (exit 1);
- soft: informative-pair accuracy should reach 0.85 — reported, does not fail the run.

Informative pairs are those where the hand label or the extracted relation is not
`independent`. Most fixture pairs are independent (787 of 820), so accuracy over all pairs is
~0.96 for an extractor that extracts nothing; over informative pairs it is 0. Such an
extractor flags no conflict, so its conflict precision is vacuously 1.0: the hard gate does
not catch it, the soft target does.
"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from pathlib import Path

import yaml
from pydantic import BaseModel

from skillfetch.ingest.extract import ExtractRecord
from skillfetch.ingest.local_scan import load_sidecar
from skillfetch.ingest.skillfile import discover_skills
from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.relation import Relation, normalize_term, pair_label, skill_relation
from skillfetch.resolve.report import render_finding
from skillfetch.resolve.resolver import make_finding

HARD_CONFLICT_PRECISION = 1.0
SOFT_TARGET = 0.85
LABEL_KEYS = ("conflict", "redundant", "subsumes", "tension", "needs_review")
FIELDS = (
    "subject",
    "directive",
    "object",
    "scope",
    "strength",
    "artifact",
    "phase",
    "condition",
    "direction",
)


# --- labels ----------------------------------------------------------------------------------


def load_labels(path: Path) -> dict[frozenset[str], str]:
    """expected.yaml → {unordered pair: label}; `subsumes` entries become
    "subsumes:<superset>". Unlisted pairs are `independent`."""
    raw = yaml.safe_load(path.read_text()) or {}
    labels: dict[frozenset[str], str] = {}
    for key in LABEL_KEYS:
        for a, b in raw.get(key) or []:
            pair = frozenset((a, b))
            if len(pair) != 2:
                raise ValueError(f"{path}: self-pair {a}")
            if pair in labels:
                raise ValueError(f"{path}: pair listed twice: {a}, {b}")
            labels[pair] = f"subsumes:{a}" if key == "subsumes" else key
    return labels


def load_labelled(skills_dir: Path) -> dict[str, Skill]:
    """Hand-labelled fixture skills (constraints.json next to each SKILL.md)."""
    return {
        d.name: Skill(id=d.name, constraints=load_sidecar(d, d.name))
        for d in discover_skills(skills_dir)
    }


# --- reports -----------------------------------------------------------------------------------


class Agreement(BaseModel):
    matches: int = 0
    total: int = 0

    @property
    def rate(self) -> float:
        return self.matches / self.total if self.total else 1.0


class FieldReport(BaseModel):
    labelled: int
    extracted: int
    aligned: int
    per_field: dict[str, Agreement]
    missed: list[tuple[str, Constraint]]
    extra: list[tuple[str, Constraint]]


class Mismatch(BaseModel):
    a: str
    b: str
    expected: str
    got: str


class PairReport(BaseModel):
    total: int
    correct: int
    informative_total: int
    informative_correct: int
    labelled_total: int  # pairs whose hand label is not independent
    labelled_correct: int
    false_positives: int  # labelled independent, extracted as anything else
    by_label: dict[str, Agreement]
    conflict_flagged: int
    conflict_true_positives: int
    conflict_expected: int
    mismatches: list[Mismatch]

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 1.0

    @property
    def conflict_precision(self) -> float:
        """1.0 when nothing is flagged (vacuous)."""
        if not self.conflict_flagged:
            return 1.0
        return self.conflict_true_positives / self.conflict_flagged

    @property
    def recall(self) -> float:
        return self.labelled_correct / self.labelled_total if self.labelled_total else 1.0

    @property
    def informative_accuracy(self) -> float:
        if not self.informative_total:
            return 1.0
        return self.informative_correct / self.informative_total


class Calibration(BaseModel):
    fields: FieldReport
    pairs: PairReport
    failed: list[str]
    missing: list[str]
    labelled: dict[str, Skill]
    extracted: dict[str, Skill]

    @property
    def hard_pass(self) -> bool:
        return self.pairs.conflict_precision >= HARD_CONFLICT_PRECISION

    @property
    def soft_pass(self) -> bool:
        return self.pairs.informative_accuracy >= SOFT_TARGET

    @property
    def passed(self) -> bool:
        """Only the hard gate decides; the soft target is reported."""
        return self.hard_pass


# --- comparison -----------------------------------------------------------------------------


def _norm(value: str | None) -> str | None:
    return normalize_term(value) if value is not None else None


def _field_values(c: Constraint) -> dict[str, object]:
    scope = (c.scope.artifact, c.scope.phase, _norm(c.scope.condition))
    return {
        "subject": normalize_term(c.subject),
        "directive": c.directive,
        "object": _norm(c.object),
        "scope": scope,
        "strength": c.strength,
        "artifact": c.scope.artifact,
        "phase": c.scope.phase,
        "condition": scope[2],
        "direction": c.direction,
    }


def _agreeing(a: Constraint, b: Constraint) -> int:
    va, vb = _field_values(a), _field_values(b)
    return sum(va[f] == vb[f] for f in FIELDS)


def compare_fields(labelled: Mapping[str, Skill], extracted: Mapping[str, Skill]) -> FieldReport:
    per_field = {f: Agreement() for f in FIELDS}
    missed: list[tuple[str, Constraint]] = []
    extra: list[tuple[str, Constraint]] = []
    aligned = n_extracted = 0
    for sid, skill in labelled.items():
        remaining = list(extracted[sid].constraints) if sid in extracted else []
        n_extracted += len(remaining)
        for want in skill.constraints:
            same_line = [c for c in remaining if c.evidence.line_no == want.evidence.line_no]
            if not same_line:
                missed.append((sid, want))
                continue
            got = max(same_line, key=lambda c: _agreeing(want, c))
            remaining.remove(got)
            aligned += 1
            vw, vg = _field_values(want), _field_values(got)
            for f in FIELDS:
                per_field[f].total += 1
                per_field[f].matches += vw[f] == vg[f]
        extra += [(sid, c) for c in remaining]
    return FieldReport(
        labelled=sum(len(s.constraints) for s in labelled.values()),
        extracted=n_extracted,
        aligned=aligned,
        per_field=per_field,
        missed=missed,
        extra=extra,
    )


def compare_pairs(
    labels: Mapping[frozenset[str], str], extracted: Mapping[str, Skill]
) -> PairReport:
    by_label: dict[str, Agreement] = {}
    mismatches: list[Mismatch] = []
    correct = flagged = true_pos = expected_conflicts = informative = informative_ok = 0
    labelled = labelled_ok = false_positives = 0
    for a, b in combinations(sorted(extracted), 2):
        want = labels.get(frozenset((a, b)), Relation.INDEPENDENT.value)
        got = pair_label(extracted[a], extracted[b])
        bucket = by_label.setdefault(want.split(":", 1)[0], Agreement())
        bucket.total += 1
        flagged += got == "conflict"
        expected_conflicts += want == "conflict"
        true_pos += got == want == "conflict"
        if want != Relation.INDEPENDENT.value or got != Relation.INDEPENDENT.value:
            informative += 1
            informative_ok += got == want
        if want != Relation.INDEPENDENT.value:
            labelled += 1
            labelled_ok += got == want
        elif got != Relation.INDEPENDENT.value:
            false_positives += 1
        if got == want:
            correct += 1
            bucket.matches += 1
        else:
            mismatches.append(Mismatch(a=a, b=b, expected=want, got=got))
    return PairReport(
        total=len(extracted) * (len(extracted) - 1) // 2,
        correct=correct,
        informative_total=informative,
        informative_correct=informative_ok,
        labelled_total=labelled,
        labelled_correct=labelled_ok,
        false_positives=false_positives,
        by_label=dict(sorted(by_label.items())),
        conflict_flagged=flagged,
        conflict_true_positives=true_pos,
        conflict_expected=expected_conflicts,
        mismatches=mismatches,
    )


def calibrate(fixtures_dir: Path, records: Mapping[str, ExtractRecord]) -> Calibration:
    """fixtures_dir holds skills/ and expected.yaml (the layout of tests/fixtures/)."""
    labelled = load_labelled(fixtures_dir / "skills")
    labels = load_labels(fixtures_dir / "expected.yaml")
    extracted = {
        sid: Skill(id=sid, constraints=records[sid].constraints() if sid in records else [])
        for sid in labelled
    }
    return Calibration(
        fields=compare_fields(labelled, extracted),
        pairs=compare_pairs(labels, extracted),
        failed=sorted(s for s in labelled if s in records and records[s].status != "ok"),
        missing=sorted(s for s in labelled if s not in records),
        labelled=labelled,
        extracted=extracted,
    )


# --- rendering -----------------------------------------------------------------------------------


def compact(c: Constraint) -> str:
    out = f"{c.directive} {c.subject}"
    if c.object:
        out += f" [{c.object}]"
    if c.direction:
        out += f" {c.direction}"
    out += f" @{c.scope.artifact}/{c.scope.phase}"
    if c.scope.condition:
        out += f" if {c.scope.condition}"
    return out + f" ({c.strength})"


def _relation_lines(a: Skill, b: Skill) -> set[tuple[str, int]]:
    lines = set()
    for x, y in ((a, b), (b, a)):
        for p in skill_relation(x, y).pairs:
            lines |= {(x.id, p.a.evidence.line_no), (y.id, p.b.evidence.line_no)}
    return lines


def _expected_finding(m: Mismatch, labelled: Mapping[str, Skill]) -> list[str]:
    a, b = labelled[m.a], labelled[m.b]
    if m.expected == "independent":
        return ["  hand labels: independent"]
    if m.expected.startswith("subsumes:"):
        sup = m.expected.split(":", 1)[1]
        a, b = (a, b) if sup == a.id else (b, a)
        rel, kind = skill_relation(a, b), "redundant"
    else:
        rel, kind = skill_relation(a, b), m.expected
    finding = make_finding(kind, rel, a, b)
    return ["  hand labels:"] + ["  " + line for line in render_finding(finding).splitlines()[1:]]


def render_mismatch(m: Mismatch, cal: Calibration) -> str:
    out = [f"MISMATCH  {m.a} ⟷ {m.b}  expected {m.expected}, got {m.got}"]
    out += _expected_finding(m, cal.labelled)
    lines = _relation_lines(cal.labelled[m.a], cal.labelled[m.b]) | _relation_lines(
        cal.extracted[m.a], cal.extracted[m.b]
    )
    out.append("  extracted:")
    for sid, line_no in sorted(lines):
        found = [c for c in cal.extracted[sid].constraints if c.evidence.line_no == line_no]
        shown = [compact(c) for c in found] or ["(nothing extracted on this line)"]
        out += [f"    {sid}:{line_no}  {text}" for text in shown]
    return "\n".join(out)


def render_calibration(cal: Calibration) -> str:
    f, p = cal.fields, cal.pairs
    out = [
        f"constraints: {f.labelled} labelled, {f.extracted} extracted, {f.aligned} aligned "
        f"by evidence line ({len(f.missed)} missed, {len(f.extra)} extra)",
        "field agreement (aligned constraints):",
    ]
    out += [f"  {name:<10} {a.rate:.3f} ({a.matches}/{a.total})" for name, a in f.per_field.items()]
    if cal.failed or cal.missing:
        out.append(f"not extracted: failed {cal.failed or '-'}, missing {cal.missing or '-'}")
    for sid, c in f.missed:
        out.append(f'MISSED  {sid}:{c.evidence.line_no}  {compact(c)}  "{c.evidence.text}"')
    for sid, c in f.extra:
        out.append(f'EXTRA   {sid}:{c.evidence.line_no}  {compact(c)}  "{c.evidence.text}"')
    out += ["", *(render_mismatch(m, cal) + "\n" for m in p.mismatches)]
    out.append("pair relations by expected label:")
    out += [f"  {label:<13} {a.matches}/{a.total}" for label, a in p.by_label.items()]
    recall = p.conflict_true_positives / p.conflict_expected if p.conflict_expected else 1.0
    out.append(
        f"conflict precision {p.conflict_precision:.3f} "
        f"({p.conflict_true_positives}/{p.conflict_flagged} flagged), recall {recall:.3f}"
    )
    out.append(
        f"labelled pairs: recall {p.recall:.3f} ({p.labelled_correct}/{p.labelled_total}), "
        f"false positives {p.false_positives} (of {p.total - p.labelled_total} independent)"
    )
    out.append(f"pair-relation accuracy, all pairs: {p.accuracy:.3f} ({p.correct}/{p.total})")
    out.append(
        f"pair-relation accuracy, informative pairs: {p.informative_accuracy:.3f} "
        f"({p.informative_correct}/{p.informative_total})"
    )
    out.append(
        f"gate: conflict precision {p.conflict_precision:.3f} (hard, must be "
        f"{HARD_CONFLICT_PRECISION:.1f}): {'PASS' if cal.hard_pass else 'FAIL'} · "
        f"informative-pair accuracy {p.informative_accuracy:.3f} (soft target "
        f"{SOFT_TARGET:.2f}): {'met' if cal.soft_pass else 'MISSED'}"
    )
    return "\n".join(out)
