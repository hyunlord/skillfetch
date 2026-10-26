"""#26 options (docs/design/router-cost.md), off by default: the server-side profile and
the summary length. No network."""

from indexkit import make_index

from skillfetch.cli import main
from skillfetch.index.loader import Index
from skillfetch.index.search import ONE_LINE_CHARS
from skillfetch.mcp.session import Session

QUERIES = ["add type annotations to a python module", "write tests first", "python"]


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["fastapi", "pydantic"]\n'
        '[dependency-groups]\ndev = ["pytest>=8"]\n'
    )
    return repo


def test_defaults_are_unchanged(tmp_path):
    s = Session(Index.load(make_index(tmp_path / "i")))
    assert s.profile_root is None and s.summary_chars == ONE_LINE_CHARS == 160
    plain = s.search_skills(queries=QUERIES, verbose=True)["results"]
    assert not any("profile tag" in " ".join(r["match_reasons"]) for r in plain)


def test_auto_profile_equals_passing_profile_repo(tmp_path):
    """Pre-check 1: with profile_root, a search without `profile` returns exactly what the
    router gets today by calling profile_repo(root) and passing the result."""
    index = Index.load(make_index(tmp_path / "i"))
    repo = _repo(tmp_path)
    today = Session(index)
    expected = today.search_skills(
        queries=QUERIES, profile=today.profile_repo(str(repo)), verbose=True
    )
    # the profile does change the ranking here (a python repo boosts python-tagged skills)
    assert any("profile tag" in " ".join(r["match_reasons"]) for r in expected["results"])
    auto = Session(index, profile_root=repo)
    assert auto.search_skills(queries=QUERIES, verbose=True) == expected
    # the compact results too, and an explicit profile still wins
    assert auto.search_skills(queries=QUERIES) == today.search_skills(
        queries=QUERIES, profile=today.profile_repo(str(repo))
    )
    other = {"languages": ["go"], "frameworks": [], "package_managers": [], "tags": ["go"]}
    assert auto.search_skills(queries=QUERIES, profile=other) == today.search_skills(
        queries=QUERIES, profile=other
    )


def test_summary_chars_cuts_summaries_and_keeps_the_ranking(tmp_path):
    index = Index.load(make_index(tmp_path / "i"))
    long = Session(index).search_skills(queries=QUERIES)["results"]
    short = Session(index, summary_chars=80).search_skills(queries=QUERIES)["results"]
    assert [r["id"] for r in short] == [r["id"] for r in long]
    assert all(len(r["summary"]) <= 80 for r in short)
    assert all(len(r["summary"]) <= 160 for r in long)
    assert any(len(r["summary"]) > 80 for r in long) or all(
        a["summary"] == b["summary"] for a, b in zip(long, short, strict=True)
    )


def test_serve_flags(tmp_path, monkeypatch):
    import skillfetch.mcp.server as server

    seen = {}
    monkeypatch.setattr(server, "serve", lambda index, **kw: seen.update(index=index, **kw))
    monkeypatch.chdir(tmp_path)
    assert main(["serve", "--index", str(tmp_path)]) == 0
    assert seen["profile_root"] is None and seen["summary_chars"] == 160
    assert main(["serve", "--index", str(tmp_path), "--auto-profile", "--summary-chars", "80"]) == 0
    assert seen["profile_root"] == tmp_path and seen["summary_chars"] == 80
