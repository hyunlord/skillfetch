#!/usr/bin/env python3
"""Top-1 final score (BM25 × profile boosts, exactly as Searcher.search ranks) for gold and no-gold queries, and
the score of the best-ranked gold id. search_skills does not return scores; this recomputes them with the same
code path (Searcher.search logic, copied: tier filter, tag boost, language mismatch)."""
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.index.search import DEFAULT_TIERS, LANGUAGE_MISMATCH, TAG_BOOST, Searcher, _profile_tags, _skill_tags

R = Path(__file__).resolve().parents[1]


def ranked(s, query, profile, tiers=DEFAULT_TIERS):
    wanted = _profile_tags(profile or {})
    repo_languages = {str(v).lower() for v in (profile or {}).get("languages") or []}
    out = []
    for doc, score, _ in s.bm25.scores(query):
        rec = s.index.records[doc.id]
        if rec.get("tier") not in set(tiers):
            continue
        tags = _skill_tags(rec)
        for _, values in sorted(tags.items()):
            for _ in sorted(values & wanted):
                score *= TAG_BOOST
        langs = tags.get("languages") or set()
        if repo_languages and langs and not langs & repo_languages:
            score *= LANGUAGE_MISMATCH
        out.append((score, rec["id"]))
    out.sort(key=lambda x: (-x[0], x[1]))
    return out


def main():
    s = Searcher(Index.load(DEFAULT_INDEX_DIR))
    rows = []
    for name, has_gold in (("retrieval-eval.jsonl", True), ("retrieval-nogold.jsonl", False)):
        for l in (R / name).read_text().splitlines():
            q = json.loads(l)
            rk = ranked(s, q["query"], q["profile"])
            assert [i for _, i in rk[:10]] == [x["id"] for x in s.search(q["query"], q["profile"], 10)]
            gold = [(n + 1, sc) for n, (sc, i) in enumerate(rk) if i in q["gold"]]
            rows.append({"qid": q["qid"], "has_gold": has_gold, "top1": round(rk[0][0], 3), "top1_id": rk[0][1],
                         "top10": round(rk[9][0], 3), "gold_best": gold[0] if gold else None,
                         "query_tokens": len(set(__import__("skillfetch.index.bm25", fromlist=["x"]).tokenize(q["query"])))})
    (R / "scores.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    for hg in (True, False):
        v = sorted(x["top1"] for x in rows if x["has_gold"] == hg)
        print("gold" if hg else "no-gold", len(v), v)


if __name__ == "__main__":
    main()
