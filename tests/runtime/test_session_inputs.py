"""Tool inputs at the session boundary: query length, k, profile shape, path: in auto_ids,
and the manifest-size cap of profile_repo."""

import json

from indexkit import make_index, skill_id

from skillfetch.index import profile as profile_mod
from skillfetch.index.loader import Index
from skillfetch.index.profile import profile_repo
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.session import MAX_AUTO_IDS, MAX_K, MAX_QUERY_CHARS, Session


def _session(tmp_path):
    root = make_index(tmp_path)
    return root, Session(Index.load(root), extract_cache=ExtractCache(tmp_path / "xc"))


def _spy(s):
    calls = []
    real = s.searcher.search

    def search(query, profile, k, tiers, verbose=False):
        calls.append((query, profile, k))
        return real(query, profile, k, tiers, verbose=verbose)

    s.searcher.search = search
    return calls


def test_the_query_is_not_echoed(tmp_path):
    _, s = _session(tmp_path)
    out = s.search_skills("squash commits")
    assert set(out) == {"results"} and out["results"]


def test_long_queries_are_cut_and_flagged(tmp_path):
    _, s = _session(tmp_path)
    calls = _spy(s)
    out = s.search_skills("squash commits " * 400)
    assert out["truncated"] is True
    assert len(calls[0][0]) == MAX_QUERY_CHARS
    assert "truncated" not in s.search_skills("squash commits")


def test_k_is_capped(tmp_path):
    _, s = _session(tmp_path)
    calls = _spy(s)
    s.search_skills("squash commits", k=10_000)
    assert calls[0][2] == MAX_K


def test_a_malformed_profile_is_a_structured_error(tmp_path):
    _, s = _session(tmp_path)
    out = s.search_skills("python types", profile={"tags": "python", "languages": [1, {"x": 2}]})
    assert out["error"] == "invalid profile"
    assert {d["loc"].split(".")[0] for d in out["details"]} == {"tags", "languages"}
    json.dumps(out)


def test_a_profile_repo_result_is_accepted_as_is(tmp_path):
    _, s = _session(tmp_path)
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "pyproject.toml").write_text('[project]\nname = "x"\n')
    prof = s.profile_repo(str(tmp_path / "repo"))
    out = s.search_skills("python types", profile=prof)
    assert "error" not in out and out["results"]


def test_path_ids_are_refused_in_auto_ids(tmp_path):
    root, s = _session(tmp_path)
    squash = skill_id(root, "commit-squash")
    out = s.resolve_set([f"path:{tmp_path}", squash])
    assert out["included"] == [squash]
    assert out["errors"] == [
        {"id": f"path:{tmp_path}", "error": "path: ids go in pinned_ids, not auto_ids"}
    ]


def test_oversized_manifests_are_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_mod, "MAX_MANIFEST_BYTES", 64)
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "1"}}) + " " * 64)
    (tmp_path / "go.mod").write_text("module x\n")
    out = profile_repo(tmp_path)
    assert out["skipped"] == ["package.json"]
    assert "react" not in out["frameworks"] and "go" in out["languages"]


def test_auto_ids_are_capped(tmp_path):
    root, s = _session(tmp_path)
    squash = skill_id(root, "commit-squash")
    out = s.resolve_set([squash] * (MAX_AUTO_IDS + 1))
    assert out == {
        "error": f"auto_ids: at most {MAX_AUTO_IDS} candidates per call (got {MAX_AUTO_IDS + 1}); "
        "pick fewer from the search results"
    }
    assert s.resolve_set([squash] * MAX_AUTO_IDS)["included"] == [squash]
