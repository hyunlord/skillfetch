"""`skillfetch scan <dir>`: lint + injection scan + dedup-by-hash + pairwise constraint
analysis over a local skills directory (index-format.md §5).

Constraints come from, in order: a `constraints.json` next to SKILL.md, the index (a skill
with the same content hash, e.g. an installed copy of a public skill), the extract cache,
and, with an extractor, a fresh extraction. Every evidence line is checked against the
local SKILL.md whatever the source."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from skillfetch.index.loader import Index
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.ingest import run_extractions
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
from skillfetch.resolve.relation import Relation, candidate_pairs, mark_fan_out, skill_relation
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
    constraints_source: Literal["sidecar", "index", "cache", "extracted", "none", "invalid"]
    constraints_error: str | None = None
    constraints_note: str | None = None  # why a skill has no constraints, when known
    index_id: str | None = None  # the indexed skill with the same content
    constraint_count: int = 0


class DuplicateGroup(BaseModel):
    content_hash: str
    ids: list[str]


class ScanReport(BaseModel):
    root: str
    index: str | None = None  # "<path> (<n> skills, extraction <model>)" when one was read
    scan_rules_version: int
    skills: list[SkillScan]
    duplicates: list[DuplicateGroup]
    findings: list[Finding]
    analyzed: list[str]
    skipped: list[str]
    # tension / needs_review pairs of two indexed skills that the judge stored as
    # independent (constraints.md §8): not shown, as in resolve_set
    suppressed_by_judge: int = 0


def _skill_id(root: Path, skill_dir: Path) -> str:
    return skill_dir.name if skill_dir == root else skill_dir.relative_to(root).as_posix()


def check_evidence(skill_dir: Path, constraints: list[Constraint]) -> None:
    """Raises ValueError unless every evidence line appears verbatim on its line of
    SKILL.md: a quote that cannot be found is not evidence."""
    lines = read_text(skill_dir / SKILL_FILE).split("\n")
    for c in constraints:
        ln = c.evidence.line_no
        if ln > len(lines) or c.evidence.text not in lines[ln - 1]:
            raise ValueError(f"evidence {c.evidence.text!r} not found on line {ln} of SKILL.md")


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
    check_evidence(skill_dir, constraints)
    return constraints


@dataclass
class Lookup:
    """Constraints for skills without a constraints.json: the index by content hash, then
    the extract cache under `model`, then `extractor` (skills that pass lint and the
    injection scan only). All optional."""

    index: Index | None = None
    cache: ExtractCache | None = None
    model: str | None = None
    extractor: Extractor | None = None
    jobs: int = 4
    _by_hash: dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self):
        if self.index is not None:
            # prefer a record that has constraints (a canonical copy) over one that has none
            for rid, r in sorted(
                self.index.records.items(), key=lambda kv: not self.index.constraints.get(kv[0])
            ):
                self._by_hash.setdefault(r["content_hash"], rid)

    def from_index(self, digest: str, skill_id: str) -> tuple[str, list[Constraint]] | None:
        rid = self._by_hash.get(digest)
        if rid is None:
            return None
        return rid, _renumbered(skill_id, self.index.constraints.get(rid, []))

    def index_note(self, rid: str) -> str:
        r = self.index.records[rid]
        reason = r.get("not_extracted_reason") or r.get("status")
        return f"in the index as {rid}, not extracted: {reason}"


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
    return record, constraints


def _renumbered(skill_id: str, constraints: list[Constraint]) -> list[Constraint]:
    return [c.model_copy(update={"id": f"{skill_id}#c{i}"}) for i, c in enumerate(constraints, 1)]


def _checked(
    record: SkillScan, skill_dir: Path, source: str, constraints: list[Constraint]
) -> list[Constraint] | None:
    """The looked-up constraints if their evidence is on the local SKILL.md lines."""
    try:
        check_evidence(skill_dir, constraints)
    except ValueError as exc:
        record.constraints_source, record.constraints_error = "invalid", str(exc)
        return None
    record.constraints_source, record.constraint_count = source, len(constraints)
    return constraints


def _lookup(lookup: Lookup, record: SkillScan, skill_dir: Path) -> list[Constraint] | None:
    """Index, then cache. Sets the record's source and note; None if neither has it."""
    hit = lookup.from_index(record.content_hash, record.id)
    if hit is not None:
        record.index_id, constraints = hit
        if constraints:
            return _checked(record, skill_dir, "index", constraints)
        record.constraints_note = lookup.index_note(record.index_id)
    if lookup.cache is not None and lookup.model:
        cached = lookup.cache.get(record.content_hash, lookup.model)
        if cached is not None and cached.status != "ok":
            record.constraints_note = (
                record.constraints_note or f"cached extraction: {cached.status}"
            )
        elif cached is not None:
            constraints = _renumbered(record.id, cached.result.constraints)
            return _checked(record, skill_dir, "cache", constraints)
    return None


