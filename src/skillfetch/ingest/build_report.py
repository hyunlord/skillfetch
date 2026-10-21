"""Human-readable reports for a built index: report.md (distributions, rejections, licenses,
condition nulls, cost) and review.md (every informative pair, with evidence, for review)."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from skillfetch.ingest.build import BuildResult, Built, tier_warnings
from skillfetch.ingest.calibrate import compact
from skillfetch.ingest.local_scan import pair_finding
from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.relation import candidate_pairs
from skillfetch.resolve.report import render_finding

KIND_ORDER = ("conflict", "redundant", "tension", "needs_review")


def _table(header: tuple[str, ...], rows: list[tuple]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def _counts(title: str, counter: Counter, label: str = "") -> list[str]:
    if not counter:
        return [f"{title}: none", ""]
    rows = [(f"`{k}`" if label == "code" else k, n) for k, n in counter.most_common()]
    return [f"{title}:", "", *_table(("", "count"), rows), ""]


def _c_reasons(b: Built, by_id: dict) -> list[str]:
    r = b.record
    if r.status != "ok":
        return [r.status]
    reasons = []
    if r.canonical_id != r.id and by_id[r.canonical_id].publisher_trust == "verified":
        reasons.append("copy of a tier A skill")
    if r.has_scripts:
        reasons.append("has scripts (publisher not verified)")
    if r.publisher_trust == "unknown" and tier_warnings(r.scan):
        reasons.append("unknown publisher with scan warnings")
    return reasons


def render_report(result: BuildResult) -> str:
    m, skills = result.manifest, result.skills
    by_id = {b.record.id: b.record for b in skills}
    out = [
        "# Index build report",
        "",
        f"Built {m['built_at']} · extraction `{m['extract_model']}` v{m['extract_version']} · "
        f"scan rules v{m['scan_rules_version']} · conflict cap `{m.get('conflict_cap', 'all')}`",
        "",
        "## Sources",
        "",
        *_table(
            ("source", "commit", "trust", "discovered", "sampled", "seed", "records"),
            [
                (
                    s["id"],
                    s["commit"][:12],
                    s["publisher_trust"],
                    s["discovered"],
                    s["sampled"],
                    s["sample_seed"] if s["sample_seed"] is not None else "-",
                    s["skills"],
                )
                for s in m["sources"]
            ],
        ),
        "",
        "## Tiers",
        "",
    ]
    per_source: dict[str, Counter] = defaultdict(Counter)
    for b in skills:
        per_source[b.record.source_id][b.record.tier or b.record.status] += 1
    # extract_failed and uncached skills are tier C ("Why tier C"); too_large keeps its tier
    columns = ("A", "B", "C", "lint_failed", "scan_failed")
    out += _table(
        ("source", *columns),
        [(sid, *(c.get(k, 0) for k in columns)) for sid, c in per_source.items()],
    )
    rejected = [b for b in skills if b.record.tier is None]
    lint_rules = Counter(i["rule"] for b in rejected for i in b.record.lint.get("errors", []))
    scan_rules = Counter(h["rule_id"] for b in rejected for h in b.record.scan.get("failures", []))
    out += ["", "## Not indexed", ""]
    out += _counts("Lint errors (by rule)", lint_rules, "code")
    out += _counts("Injection-scan failures (by rule)", scan_rules, "code")
    tier_c = [b for b in skills if b.record.tier == "C"]
    c_reasons = Counter(reason for b in tier_c for reason in _c_reasons(b, by_id))
    out += ["## Why tier C", "", *_table(("reason", "count"), c_reasons.most_common()), ""]
    warn_rules = Counter(
        h["rule_id"] for b in skills if b.record.tier for h in b.record.scan.get("warnings", [])
    )
    out += _counts("Scan warnings on indexed skills (by rule)", warn_rules, "code")
    failed = [b for b in skills if b.record.status in ("extract_failed", "not_extracted")]
    if failed:
        out += ["Not extracted (extract_failed is tier C; too_large keeps its tier):", ""]
        out += [
            f"- `{b.record.id}` {b.record.not_extracted_reason or b.record.status}: "
            f"{b.record.extract_error}"
            for b in failed
        ]
        out.append("")

    indexed = [b for b in skills if b.record.tier]
    out += ["## Licenses", ""]
    lic = Counter((b.record.source_id, b.record.license) for b in indexed)
    out += _table(
        ("source", "license", "indexed", "redistributable"),
        [
            (sid, name, n, "yes" if name in _redistributable_names(indexed) else "no")
            for (sid, name), n in sorted(lic.items())
        ],
    )
    redistributable = sum(b.record.redistributable for b in indexed)
    out += ["", f"Bodies included: {redistributable} of {len(indexed)} indexed skills.", ""]
    origins = Counter(b.record.license_origin for b in indexed)
    out += _counts("License taken from", origins)
    with_up = [b for b in indexed if b.record.upstream]
    repos = Counter(b.record.upstream["repo"] for b in with_up)
    out += [
        "## Upstreams",
        "",
        f"{len(with_up)} of {len(indexed)} indexed skills name an upstream.",
        "",
    ]
    out += _counts("Most common upstream repos", Counter(dict(repos.most_common(15))))
    for s in m["sources"]:
        if s["third_party_upstreams"]:
            names = ", ".join(f"{u['name']} ({u['url']})" for u in s["third_party_upstreams"])
            out += [f"Third-party upstreams listed by {s['id']}: {names}", ""]

    out += ["## Duplicate groups", "", f"{len(result.groups)} groups.", ""]
    for canon, members in sorted(result.groups.items()):
        out.append(f"- `{canon}`: " + ", ".join(f"`{x}`" for x in members if x != canon))
    out.append("")

    extracted = [b for b in indexed if b.record.status == "ok"]
    total = sum(b.record.constraint_count for b in extracted)
    kinds = Counter(_kind(n) for b in extracted for n in b.record.adjusted)
    dropped = Counter(d.split(";")[0].split(":")[0] for b in extracted for d in b.record.dropped)
    out += [
        "## Constraints",
        "",
        f"{total} constraints from {len(extracted)} extracted skills "
        f"({total / len(extracted):.1f} per skill)."
        if extracted
        else "No extracted skills.",
        "",
    ]
    out += _counts("Post-processing adjustments (by kind)", kinds)
    out += _counts("Dropped constraints (by reason)", dropped)
    nulls = [(b.record.id, n) for b in skills for n in b.record.adjusted if _kind(n) == "condition"]
    out += ["## Conditions set to null", "", f"{len(nulls)} constraints.", ""]
    out += [f"- `{sid}` {note}" for sid, note in nulls]
    out.append("")

    fresh = {b.record.content_hash: b for b in skills if b.fresh and b.extraction}
    cached = {b.record.content_hash for b in skills if b.extraction and not b.fresh}
    cost = result.api_cost_usd
    out += [
        "## Cost",
        "",
        f"API cost this run: ${cost:.4f} for {len(fresh)} extractions"
        + (f" (${cost / len(fresh):.5f} per skill)" if fresh else "")
        + f"; {len(cached)} extractions came from the cache.",
        "",
    ]
    return "\n".join(out)


def _kind(note: str) -> str:
    if ": under heading " in note:
        return "heading"
    for kind in ("condition", "subject", "artifact"):
        if f": {kind}" in note:
            return kind
    return "polarity"


def _redistributable_names(indexed: list[Built]) -> set[str]:
    return {b.record.license for b in indexed if b.record.redistributable}


def informative_findings(result: BuildResult):
    """(finding, a, b) for every non-independent pair of canonical, extracted skills."""
    canon = [
        b
        for b in result.skills
        if b.record.tier and b.record.status == "ok" and b.record.canonical_id == b.record.id
    ]
    canon.sort(key=lambda b: b.record.id)
    skills = [Skill(id=b.record.id, constraints=b.constraints) for b in canon]
    found = []
    for i, j in candidate_pairs(skills):
        f = pair_finding(skills[i], skills[j])
        if f is not None:
            found.append((f, canon[i], canon[j]))
    found.sort(key=lambda t: (KIND_ORDER.index(t[0].kind), t[0].a, t[0].b))
    return found


def describe(c: Constraint) -> str:
    """A constraint as extracted, with the fields relations ignore (raw object)."""
    out = compact(c)
    if c.object_raw and c.object_raw != c.object:
        out += f' · raw object "{c.object_raw}"'
    if c.section_heading:
        out += f' · under "{c.section_heading}"'
    return out


def _extracted_lines(finding, built: dict[str, Built]) -> list[str]:
    seen, out = set(), []
    for ev in finding.evidence:
        for q in (ev.a, ev.b):
            if (q.skill_id, q.line_no) in seen:
                continue
            seen.add((q.skill_id, q.line_no))
            for c in built[q.skill_id].constraints:
                if c.evidence.line_no == q.line_no:
                    out.append(f"  - `{q.skill_id}:{q.line_no}` {describe(c)}")
    return out


def render_review(result: BuildResult) -> str:
    found = informative_findings(result)
    by_kind = Counter(f.kind for f, _, _ in found)
    recs = {b.record.id: b.record for b in result.skills}
    built = {b.record.id: b for b in result.skills}
    out = [
        "# Informative pairs for review",
        "",
        "Every non-independent pair among canonical, extracted skills (duplicates collapsed).",
        "Mark each finding right or wrong; wrong `conflict` findings are precision bugs.",
        "",
        *_table(("kind", "pairs"), [(k, by_kind.get(k, 0)) for k in KIND_ORDER]),
    ]
    current = None
    for i, (finding, _, _) in enumerate(found, 1):
        if finding.kind != current:
            current = finding.kind
            out += ["", f"## {current}", ""]
        ra, rb = recs[finding.a], recs[finding.b]
        out += [
            f"### {i}. `{finding.a}` ⟷ `{finding.b}`",
            "",
            f"- tiers {ra.tier} / {rb.tier} · {ra.source_url} · {rb.source_url}",
            "- [ ] correct",
            "- extracted as:",
            *_extracted_lines(finding, built),
            "",
            "```",
            render_finding(finding),
            "```",
            "",
        ]
    return "\n".join(out)


def write_reports(result: BuildResult, report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report, review = report_dir / "report.md", report_dir / "review.md"
    report.write_text(render_report(result) + "\n")
    review.write_text(render_review(result) + "\n")
    return report, review
