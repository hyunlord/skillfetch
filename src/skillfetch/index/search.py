"""search_skills (CLAUDE.md tool surface, index-format.md §4).

BM25 over title + description + keywords (×2) + synthetic_queries + summary of canonical
skills. The repo profile never enters the query: it boosts (×1.3 per matching tag) or
softly demotes (×0.5 when the skill names languages the repo does not use).
"""

from __future__ import annotations

from collections.abc import Iterable

from skillfetch.index.bm25 import BM25
from skillfetch.index.loader import Index

FIELD_WEIGHTS = {"keywords": 2}
TAG_BOOST = 1.3
LANGUAGE_MISMATCH = 0.5
DEFAULT_TIERS = ("A", "B")


def _text(value) -> str:
    if isinstance(value, list):
        return " ".join(map(str, value))
    return str(value or "")


def _skill_tags(record: dict) -> dict[str, set[str]]:
    return {k: {str(v).lower() for v in vs} for k, vs in (record.get("tags") or {}).items()}


def _profile_tags(profile: dict) -> set[str]:
    out = set()
    for key in ("tags", "languages", "frameworks", "package_managers"):
        out |= {str(v).lower() for v in profile.get(key) or []}
    return out


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
        k: int = 10,
        tiers: Iterable[str] = DEFAULT_TIERS,
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
        return [
            {
                "id": record["id"],
                "title": record.get("title") or record.get("name"),
                "summary": record.get("summary", ""),
                "tier": record.get("tier"),
                "tags": record.get("tags") or {},
                "match_reasons": reasons,
                "token_estimate": record.get("token_estimate", 0),
            }
            for _, record, reasons in ranked[: max(0, k)]
        ]