def _extract(
    lookup: Lookup, todo: list[tuple[SkillScan, Path]], found: dict[str, list[Constraint]]
) -> None:
    """Extract the skills no lookup found (lint and injection scan passed), once each."""
    errors: dict[str, str] = {}
    fresh = run_extractions(
        [(d, r.id, r.content_hash) for r, d in todo],
        lookup.cache or ExtractCache(),
        lookup.extractor,
        lookup.jobs,
        errors,
    )
    for record, skill_dir in todo:
        got = fresh.get(record.content_hash)
        if got is None:
            error = errors.get(record.content_hash, "no result")
            record.constraints_note = (
                "queued for Claude Code; rerun once answered"
                if error.startswith("PendingAnswer")
                else f"extraction failed: {error}"
            )
        elif got.status != "ok":
            record.constraints_note = f"extraction: {got.status}"
        else:
            constraints = _renumbered(record.id, got.result.constraints)
            if (checked := _checked(record, skill_dir, "extracted", constraints)) is not None:
                found[record.id] = checked


def pair_finding(a: Skill, b: Skill) -> Finding | None:
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


def _judged(
    findings: list[Finding], records: list[SkillScan], lookup: Lookup | None
) -> tuple[list[Finding], int]:
    """Drop tension / needs_review findings between two skills taken from the index whose
    pair the judge stored as independent; return the rest and the number dropped."""
    if lookup is None or lookup.index is None or not lookup.index.pairs:
        return findings, 0
    verdicts = lookup.index.verdicts()
    indexed = {r.id: r.index_id for r in records if r.constraints_source == "index"}
    kept = [
        f
        for f in findings
        if f.kind not in ("tension", "needs_review")
        or f.a not in indexed
        or f.b not in indexed
        or verdicts.get(frozenset((indexed[f.a], indexed[f.b]))) != "independent"
    ]
    return kept, len(findings) - len(kept)


