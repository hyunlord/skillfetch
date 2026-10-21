"""Constraints whose polarity extraction cannot be trusted (constraints.md §3 row 14b).

A line under a heading that lists what not to do ("❌ Don't", "Never", "Avoid") that itself
uses a negating verb ("Ignore naming conventions.", "Skip validation") is a double negative:
extractors get its directive wrong in either direction. Such a constraint never makes a
conflict on its own. Pure text heuristics over fields filled at extraction time.
"""

from __future__ import annotations

import re

from skillfetch.resolve.models import Constraint

_NEGATIVE_MARK = re.compile(r"❌|🚫|⛔|✗|✘")
# The whole heading must be a label: "## Never hardcode secrets" is an instruction with an
# explanation below it, not a list of what not to do.
_NEGATIVE_LABEL = re.compile(
    r"^(?:don'?ts?|do not|never|never do|avoid|drop|what to avoid|things to avoid|"
    r"what not to do|(?:\w+ )?anti-?patterns?|(?:\w+ )?mistakes(?: to avoid)?|"
    r"bad (?:practices?|examples?|patterns?)|must not(?: do)?)$",
    re.IGNORECASE,
)
# With a marker, only a label or nothing: "⛔ DO NOT start until you read the docs" is an
# instruction whose lines say what to do.
_MARKED_LABEL = re.compile(r"^(?:|wrong|bad|incorrect|no)$", re.IGNORECASE)
_POSITIVE = re.compile(r"✅|✔|☑|(?<![\w'])(?:do'?s|do and|dos and|do/)(?![\w'])", re.IGNORECASE)
_NEGATING = re.compile(
    r"(?<![\w'])(?:ignor(?:e|es|ed|ing)|skip(?:s|ped|ping)?|omit(?:s|ted|ting)?|"
    r"forget(?:s|ting)?|neglect(?:s|ed|ing)?|disregard(?:s|ed|ing)?|bypass(?:es|ed|ing)?|"
    r"avoid(?:s|ed|ing)?|drop(?:s|ped|ping)?|don'?t|do not|never|not|no|without)(?![\w'])",
    re.IGNORECASE,
)


def negative_heading(heading: str | None) -> bool:
    """A heading over a list of things not to do, and not a mixed "Do's and Don'ts"."""
    if not heading:
        return False
    text = heading.replace("’", "'")
    if _POSITIVE.search(text):
        return False
    label = re.sub(r"^[\W\d_]+|[\W\d_]+$", "", _NEGATIVE_MARK.sub("", text))
    if _NEGATIVE_LABEL.match(label):
        return True
    return bool(_NEGATIVE_MARK.search(text)) and bool(_MARKED_LABEL.match(label))


def polarity_uncertain(c: Constraint) -> bool:
    """Under a negative heading and negated again on its own line."""
    return negative_heading(c.section_heading) and bool(
        _NEGATING.search(c.evidence.text.replace("’", "'"))
    )
