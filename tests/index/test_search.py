"""search_skills: BM25 ranking, tiers, profile boost (index-format.md §4)."""

import json

from indexkit import make_index, skill_id

from skillfetch.index.loader import Index
from skillfetch.index.search import Searcher


def _searcher(tmp_path, **kw):
    return Searcher(Index.load(make_index(tmp_path, **kw)))


def test_results_are_ranked_and_explained(tmp_path):
    s = _searcher(tmp_path)
    [top, *_] = s.search("add type annotations to a python module")
    assert top["id"].startswith("fx/typed-python@")
    assert set(top) == {"id", "title", "summary", "tier", "tags", "match_reasons", "token_estimate"}
    assert any("'python' in" in r for r in top["match_reasons"])
    json.dumps(top)  # plain JSON


def test_k_limits_the_results(tmp_path):
    s = _searcher(tmp_path)
    assert len(s.search("commits squash emoji pnpm python", k=2)) == 2
    assert s.search("nothing matches this at all xyzzy") == []


def test_profile_is_a_boost_never_part_of_the_query(tmp_path):
    s = _searcher(tmp_path)
    # the profile alone does not create hits
    assert s.search("xyzzy", profile={"languages": ["python"]}) == []
    boosted = s.search("install dependencies headers", profile={"tags": ["docs"]})
    assert boosted[0]["id"].startswith("fx/emoji-headers@")
    assert any("profile tag 'docs'" in r for r in boosted[0]["match_reasons"])


def test_skills_for_other_languages_are_demoted_not_dropped(tmp_path):
    s = _searcher(tmp_path)
    hits = s.search("python javascript", profile={"languages": ["rust"]})
    assert {h["id"].split("@")[0] for h in hits} >= {"fx/typed-python", "fx/pnpm-only"}
    for h in hits:
        if h["id"].split("@")[0] in ("fx/typed-python", "fx/pnpm-only"):
            assert "not the repo's" in " ".join(h["match_reasons"])


def test_tier_filter(tmp_path):
    root = make_index(tmp_path, trust="unknown")  # unknown publisher: tier B
    s = Searcher(Index.load(root))
    assert s.search("python", tiers=["A"]) == []
    assert s.search("python", tiers=["B"])[0]["id"] == skill_id(root, "typed-python")