def scan_dir(root: Path, lookup: Lookup | None = None) -> ScanReport:
    records: list[SkillScan] = []
    found: dict[str, list[Constraint]] = {}
    todo: list[tuple[SkillScan, Path]] = []
    for skill_dir in discover_skills(root):
        record, constraints = _scan_one(root, skill_dir)
        records.append(record)
        if constraints is None and lookup is not None and record.constraints_source == "none":
            constraints = _lookup(lookup, record, skill_dir)
            unresolved = constraints is None and record.constraints_source == "none"
            if unresolved and record.status == "scan_failed" and not record.constraints_note:
                record.constraints_note = "fails the injection scan, so it is never extracted"
            if unresolved and lookup.extractor is not None and record.status == "ok":
                todo.append((record, skill_dir))
        if constraints is not None and record.status != "lint_failed":
            found[record.id] = constraints
    if todo:
        _extract(lookup, todo, found)

    analyzable = [Skill(id=r.id, constraints=found[r.id]) for r in records if r.id in found]
    # fan-out flags the corpus set on index constraints stay set (constraints.md §3 row
    # 14a): a handful of local skills cannot show that a rule fights half the corpus
    corpus_hubs = {
        c.id
        for r in records
        if r.constraints_source == "index"
        for c in found.get(r.id, [])
        if c.fan_out
    }

    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in records:
        by_hash[r.content_hash].append(r.id)
    duplicates = [
        DuplicateGroup(content_hash=h, ids=ids) for h, ids in by_hash.items() if len(ids) > 1
    ]
    same_content = {frozenset(p) for g in duplicates for p in combinations(g.ids, 2)}

    analyzable = [
        s.model_copy(
            update={
                "constraints": [
                    c.model_copy(update={"fan_out": c.fan_out or c.id in corpus_hubs})
                    for c in s.constraints
                ]
            }
        )
        for s in mark_fan_out(analyzable)
    ]
    findings = [
        f
        for i, j in candidate_pairs(analyzable)
        if frozenset((analyzable[i].id, analyzable[j].id)) not in same_content
        and (f := pair_finding(analyzable[i], analyzable[j])) is not None
    ]
    findings, suppressed = _judged(findings, records, lookup)
    findings.sort(key=lambda f: (_KIND_ORDER[f.kind], f.a, f.b))
    analyzed = {s.id for s in analyzable}
    index = None
    if lookup is not None and lookup.index is not None:
        idx = lookup.index
        where, home = str(idx.root.resolve()), str(Path.home())
        where = "~" + where[len(home) :] if where.startswith(home + "/") else str(idx.root)
        index = (
            f"{where} ({len(idx.records)} skills, extraction "
            f"{idx.manifest.get('extract_model', '?')})"
        )
    return ScanReport(
        root=str(root),
        index=index,
        scan_rules_version=load_rules().version,
        skills=records,
        duplicates=duplicates,
        findings=findings,
        analyzed=sorted(analyzed),
        suppressed_by_judge=suppressed,
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


def _sources(report: ScanReport) -> str:
    names = {
        "sidecar": CONSTRAINTS_FILE,
        "index": "index",
        "cache": "extract cache",
        "extracted": "extracted now",
    }
    counts = defaultdict(int)
    analyzed = set(report.analyzed)
    for s in report.skills:
        if s.id in analyzed:
            counts[s.constraints_source] += 1
    parts = [f"{names[k]} {n}" for k, n in counts.items() if k in names]
    return f" ({', '.join(parts)})" if parts else ""


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
        f"constraints: {len(report.analyzed)} analyzed"
        + _sources(report)
        + f", {len(report.skipped)} skipped",
    ]
    if report.index is not None:
        out.append(f"index: {report.index}")
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
            where = (
                CONSTRAINTS_FILE
                if (Path(s.path) / CONSTRAINTS_FILE).is_file()
                else (s.index_id or s.constraints_source)
            )
            blocks.append(f"INVALID_CONSTRAINTS  {s.id}\n  {where}: {s.constraints_error}")
    for g in report.duplicates:
        first, *rest = g.ids
        for other in rest:
            blocks.append(
                f"DUPLICATE  {first} ⟷ {other}  identical content sha256:{g.content_hash[:12]}"
            )
    blocks += [render_finding(f) for f in report.findings]
    if report.skipped:
        by_id = {s.id: s for s in skills}
        lines = [f"constraint analysis skipped for {_plural(len(report.skipped), 'skill')}:"]
        unknown = False
        for sid in report.skipped:
            note = by_id[sid].constraints_note or by_id[sid].constraints_error
            unknown |= note is None
            lines.append(
                f"  {sid}  ({note or f'no {CONSTRAINTS_FILE}, not in the index or the cache'})"
            )
        if unknown:
            get_index = (
                "get the public index with `skillfetch sync`; " if report.index is None else ""
            )
            lines.append(
                f"  {get_index}extract the others with `--with-api --model anthropic/<model>` "
                "(calls the API)"
            )
        blocks.append("\n".join(lines))

    if report.suppressed_by_judge:
        blocks.append(
            f"{_plural(report.suppressed_by_judge, 'tension / needs_review pair')} not shown: "
            "the index's judge verdict for the pair is `independent`"
        )

    counts = {k: sum(f.kind == k for f in report.findings) for k in _KIND_ORDER}
    summary = (
        f"summary: {counts['conflict']} conflict, {counts['redundant']} redundant, "
        f"{counts['tension']} tension, {counts['needs_review']} needs_review, "
        f"{sum(len(g.ids) - 1 for g in report.duplicates)} duplicate, "
        f"{len(lint_failed)} lint_failed, {len(scan_failed)} scan_failed"
    )
    return "\n\n".join(["\n".join(out), *blocks, summary]) + "\n"
