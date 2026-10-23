"""search_skills (CLAUDE.md tool surface, index-format.md §4).

BM25 over title + description + keywords (×2) + synthetic_queries + summary of canonical
skills. The repo profile never enters the query: it boosts (×1.3 per matching tag) or
softly demotes (×0.5 when the skill names languages the repo does not use).

Results are compact by default (id, title, one-line summary, tier, token_estimate) so that
50 of them fit in about 4k tokens; `verbose=True` adds the full summary, tags and
match_reasons.

`search_many` runs up to MAX_QUERIES queries (e.g. what the task builds, how to work, the
stack) and merges their rankings with reciprocal rank fusion (`rrf`, k=60), the merge the
retrieval benchmark measures (`skillfetch eval retrieval`, evals/retrieval/).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from skillfetch.index.bm25 import BM25
from skillfetch.index.loader import Index

FIELD_WEIGHTS = {"keywords": 2}
TAG_BOOST = 1.3
LANGUAGE_MISMATCH = 0.5
DEFAULT_TIERS = ("A", "B")
DEFAULT_K = 50
RRF_K = 60
MAX_QUERIES = 4
ONE_LINE_CHARS = 160
# a sentence ends at . ! ? followed by space and a capital ("e.g. tables" does not end one)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[`])")


def _text(value) -> str:
    if isinstance(value, list):
        return " ".join(map(str, value))
    return str(value or "")


def one_line(summary: str, limit: int = ONE_LINE_CHARS) -> str:
    """The summary's first sentence, cut at a word boundary to at most `limit` characters."""
    text = " ".join(str(summary or "").split())
    first = _SENTENCE_END.split(text, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    return first[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _skill_tags(record: dict) -> dict[str, set[str]]:
    return {k: {str(v).lower() for v in vs} for k, vs in (record.get("tags") or {}).items()}


def _profile_tags(profile: dict) -> set[str]:
    out = set()
    for key in ("tags", "languages", "frameworks", "package_managers"):
        out |= {str(v).lower() for v in profile.get(key) or []}
    return out


def rrf(*rankings: list[str], k: int = RRF_K) -> list[str]:
    """Reciprocal rank fusion: each id scores the sum of 1 / (k + rank) over the rankings it
    appears in (rank from 1); best first, ties by id."""
    score: dict[str, float] = {}
    for ranking in rankings:
        for n, sid in enumerate(ranking, 1):
            score[sid] = score.get(sid, 0) + 1 / (k + n)
    return sorted(score, key=lambda s: (-score[s], s))


class Searcher:
    def __init__(self, index: Index):
        self.index = index
        self.bm25 = BM25()
        for record in index.canonical():
            self.bm25.add(
                record["id"],
                {
                    "title": _text(record.get("title")),
                    "description": _text(record.get("description")),
                    "keywords": _text(record.get("keywords")),
                    "synthetic_queries": _text(record.get("synthetic_queries")),
                    "summary": _text(record.get("summary")),
                },
                FIELD_WEIGHTS,
            )

    def search(
        self,
        query: str,
        profile: dict | None = None,
        k: int = DEFAULT_K,
        tiers: Iterable[str] = DEFAULT_TIERS,
        verbose: bool = False,
    ) -> list[dict]:
        tiers = set(tiers)
        wanted = _profile_tags(profile or {})
        repo_languages = {str(v).lower() for v in (profile or {}).get("languages") or []}
        ranked = []
        for doc, score, hits in self.bm25.scores(query):
            record = self.index.records[doc.id]
            if record.get("tier") not in tiers:
                continue
            reasons = [
                f"'{t}' in {', '.join(f for f, toks in doc.fields.items() if t in toks)}"
                for t in hits
            ]
            tags = _skill_tags(record)
            for field_name, values in sorted(tags.items()):
                for tag in sorted(values & wanted):
                    score *= TAG_BOOST
                    reasons.append(f"profile tag '{tag}' matches tags.{field_name} (x{TAG_BOOST})")
            languages = tags.get("languages") or set()
            if repo_languages and languages and not languages & repo_languages:
                score *= LANGUAGE_MISMATCH
                reasons.append(
                    f"skill languages {sorted(languages)} are not the repo's "
                    f"{sorted(repo_languages)} (x{LANGUAGE_MISMATCH})"
                )
            ranked.append((score, record, reasons))
        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))
        out = []
        for _, record, reasons in ranked[: max(0, k)]:
            title = record.get("title") or record.get("name")
            summary = record.get("summary", "")
            tokens = record.get("token_estimate", 0)
            if verbose:
                out.append(
                    {
                        "id": record["id"],
                        "title": title,
                        "summary": summary,
                        "tier": record.get("tier"),
                        "tags": record.get("tags") or {},
                        "match_reasons": reasons,
                        "token_estimate": tokens,
                    }
                )
            else:
                out.append(
                    {
                        "id": record["id"],
                        "title": title,
                        "summary": one_line(summary),
                        "tier": record.get("tier"),
                        "token_estimate": tokens,
                    }
                )
        return out

    def search_many(
        self,
        queries: list[str],
        profile: dict | None = None,
        k: int = DEFAULT_K,
        tiers: Iterable[str] = DEFAULT_TIERS,
        verbose: bool = False,
    ) -> list[dict]:
        """Each query's top k, merged with `rrf` and cut to k. One query is `search` itself."""
        tiers = tuple(tiers)
        per = [self.search(q, profile, k, tiers, verbose=verbose) for q in queries]
        if len(per) == 1:
            return per[0]
        first: dict[str, dict] = {}
        for results in per:
            for r in results:
                first.setdefault(r["id"], r)
        merged = rrf(*([r["id"] for r in results] for results in per))
        return [first[sid] for sid in merged[: max(0, k)]]
