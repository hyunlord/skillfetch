"""Section headings of SKILL.md lines, and lists that name what not to do.

A list under "### ❌ Don't" states bad practice as imperatives ("- Ignore error messages").
Read alone, such a line is the opposite of the skill's instruction. The extractor is told
to extract each line as written; `apply_sections` records every constraint's heading and
inverts the directive of constraints under a "don't" heading (constraints.md §2).
"""

from __future__ import annotations

import re

from skillfetch.resolve.models import Constraint

_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_ATX = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
# A line that is only a bold label: "**Don't:**", "**❌ Avoid**", "__Never__:"
_LABEL = re.compile(r"^\s{0,3}(?:\*\*|__)(.+?)(?:\*\*|__)\s*:?\s*$")
_EMPHASIS = re.compile(r"[*_`]+")
_NEGATIVE_MARK = re.compile(r"❌|🚫|⛔|✗|✘")
# The whole heading must be a label: "## Never hardcode secrets" is an instruction with
# explanation below it, not a list of what not to do.
_NEGATIVE_LABEL = re.compile(
    r"^(?:don'?ts?|do not|never|never do|avoid|what to avoid|things to avoid|"
    r"what not to do|(?:\w+ )?anti-?patterns?|(?:\w+ )?mistakes(?: to avoid)?|"
    r"bad (?:practices?|examples?|patterns?))$",
    re.IGNORECASE,
)
_MARKED_LABEL = re.compile(r"^(?:|wrong|bad|incorrect|no)$", re.IGNORECASE)
_POSITIVE = re.compile(r"✅|✔|☑|(?<![\w'])(?:do'?s|do and|dos and|do/)(?![\w'])", re.IGNORECASE)
# A line that negates on its own restates the ban ("- Don't skip tests" under "Don'ts").
_LINE_NEGATION = re.compile(
    r"(?<![\w'])(?:don'?t|do not|never|not|no|avoid|without|stop|nor)(?![\w'])", re.IGNORECASE
)
_INVERT = {"require": "forbid", "forbid": "require", "prefer": "avoid", "avoid": "prefer"}


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


def negative_section(heading: str | None) -> bool:
    """A heading over a list of things not to do ("❌ Don't", "Anti-patterns"), and not
    a mixed "Do's and Don'ts" heading."""
    if not heading:
        return False
    text = heading.replace("’", "'")
    if _POSITIVE.search(text):
        return False
    label = re.sub(r"^[\W\d_]+|[\W\d_]+$", "", _NEGATIVE_MARK.sub("", text))
    if _NEGATIVE_LABEL.match(label):
        return True
    # A marker only with a label or nothing else: "⛔ DO NOT start until you read the docs"
    # is an instruction, and the lines below it say what to do.
    return bool(_NEGATIVE_MARK.search(text)) and bool(_MARKED_LABEL.match(label))


def apply_sections(
    constraints: list[Constraint], lines: list[str]
) -> tuple[list[Constraint], list[str]]:
    """Record each constraint's section heading; invert the directive of constraints
    under a "don't" heading whose own line carries no negation. One note per inversion."""
    headings = section_headings(lines)
    out, notes = [], []
    for c in constraints:
        line_no = c.evidence.line_no
        heading = headings[line_no - 1] if 1 <= line_no <= len(headings) else None
        update: dict = {"section_heading": heading}
        if (
            c.directive in _INVERT
            and negative_section(heading)
            and not _LINE_NEGATION.search(c.evidence.text.replace("’", "'"))
        ):
            directive = _INVERT[c.directive]
            update |= {"directive": directive}
            notes.append(
                f"line {line_no}: under heading {heading!r}: {c.directive} -> {directive} "
                "(the list names what not to do)"
            )
        out.append(c.model_copy(update=update))
    return out, notes
