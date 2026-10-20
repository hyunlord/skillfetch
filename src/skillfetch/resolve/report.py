"""Human-readable rendering of findings (constraints.md §6)."""

from __future__ import annotations

from skillfetch.resolve.models import Finding

_LABELS = {
    "conflict": "CONFLICT",
    "tension": "TENSION",
    "needs_review": "NEEDS_REVIEW",
    "redundant": "REDUNDANT",
}


def render_finding(finding: Finding) -> str:
    lines = [f"{_LABELS[finding.kind]}  {finding.a} ⟷ {finding.b}"]
    for ev in finding.evidence:
        label_a = f"{ev.a.skill_id}:{ev.a.line_no}"
        label_b = f"{ev.b.skill_id}:{ev.b.line_no}"
        width = max(len(label_a), len(label_b))
        lines += [
            f"  subject: {ev.subject}   scope: {ev.artifact} / {ev.phase}",
            f'  {label_a.ljust(width)} "{ev.a.text}"',
            f'  {label_b.ljust(width)} "{ev.b.text}"',
        ]
    return "\n".join(lines)
