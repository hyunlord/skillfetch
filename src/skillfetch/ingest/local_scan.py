"""`skillfetch scan <dir>`: lint + injection scan + dedup-by-hash + pairwise constraint
analysis over a local skills directory (index-format.md §5)."""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from skillfetch.ingest.injection import ScanResult, load_rules, scan_skill
from skillfetch.ingest.lint import LintResult, lint_skill
from skillfetch.ingest.skillfile import (
    CONSTRAINTS_FILE,
    SKILL_FILE,
    content_hash,
    discover_skills,
    read_skill,
    read_text,
)
from skillfetch.resolve.models import Constraint, Finding, Skill
from skillfetch.resolve.relation import Relation, skill_relation
from skillfetch.resolve.report import render_finding
from skillfetch.resolve.resolver import make_finding

_KIND_ORDER = {"conflict": 0, "redundant": 1, "tension": 2, "needs_review": 3}


class SkillScan(BaseModel):
    id: str
    path: str
    name: str | None
    content_hash: str
    status: Literal["ok", "lint_failed", "scan_failed"]
    lint: LintResult
    scan: ScanResult
    constraints_source: Literal["sidecar", "none", "invalid"]
    constraints_error: str | None = None
    constraint_count: int = 0


class DuplicateGroup(BaseModel):
    content_hash: str
    ids: list[str]


class ScanReport(BaseModel):
    root: str
    scan_rules_version: int
    skills: list[SkillScan]
    duplicates: list[DuplicateGroup]
    findings: list[Finding]
    analyzed: list[str]
    skipped: list[str]


def _skill_id(root: Path, skill_dir: Path) -> str:
    return skill_dir.name if skill_dir == root else skill_dir.relative_to(root).as_posix()


