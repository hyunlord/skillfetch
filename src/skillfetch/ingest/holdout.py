"""Holdout measurement: extraction + rules on real skills, against hand labels.

The calibration set (tests/fixtures/skills/) is what the prompt is tuned on; the holdout
(tests/fixtures/holdout/*.yaml) is not. It pins skills of public sources by commit, path
and content hash and labels pairs of them by hand. Bodies are not stored: the sources are
snapshotted at the pinned commits. Gates as for calibration (constraints.md §2).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel

from skillfetch.ingest.calibrate import (
    HARD_CONFLICT_PRECISION,
    LABEL_KEYS,
    SOFT_TARGET,
    PairReport,
    compare_pairs,
)
from skillfetch.ingest.extract import Extractor, ExtractRecord
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.ingest import run_extractions
from skillfetch.ingest.local_scan import pair_finding
from skillfetch.ingest.skillfile import content_hash
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR, snapshot
from skillfetch.ingest.sources import Source
from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.relation import DEFAULT_CAP, fan_out_map
from skillfetch.resolve.report import render_finding

LABELS = (*LABEL_KEYS, "independent")


class HoldoutSkill(BaseModel):
    path: str
    content_hash: str


class HoldoutPair(BaseModel):
    a: str
    b: str
    label: str
    v4: str | None = None
    note: str = ""


class Holdout(BaseModel):
    sources: dict[str, str]  # source id -> pinned commit
    skills: dict[str, HoldoutSkill]  # skill id ("<source>/<name>@<hash12>") -> pin
    pairs: list[HoldoutPair]

    def labels(self) -> dict[frozenset[str], str]:
        out: dict[frozenset[str], str] = {}
        for p in self.pairs:
            if p.label not in LABELS:
                raise ValueError(f"unknown label {p.label!r} for {p.a} / {p.b}")
            for sid in (p.a, p.b):
                if sid not in self.skills:
                    raise ValueError(f"pair names an unknown skill: {sid}")
            key = frozenset((p.a, p.b))
            if len(key) != 2 or key in out:
                raise ValueError(f"self-pair or pair listed twice: {p.a}, {p.b}")
            out[key] = p.label
        return out


def load_holdout(path: Path) -> Holdout:
    holdout = Holdout.model_validate(yaml.safe_load(path.read_text()))
    holdout.labels()  # validate
    return holdout


def source_of(skill_id: str) -> str:
    return skill_id.split("/", 1)[0]


class HoldoutResult(BaseModel):
    pairs: PairReport
    missing: list[str]  # not extracted (no cache entry and no extractor, or failed)
    moved: list[str]  # content at the pinned path no longer matches the pinned hash
    extracted: dict[str, Skill]
    notes: dict[str, str]  # "a|b" -> hand-label note
    api_cost_usd: float
    fresh: int
    cap: str = DEFAULT_CAP

    @property
    def hard_pass(self) -> bool:
        return self.pairs.conflict_precision >= HARD_CONFLICT_PRECISION

    @property
    def soft_pass(self) -> bool:
        return self.pairs.informative_accuracy >= SOFT_TARGET


def measure_holdout(
    holdout: Holdout,
    sources: list[Source],
    *,
    cache: ExtractCache,
    extractor: Extractor | None,
    model: str,
    work_dir: Path = DEFAULT_WORK_DIR,
    jobs: int = 4,
    cap: str = DEFAULT_CAP,
) -> HoldoutResult:
    by_id = {s.id: s for s in sources}
    unknown = sorted(set(holdout.sources) - set(by_id))
    if unknown:
        raise ValueError(f"holdout names sources missing from sources.yaml: {unknown}")
    snaps = {
        sid: snapshot(by_id[sid].model_copy(update={"ref": commit}), work_dir)
        for sid, commit in holdout.sources.items()
    }
    dirs: dict[str, Path] = {}
    moved = []
    for sid, pin in holdout.skills.items():
        skill_dir = snaps[source_of(sid)].path / pin.path
        if not skill_dir.is_dir() or content_hash(skill_dir) != pin.content_hash:
            moved.append(sid)
            continue
        dirs[sid] = skill_dir
    records: dict[str, ExtractRecord] = {}
    todo = []
    for sid, d in dirs.items():
        digest = holdout.skills[sid].content_hash
        if (hit := cache.get(digest, model, d)) is not None:
            records[sid] = hit
        else:
            todo.append((d, sid, digest))
    fresh = run_extractions(todo, cache, extractor, jobs) if extractor and todo else {}
    cost = 0.0
    for _, sid, digest in todo:
        if digest in fresh:
            records[sid] = fresh[digest]
            cost += fresh[digest].cost_usd or 0.0
    extracted = fan_out_map(
        {
            sid: Skill(id=sid, constraints=_with_ids(records[sid], sid) if sid in records else [])
            for sid in holdout.skills
        },
        cap,
    )
    missing = sorted(sid for sid in dirs if sid not in records or records[sid].status != "ok")
    return HoldoutResult(
        pairs=compare_pairs(holdout.labels(), extracted, cap),
        cap=cap,
        missing=missing,
        moved=sorted(moved),
        extracted=extracted,
        notes={f"{p.a}|{p.b}": p.note for p in holdout.pairs},
        api_cost_usd=cost,
        fresh=len(fresh),
    )


def _with_ids(record: ExtractRecord, sid: str) -> list[Constraint]:
    constraints = record.result.constraints if record.result else []
    return [c.model_copy(update={"id": f"{sid}#c{i}"}) for i, c in enumerate(constraints, 1)]


def _note(notes: Mapping[str, str], a: str, b: str) -> str:
    return notes.get(f"{a}|{b}") or notes.get(f"{b}|{a}") or ""


def render_holdout(result: HoldoutResult) -> str:
    from skillfetch.ingest.build_report import describe

    p = result.pairs
    out = []
    if result.moved:
        out.append(f"content moved (pinned hash no longer matches): {', '.join(result.moved)}")
    if result.missing:
        out.append(f"not extracted: {', '.join(result.missing)}")
    for m in p.mismatches:
        out.append(f"MISMATCH  {m.a} ⟷ {m.b}  expected {m.expected}, got {m.got}")
        if note := _note(result.notes, m.a, m.b):
            out.append(f"  hand label: {note}")
        finding = pair_finding(result.extracted[m.a], result.extracted[m.b], result.cap)
        if finding is None:
            out.append("  extracted: no relation")
        else:
            out += ["  " + line for line in render_finding(finding).splitlines()]
            shown = set()
            for ev in finding.evidence:
                for q in (ev.a, ev.b):
                    if (q.skill_id, q.line_no) in shown:
                        continue
                    shown.add((q.skill_id, q.line_no))
                    for c in result.extracted[q.skill_id].constraints:
                        if c.evidence.line_no == q.line_no:
                            out.append(f"    {q.skill_id}:{q.line_no}  {describe(c)}")
        out.append("")
    out.append("pair relations by expected label:")
    out += [f"  {label:<13} {a.matches}/{a.total}" for label, a in p.by_label.items()]
    out.append(
        f"conflict precision {p.conflict_precision:.3f} "
        f"({p.conflict_true_positives}/{p.conflict_flagged} flagged)"
    )
    out.append(
        f"labelled pairs {p.labelled_correct}/{p.labelled_total} · false positives "
        f"{p.false_positives} (of {p.total - p.labelled_total} unlisted or independent) · "
        f"informative-pair accuracy {p.informative_accuracy:.3f} "
        f"({p.informative_correct}/{p.informative_total})"
    )
    out.append(
        f"gate: conflict precision {p.conflict_precision:.3f} (hard, must be "
        f"{HARD_CONFLICT_PRECISION:.1f}): {'PASS' if result.hard_pass else 'FAIL'} · "
        f"informative-pair accuracy {p.informative_accuracy:.3f} (soft target "
        f"{SOFT_TARGET:.2f}): {'met' if result.soft_pass else 'MISSED'}"
    )
    out.append(f"API cost: ${result.api_cost_usd:.4f} for {result.fresh} extractions")
    return "\n".join(out)
