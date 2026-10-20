"""Term normalization shared by relation rules and the vocabulary (constraints.md §3)."""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")


def _singular(word: str) -> str:
    if len(word) <= 3 or word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s"):
        return word[:-1]
    return word


def normalize_term(text: str) -> str:
    """Lowercase, collapse whitespace, naive per-word singular, strip edge punctuation."""
    text = re.sub(r"\s+", " ", text.lower()).strip()
    text = _WORD.sub(lambda m: _singular(m.group()), text)
    return text.strip(" .,;:!?")
