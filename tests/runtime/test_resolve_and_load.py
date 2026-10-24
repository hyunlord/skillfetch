"""resolve_and_load: resolve_set and load_skills in one call, with the same result."""

import json
from urllib.request import urlopen

from conftest import SKILLS_DIR
from indexkit import make_index, skill_id

from skillfetch.index.fetch import BodyCache
from skillfetch.index.loader import Index
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.session import MAX_AUTO_IDS, Session


class Recorder:
    def __init__(self):
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        with urlopen(url) as r:
            return r.read()


def _session(tmp_path, root, name):
    fetcher = Recorder()
    session = Session(
        Index.load(root),
        extract_cache=ExtractCache(tmp_path / f"xc-{name}"),
        bodies=BodyCache(tmp_path / f"bodies-{name}", fetcher),
    )
    return session, fetcher


def _both(tmp_path, auto, pinned, **kw):
    """The same request through resolve_set + load_skills and through resolve_and_load,
    each on a fresh session and body cache."""
    root = make_index(tmp_path)
    auto, pinned = [skill_id(root, n) for n in auto], [skill_id(root, n) for n in pinned]
    two, _ = _session(tmp_path, root, "two")
    resolved = two.resolve_set(auto, pinned)
    loaded = two.load_skills(resolved["set_id"], **kw)
    one, fetcher = _session(tmp_path, root, "one")
    return root, resolved, loaded, one.resolve_and_load(auto, pinned, **kw), fetcher


def test_the_result_equals_the_two_calls(tmp_path):
    _, resolved, loaded, out, _ = _both(
        tmp_path, ["commit-squash", "atomic-commits", "npm-classic", "typed-python"], ["pnpm-only"]
    )
    assert len(resolved["excluded"]) == 2  # atomic-commits and npm-classic
    for key in ("set_id", "included", "excluded", "warnings", "notes"):
        assert out[key] == resolved[key]
    assert out["content"] == loaded["content"]
    assert out["errors"] == resolved["errors"] + loaded["errors"]
    assert set(out) == {
        "set_id", "included", "excluded", "warnings", "notes", "content", "errors"
    }  # fmt: skip
    json.dumps(out)


def test_excluded_skills_are_not_loaded(tmp_path):
    root, _, _, out, fetcher = _both(tmp_path, ["commit-squash", "atomic-commits"], [])
    atomic = skill_id(root, "atomic-commits")
    assert [e["id"] for e in out["excluded"]] == [atomic]
    assert "Never squash" not in out["content"] and "Squash every feature" in out["content"]
    base = Index.load(root).records[atomic]["fetch_base"]
    assert not [u for u in fetcher.urls if u.startswith(base)]


def test_pinned_is_handled_as_in_resolve_set(tmp_path):
    root, resolved, loaded, out, _ = _both(tmp_path, ["commit-squash"], ["atomic-commits"])
    squash, atomic = skill_id(root, "commit-squash"), skill_id(root, "atomic-commits")
    assert out["included"] == resolved["included"] == [atomic]
    assert out["excluded"][0]["id"] == squash
    assert out["content"] == loaded["content"] and "Never squash" in out["content"]


def test_a_pinned_local_path_loads_from_disk(tmp_path):
    root = make_index(tmp_path)
    s, _ = _session(tmp_path, root, "one")
    local = f"path:{SKILLS_DIR / 'gitmoji-commits'}"
    out = s.resolve_and_load([skill_id(root, "commit-squash")], [local])
    assert out["included"][0] == local and "no extracted constraints" in out["notes"][0]
    assert out["content"].startswith("## 1. ") and out["errors"] == []


def test_over_max_tokens_and_input_errors_are_reported_as_in_the_two_tools(tmp_path):
    _, _, loaded, out, _ = _both(tmp_path, ["commit-squash", "typed-python"], [], max_tokens=1)
    assert out["errors"] == loaded["errors"] and out["errors"]
    root = make_index(tmp_path / "x")
    s, _ = _session(tmp_path, root, "x")
    too_many = [f"s{i}@0" for i in range(MAX_AUTO_IDS + 1)]
    assert s.resolve_and_load(too_many) == s.resolve_set(too_many)