def load_sidecar(skill_dir: Path, skill_id: str) -> list[Constraint]:
    """Pre-extracted constraints next to SKILL.md. Raises ValueError if unusable.

    Every evidence line must appear verbatim on its line of SKILL.md: a quote that
    cannot be found is not evidence."""
    try:
        raw = json.loads((skill_dir / CONSTRAINTS_FILE).read_text())
        constraints = [
            Constraint.model_validate({**c, "id": f"{skill_id}#c{i}"})
            for i, c in enumerate(raw["constraints"], 1)
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
        raise ValueError(f"{CONSTRAINTS_FILE} is not valid: {exc}") from exc
    lines = read_text(skill_dir / SKILL_FILE).split("\n")
    for c in constraints:
        ln = c.evidence.line_no
        if ln > len(lines) or c.evidence.text not in lines[ln - 1]:
            raise ValueError(f"evidence {c.evidence.text!r} not found on line {ln} of SKILL.md")
    return constraints


def _scan_one(root: Path, skill_dir: Path) -> tuple[SkillScan, Skill | None]:
    skill_id = _skill_id(root, skill_dir)
    lint = lint_skill(skill_dir)
    scan = scan_skill(skill_dir)
    status = "lint_failed" if not lint.ok else "scan_failed" if not scan.ok else "ok"
    name = read_skill(skill_dir).frontmatter.get("name") if lint.ok else None

    source, error, constraints = "none", None, None
    if (skill_dir / CONSTRAINTS_FILE).is_file():
        try:
            constraints = load_sidecar(skill_dir, skill_id)
            source = "sidecar"
        except ValueError as exc:
            source, error = "invalid", str(exc)
    record = SkillScan(
        id=skill_id,
        path=str(skill_dir.resolve()),
        name=name,
        content_hash=content_hash(skill_dir),
        status=status,
        lint=lint,
        scan=scan,
        constraints_source=source,
        constraints_error=error,
        constraint_count=len(constraints or []),
    )
    analyzable = constraints is not None and status != "lint_failed"
    return record, Skill(id=skill_id, constraints=constraints) if analyzable else None


def _pair_finding(a: Skill, b: Skill) -> Finding | None:
    forward, backward = skill_relation(a, b), skill_relation(b, a)
    if forward.relation == Relation.CONFLICT:
        return make_finding("conflict", forward, a, b)
    if forward.relation == Relation.REDUNDANT:  # b ⊆ a
        return make_finding("redundant", forward, a, b)
    if backward.relation == Relation.REDUNDANT:  # a ⊆ b
        return make_finding("redundant", backward, b, a)
    if forward.relation in (Relation.TENSION, Relation.NEEDS_REVIEW):
        return make_finding(forward.relation.value, forward, a, b)
    return None


def scan_dir(root: Path) -> ScanReport:
    records: list[SkillScan] = []
    analyzable: list[Skill] = []
    for skill_dir in discover_skills(root):
        record, skill = _scan_one(root, skill_dir)
        records.append(record)
        if skill is not None:
            analyzable.append(skill)

    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in records:
        by_hash[r.content_hash].append(r.id)
    duplicates = [
        DuplicateGroup(content_hash=h, ids=ids) for h, ids in by_hash.items() if len(ids) > 1
    ]
    same_content = {frozenset(p) for g in duplicates for p in combinations(g.ids, 2)}

    findings = [
        f
        for a, b in combinations(analyzable, 2)
        if frozenset((a.id, b.id)) not in same_content and (f := _pair_finding(a, b)) is not None
    ]
    findings.sort(key=lambda f: (_KIND_ORDER[f.kind], f.a, f.b))
    analyzed = {s.id for s in analyzable}
    return ScanReport(
        root=str(root),
        scan_rules_version=load_rules().version,
        skills=records,
        duplicates=duplicates,
        findings=findings,
        analyzed=sorted(analyzed),
        skipped=sorted(r.id for r in records if r.status != "lint_failed" and r.id not in analyzed),
    )


def fail_counts(report: ScanReport) -> dict[str, int]:
    """Counts behind `scan --fail-on`. Per stage, not per status: a skill can fail
    both lint and the injection scan (its status is then lint_failed)."""
    return {
        "conflict": sum(f.kind == "conflict" for f in report.findings),
        "scan": sum(not s.scan.ok for s in report.skills),
        "lint": sum(not s.lint.ok for s in report.skills),
    }


# --- text rendering ------------------------------------------------------------------


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def render_report(report: ScanReport) -> str:
    skills = report.skills
    # Per stage, not per status: a skill can fail both (its status is lint_failed).
    lint_failed = [s for s in skills if not s.lint.ok]
    scan_failed = [s for s in skills if not s.scan.ok]
    with_warnings = [s for s in skills if s.scan.warnings]
    with_scripts = [s for s in skills if s.scan.has_scripts]
    out = [
        f"skillfetch scan {report.root}",
        f"{_plural(len(skills), 'skill')} · lint: {len(skills) - len(lint_failed)} ok, "
        f"{len(lint_failed)} failed · injection scan: {len(skills) - len(scan_failed)} ok, "
        f"{len(scan_failed)} failed, {len(with_warnings)} with warnings · "
        f"scripts: {len(with_scripts)}",
        f"constraints: {len(report.analyzed)} analyzed from {CONSTRAINTS_FILE}, "
        f"{len(report.skipped)} skipped",
    ]
    blocks: list[str] = []

    for s in skills:
        if s.lint.errors or s.lint.warnings:
            label = "LINT_FAILED" if s.lint.errors else "LINT_WARNING"
            lines = [f"{label}  {s.id}"]
            for issue in s.lint.errors + s.lint.warnings:
                where = f"{s.id}/{issue.file}" + (f":{issue.line_no}" if issue.line_no else "")
                lines.append(f"  {where}  [{issue.rule}] {issue.message}")
            blocks.append("\n".join(lines))
    for s in skills:
        for label, hits in (("SCAN_FAILED", s.scan.failures), ("SCAN_WARNING", s.scan.warnings)):
            if hits:
                lines = [f"{label}  {s.id}"]
                lines += [f'  {s.id}/{h.file}:{h.line_no}  [{h.rule_id}] "{h.line}"' for h in hits]
                blocks.append("\n".join(lines))
    for s in with_scripts:
        lines = [f"HAS_SCRIPTS  {s.id}  (tier capped at C unless the publisher is verified)"]
        lines += [f"  {s.id}/{path}" for path in s.scan.scripts]
        blocks.append("\n".join(lines))
    for s in skills:
        if s.constraints_source == "invalid":
            blocks.append(
                f"INVALID_CONSTRAINTS  {s.id}\n  {s.id}/{CONSTRAINTS_FILE}: {s.constraints_error}"
            )
    for g in report.duplicates:
        first, *rest = g.ids
        for other in rest:
            blocks.append(
                f"DUPLICATE  {first} ⟷ {other}  identical content sha256:{g.content_hash[:12]}"
            )
    blocks += [render_finding(f) for f in report.findings]
    if report.skipped:
        blocks.append(
            f"constraint analysis skipped for {_plural(len(report.skipped), 'skill')} without a "
            f"valid {CONSTRAINTS_FILE} (API extraction is not implemented yet): "
            + ", ".join(report.skipped)
        )

    counts = {k: sum(f.kind == k for f in report.findings) for k in _KIND_ORDER}
    summary = (
        f"summary: {counts['conflict']} conflict, {counts['redundant']} redundant, "
        f"{counts['tension']} tension, {counts['needs_review']} needs_review, "
        f"{sum(len(g.ids) - 1 for g in report.duplicates)} duplicate, "
        f"{len(lint_failed)} lint_failed, {len(scan_failed)} scan_failed"
    )
    return "\n\n".join(["\n".join(out), *blocks, summary]) + "\n"
