"""A small hand-rolled BM25 (Okapi, k1=1.5, b=0.75) over fielded documents.

Fields are concatenated into one bag of tokens per document (a field can be weighted by
repeating it); per-field token sets are kept so a hit can be explained (`match_reasons`).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

_TOKEN = re.compile(r"[a-z0-9]+")


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


STOPWORDS = _words(
    """a an and are as at be but by do for from has have how i if in into is it its me my
    no not of on or our so that the their them then there these this to use using was we
    were what when where which while who why will with you your"""
)


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords; no stemming (index-format §4)."""
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Doc:
    id: str
    fields: dict[str, set[str]]  # field -> distinct tokens, for match_reasons
    tf: Counter
    length: int


@dataclass
class BM25:
    k1: float = 1.5
    b: float = 0.75
    docs: list[Doc] = field(default_factory=list)
    df: Counter = field(default_factory=Counter)

    def add(self, doc_id: str, fields: dict[str, str], weights: dict[str, int] | None = None):
        weights = weights or {}
        tokens: list[str] = []
        per_field = {}
        for name, text in fields.items():
            toks = tokenize(text)
            per_field[name] = set(toks)
            tokens += toks * weights.get(name, 1)
        tf = Counter(tokens)
        self.docs.append(Doc(doc_id, per_field, tf, len(tokens)))
        self.df.update(tf.keys())

    @property
    def avg_length(self) -> float:
        return sum(d.length for d in self.docs) / len(self.docs) if self.docs else 0.0

    def idf(self, token: str) -> float:
        n, df = len(self.docs), self.df.get(token, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def scores(self, query: str) -> list[tuple[Doc, float, list[str]]]:
        """(doc, score, matched query tokens) for every doc with a hit, best first."""
        q = list(dict.fromkeys(tokenize(query)))
        avg = self.avg_length or 1.0
        out = []
        for d in self.docs:
            hits = [t for t in q if t in d.tf]
            if not hits:
                continue
            score = 0.0
            for t in hits:
                f = d.tf[t]
                norm = f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * d.length / avg))
                score += self.idf(t) * norm
            out.append((d, score, hits))
        out.sort(key=lambda x: (-x[1], x[0].id))
        return out
