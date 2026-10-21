"""Pairs for the LLM judge: the labelled fixture pairs (calibration) and every needs_review /
tension pair of a built index, with the §3 row that made it one (the cross-table)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from skillfetch.ingest.calibrate import load_labelled, load_labels
from skillfetch.ingest.judge import VERDICTS, Item, Outcome, Side, agrees, pair_input
from skillfetch.ingest.local_scan import pair_finding
from skillfetch.ingest.skillfile import SKILL_FILE, read_skill, read_text
from skillfetch.resolve import relation
from skillfetch.resolve.models import Constraint, Finding, Skill
from skillfetch.resolve.relation import candidate_pairs, relation_reason


@dataclass
class JudgePair:
    key: str
    kind: str  # relation from the rules (or the hand label, for fixtures)
    reason: str  # §3 row behind it
    item: Item
    evidence: list[tuple[str, int, str]]  # (skill id, line, text) of the shown lines


def _side(skill_id: str, skill_dir: Path, lines: list[int]) -> Side:
    doc = read_skill(skill_dir)
    fm = doc.frontmatter or {}
    return Side(
        skill_id=skill_id,
        name=str(fm.get("name") or skill_dir.name),
        description=str(fm.get("description") or ""),
        text=read_text(skill_dir / SKILL_FILE),
        lines=tuple(lines),
    )


def _lines(finding: Finding) -> tuple[list[int], list[int]]:
    a = [ev.a.line_no for ev in finding.evidence]
    b = [ev.b.line_no for ev in finding.evidence]
    return list(dict.fromkeys(a)), list(dict.fromkeys(b))


def _reason(finding: Finding, skills: dict[str, Skill]) -> str:
    ev = finding.evidence[0]

    def at(sid: str, line: int) -> Constraint:
        return next(c for c in skills[sid].constraints if c.evidence.line_no == line)

    return relation_reason(at(finding.a, ev.a.line_no), at(finding.b, ev.b.line_no))


def _pair(finding: Finding, dirs: dict[str, Path], skills, kind: str | None = None) -> JudgePair:
    lines_a, lines_b = _lines(finding)
    a = _side(finding.a, dirs[finding.a], lines_a)
    b = _side(finding.b, dirs[finding.b], lines_b)
    shown = [(finding.a, n, a.text.split("\n")[n - 1]) for n in a.lines[:2]] + [
        (finding.b, n, b.text.split("\n")[n - 1]) for n in b.lines[:2]
    ]
    return JudgePair(
        key=f"{finding.a}|{finding.b}",
        kind=kind or finding.kind,
        reason=_reason(finding, skills),
        item=Item(f"{finding.a}|{finding.b}", pair_input(a, b)),
        evidence=shown,
    )


def fixture_pairs(fixtures_dir: Path) -> list[JudgePair]:
    """The labelled (non-independent) fixture pairs, with their hand labels as `kind`.
    Evidence comes from the hand-labelled constraints under the vocabulary cap, where the
    labels are the real relations."""
    previous = relation.OBJECTLESS_CAP
    relation.set_objectless_cap("vocabulary")
    try:
        skills = load_labelled(fixtures_dir / "skills")
        labels = load_labels(fixtures_dir / "expected.yaml", cap="vocabulary")
        dirs = {sid: fixtures_dir / "skills" / sid for sid in skills}
        out = []
        for pair, label in sorted(labels.items(), key=lambda kv: sorted(kv[0])):
            a, b = sorted(pair)
            finding = pair_finding(skills[a], skills[b])
            assert finding is not None, (a, b)
            out.append(_pair(finding, dirs, skills, kind=label))
        return out
    finally:
        relation.set_objectless_cap(previous)


def index_pairs(
    index_dir: Path, work_dir: Path, kinds: tuple[str, ...] = ("needs_review", "tension")
) -> list[JudgePair]:
    """needs_review and tension pairs among canonical, extracted skills of a built index
    (the pairs of its review.md); bodies are read from the snapshots in work_dir."""
    records = [json.loads(line) for line in (index_dir / "skills.jsonl").open()]
    by_skill: dict[str, list[Constraint]] = {}
    for line in (index_dir / "constraints.jsonl").open():
        row = json.loads(line)
        by_skill.setdefault(row.pop("skill_id"), []).append(Constraint.model_validate(row))
    canon = sorted(
        (r for r in records if r["status"] == "ok" and r["canonical_id"] == r["id"]),
        key=lambda r: r["id"],
    )
    skills = {r["id"]: Skill(id=r["id"], constraints=by_skill.get(r["id"], [])) for r in canon}
    dirs = {r["id"]: work_dir / r["source_id"] / r["commit"] / r["path"] for r in canon}
    ordered = [skills[r["id"]] for r in canon]
    out = []
    for i, j in candidate_pairs(ordered):
        finding = pair_finding(ordered[i], ordered[j])
        if finding is not None and finding.kind in kinds:
            out.append(_pair(finding, dirs, skills))
    return out


# --- reports --------------------------------------------------------------------------------


def calibration_report(pairs: list[JudgePair], outcomes: list[Outcome]) -> tuple[float, str]:
    by_key = {o.key: o for o in outcomes}
    ok, lines = 0, []
    for p in pairs:
        o = by_key[p.key]
        j = o.record.judgment if o.record else None
        verdict = j.verdict if j else f"error ({o.error or (o.record and o.record.error)})"
        hit = j is not None and agrees(p.kind, j.verdict)
        ok += hit
        if not hit:
            lines.append(f"MISS  {p.key}  hand {p.kind}, judge {verdict}")
            if j:
                lines.append(f"      {j.reason}")
    rate = ok / len(pairs) if pairs else 1.0
    table = Counter(
        (p.kind.split(":", 1)[0], by_key[p.key].record.judgment.verdict)
        for p in pairs
        if by_key[p.key].record and by_key[p.key].record.judgment
    )
    labels = sorted({k for k, _ in table})
    out = ["| hand label | " + " | ".join(VERDICTS) + " |", "|" + "---|" * (len(VERDICTS) + 1)]
    out += [
        f"| {lab} | " + " | ".join(str(table.get((lab, v), 0)) for v in VERDICTS) + " |"
        for lab in labels
    ]
    out += ["", *lines, "", f"judge agreement with hand labels: {rate:.3f} ({ok}/{len(pairs)})"]
    return rate, "\n".join(out)


def cross_table(pairs: list[JudgePair], outcomes: list[Outcome]) -> str:
    by_key = {o.key: o for o in outcomes}
    cells: Counter = Counter()
    for p in pairs:
        o = by_key.get(p.key)
        verdict = o.record.judgment.verdict if o and o.record and o.record.judgment else "error"
        cells[(p.kind, p.reason, verdict)] += 1
    cols = (*VERDICTS, "error")
    rows = sorted({(k, r) for k, r, _ in cells}, key=lambda kr: (kr[0], kr[1]))
    out = ["| rules | §3 row | " + " | ".join(cols) + " | total |", "|" + "---|" * (len(cols) + 3)]
    for kind, reason in rows:
        counts = [cells.get((kind, reason, v), 0) for v in cols]
        out.append(f"| {kind} | {reason} | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")
    totals = [sum(cells.get((k, r, v), 0) for k, r in rows) for v in cols]
    out.append("| **total** | | " + " | ".join(map(str, totals)) + f" | {sum(totals)} |")
    return "\n".join(out)


def ambiguous_list(pairs: list[JudgePair], outcomes: list[Outcome]) -> list[str]:
    by_key = {o.key: o for o in outcomes}
    out = []
    flagged = [
        (p, by_key[p.key].record.judgment)
        for p in pairs
        if by_key.get(p.key)
        and by_key[p.key].record
        and by_key[p.key].record.judgment
        and by_key[p.key].record.judgment.ambiguous_together
    ]
    flagged.sort(key=lambda pj: (-pj[1].confidence, pj[0].key))
    for p, j in flagged:
        a, b = p.key.split("|")
        out += [
            f"### `{a}` ⟷ `{b}`",
            "",
            f"- rules: {p.kind} ({p.reason}) · judge: **{j.verdict}** "
            f"(confidence {j.confidence:.2f})",
            f"- {j.reason}",
        ]
        out += [f'- `{sid}:{n}` "{text.strip()[:300]}"' for sid, n, text in p.evidence]
        out.append("")
    return out


def write_judge_report(
    pairs: list[JudgePair], outcomes: list[Outcome], report_dir: Path, summary: str
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    by_key = {o.key: o for o in outcomes}
    rows = []
    for p in pairs:
        o = by_key.get(p.key)
        j = o.record.judgment if o and o.record else None
        rows.append(
            {
                "pair": p.key,
                "rules": p.kind,
                "row": p.reason,
                "verdict": j.verdict if j else None,
                "reason": j.reason if j else None,
                "ambiguous_together": j.ambiguous_together if j else None,
                "confidence": j.confidence if j else None,
                "error": (o.error or (o.record and o.record.error)) if o else "not judged",
                "evidence": p.evidence,
            }
        )
    (report_dir / "judgments.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    )
    amb = ambiguous_list(pairs, outcomes)
    text = [
        "# LLM judge over needs_review and tension pairs",
        "",
        summary,
        "",
        "## Rules × judge verdict",
        "",
        "Rows: the relation the rules gave and the constraints.md §3 row that decided it "
        "(for capped conflicts, row 14's reason). Columns: the judge's verdict on the "
        "original lines.",
        "",
        cross_table(pairs, outcomes),
        "",
        f"## ambiguous_together = true ({sum(1 for line in amb if line.startswith('### '))})",
        "",
        *amb,
    ]
    path = report_dir / "judge.md"
    path.write_text("\n".join(text) + "\n")
    return path
