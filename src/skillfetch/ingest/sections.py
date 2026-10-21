"""Section headings of SKILL.md lines (constraints.md §2 post-processing).

Every constraint records the heading its evidence line falls under, for review. Extraction
v5 also inverted directives under "don't" headings; the model already reads those lists as
bans, so the inversion double-inverted most of them (9 of 14 sampled) and was removed in v6.
"""

from __future__ import annotations

import re

from skillfetch.resolve.models import Constraint

_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_ATX = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
# A line that is only a bold label: "**Don't:**", "**❌ Avoid**", "__Never__:"
_LABEL = re.compile(r"^\s{0,3}(?:\*\*|__)(.+?)(?:\*\*|__)\s*:?\s*$")
_EMPHASIS = re.compile(r"[*_`]+")


def _clean(text: str) -> str:
    return " ".join(_EMPHASIS.sub("", text.replace("’", "'")).split())


def section_headings(lines: list[str]) -> list[str | None]:
    """The heading each line falls under (index i is line i + 1), headings themselves
    included. A bold label line ("**Don't:**") opens a section that lasts for the block
    right below it: up to the first blank line after a non-blank one."""
    out: list[str | None] = []
    heading: str | None = None
    label: str | None = None
    label_started = in_fence = False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and (m := _ATX.match(line)):
            heading, label = _clean(m.group(1)) or None, None
        elif not in_fence and (m := _LABEL.match(line)):
            label, label_started = _clean(m.group(1)).rstrip(":").strip() or None, False
            out.append(label)
            continue
        elif label is not None:
            if line.strip():
                label_started = True
            elif label_started:
                label = None
        out.append(label or heading)
    return out


def record_sections(constraints: list[Constraint], lines: list[str]) -> list[Constraint]:
    """Each constraint with the heading its evidence line falls under. A field only: the
    heading never changes a directive."""
    headings = section_headings(lines)
    return [
        c.model_copy(
            update={
                "section_heading": headings[c.evidence.line_no - 1]
                if 1 <= c.evidence.line_no <= len(headings)
                else None
            }
        )
        for c in constraints
    ]
