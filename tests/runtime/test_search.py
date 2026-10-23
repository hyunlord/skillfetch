"""search_skills: BM25 ranking, tiers, profile boost (index-format.md §4)."""

import json

from indexkit import make_index, skill_id

from skillfetch.index.loader import Index
from skillfetch.index.search import DEFAULT_K, ONE_LINE_CHARS, Searcher, one_line


def _searcher(tmp_path, **kw):
    return Searcher(Index.load(make_index(tmp_path, **kw)))


def test_results_are_ranked_and_explained(tmp_path):
    s = _searcher(tmp_path)
    [top, *_] = s.search("add type annotations to a python module", verbose=True)
    assert top["id"].startswith("fx/typed-python@")
    assert set(top) == {"id", "title", "summary", "tier", "tags", "match_reasons", "token_estimate"}
    assert any("'python' in" in r for r in top["match_reasons"])
    json.dumps(top)  # plain JSON


def test_results_are_compact_by_default(tmp_path):
    s = _searcher(tmp_path)
    [top, *_] = s.search("add type annotations to a python module")
    assert set(top) == {"id", "title", "summary", "tier", "token_estimate"}
    full = s.search("add type annotations to a python module", verbose=True)[0]
    assert top["id"] == full["id"]
    assert top["summary"] == one_line(full["summary"])
    assert DEFAULT_K == 50


def test_one_line_keeps_the_first_sentence_within_the_limit():
    assert one_line("Squash commits. Then push.") == "Squash commits."
    assert one_line("  two\n lines  of text ") == "two lines of text"
    assert one_line("") == ""
    long = "word " * 60 + "end."
    cut = one_line(long)
    assert len(cut) <= ONE_LINE_CHARS and cut.endswith("…") and " wor…" not in cut
    abbreviated = "v1.2 adds tables, e.g. pivots."
    assert one_line(abbreviated + " Then it stops.") == abbreviated


def test_k_limits_the_results(tmp_path):
    s = _searcher(tmp_path)
    assert len(s.search("commits squash emoji pnpm python", k=2)) == 2
    assert s.search("nothing matches this at all xyzzy") == []


def test_profile_is_a_boost_never_part_of_the_query(tmp_path):
    s = _searcher(tmp_path)
    # the profile alone does not create hits
    assert s.search("xyzzy", profile={"languages": ["python"]}) == []
    boosted = s.search("install dependencies headers", profile={"tags": ["docs"]}, verbose=True)
    assert boosted[0]["id"].startswith("fx/emoji-headers@")
    assert any("profile tag 'docs'" in r for r in boosted[0]["match_reasons"])


def test_skills_for_other_languages_are_demoted_not_dropped(tmp_path):
    s = _searcher(tmp_path)
    hits = s.search("python javascript", profile={"languages": ["rust"]}, verbose=True)
    assert {h["id"].split("@")[0] for h in hits} >= {"fx/typed-python", "fx/pnpm-only"}
    for h in hits:
        if h["id"].split("@")[0] in ("fx/typed-python", "fx/pnpm-only"):
            assert "not the repo's" in " ".join(h["match_reasons"])


def test_tier_filter(tmp_path):
    root = make_index(tmp_path, trust="unknown")  # unknown publisher: tier B
    s = Searcher(Index.load(root))
    assert s.search("python", tiers=["A"]) == []
    assert s.search("python", tiers=["B"])[0]["id"] == skill_id(root, "typed-python")


def test_korean_queries_match_through_cjk_bigrams(tmp_path, monkeypatch):
    import indexkit

    from skillfetch.index.bm25 import tokenize

    meta = dict(indexkit.META)
    meta["pnpm-only"] = {
        **meta["pnpm-only"],
        "synthetic_queries": ["React 컴포넌트 리팩토링 전에 의존성 설치"],
    }
    monkeypatch.setattr(indexkit, "META", meta)
    s = _searcher(tmp_path)
    assert tokenize("리팩토링") == ["리팩", "팩토", "토링"]
    for query in ("React 컴포넌트 리팩토링", "컴포넌트 리팩토링"):  # the second has no Latin word
        [top, *_] = s.search(query, verbose=True)
        assert top["id"].startswith("fx/pnpm-only@"), query
        assert any("'리팩'" in r or "'컴포'" in r for r in top["match_reasons"]), top


def test_rrf_order_is_fixed():
    from skillfetch.index.search import rrf

    # a: 1/61 + 1/62, c: 1/63 + 1/61, b: 1/62, d: 1/63 -> a > c > b > d
    assert rrf(["a", "b", "c"], ["c", "a", "d"]) == ["a", "c", "b", "d"]
    # equal scores break by id
    assert rrf(["y"], ["x"]) == ["x", "y"]
    assert rrf(["b", "a"], k=0) == ["b", "a"]


def test_one_query_is_plain_search(tmp_path):
    s = _searcher(tmp_path)
    for q in ("squash commits", "python types", "emoji in markdown headers"):
        assert s.search_many([q]) == s.search(q)
        assert s.search_many([q], verbose=True) == s.search(q, verbose=True)


def test_several_queries_are_rrf_merged(tmp_path):
    from skillfetch.index.search import rrf

    s = _searcher(tmp_path)
    queries = ["squash commits", "python type hints", "emoji headers"]
    lists = [[r["id"] for r in s.search(q, k=5)] for q in queries]
    merged = s.search_many(queries, k=5)
    assert [r["id"] for r in merged] == rrf(*lists)[:5]
    assert set(merged[0]) == {"id", "title", "summary", "tier", "token_estimate"}
