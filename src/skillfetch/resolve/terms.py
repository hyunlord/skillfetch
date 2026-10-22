"""Term normalization shared by relation rules and the vocabulary (constraints.md §3)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")
PLURALS_FILE = Path(__file__).with_name("plurals.txt")
# Words ending in -s whose -s is not a plural, though the stem is also a word.
STOPLIST = frozenset(
    {
        "https",
        "windows",
        "always",
        "status",
        "analysis",
        "news",
        "canvas",
        "rails",
        "express",
        "postgres",
        "devops",
        "ops",
        "aws",
        "means",
        "sometimes",
        "perhaps",
        "whereas",
        "atlas",
        "alias",
        "bias",
        "lens",
        "jenkins",
        "kubernetes",
        "less",
        "unless",
        "across",
        "series",
        "species",
    }
)


def singular_candidate(word: str) -> str:
    """The singular a plural-looking word would have (no corpus check)."""
    if len(word) <= 3 or word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s"):
        return word[:-1]
    return word


@cache
def plurals() -> frozenset[str]:
    """Plurals whose singular occurs in the corpus vocabulary (scripts/plural_words.py)."""
    lines = PLURALS_FILE.read_text().splitlines()
    return frozenset(w for w in (line.strip() for line in lines) if w and not w.startswith("#"))


def _singular(word: str) -> str:
    if word in STOPLIST or word not in plurals():
        return word
    return singular_candidate(word)


def normalize_term(text: str) -> str:
    """Lowercase, collapse whitespace, singular per word when both forms occur in the
    corpus vocabulary (never for STOPLIST words), strip edge punctuation."""
    text = re.sub(r"\s+", " ", text.lower()).strip()
    text = _WORD.sub(lambda m: _singular(m.group()), text)
    return text.strip(" .,;:!?")
