"""Organisation rules (index-format.md §4.1): `.skillfetch.yaml` in profile_repo, baseline
names resolved against the index, `org: true` on search results, and the org router
variant's extra picks under load_skills' budget. No network, no model."""

import json
from pathlib import Path
from urllib.request import urlopen

from indexkit import make_index, skill_id

from skillfetch.index.fetch import BodyCache
from skillfetch.index.loader import Index
from skillfetch.index.profile import MAX_BASELINE, ORG_FILE, org_config, profile_repo
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.session import Session

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ["add type annotations to a python module", "write tests first", "python"]


def _repo(tmp_path, config: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    (repo / "pyproject.toml").write_text('[project]\nname = "x"\ndependencies = ["pytest"]\n')
    if config is not None:
        (repo / ORG_FILE).write_text(config)
    return repo


def _session(tmp_path, root) -> Session:
    return Session(
        Index.load(root),
        extract_cache=ExtractCache(tmp_path / "xc"),
        bodies=BodyCache(tmp_path / "bodies", lambda url: urlopen(url).read()),
    )


# --- profile_repo -----------------------------------------------------------------------


def test_without_the_file_the_profile_is_unchanged(tmp_path):
    repo = _repo(tmp_path)
    p = profile_repo(repo)
    assert set(p) == {"path", "languages", "frameworks", "package_managers", "tags", "manifests"}
    assert ORG_FILE not in p["manifests"]
    s = _session(tmp_path, make_index(tmp_path / "i"))
    assert s.profile_repo(str(repo)) == p


def test_the_file_gives_org_and_baseline_names(tmp_path):
    repo = _repo(tmp_path, "org: acme\nbaseline:\n  - acme-style\n  - acme-style\n  - x/y\n")
    p = profile_repo(repo)
    assert p["org"] == "acme"
    assert p["baseline"] == ["acme-style", "x/y"]  # repeated names collapse
    assert ORG_FILE in p["manifests"]
    assert "org_errors" not in p
    assert p["languages"] == ["python"]  # the rest of the profile is as before


def test_bad_files_are_reported_not_fatal(tmp_path):
    def cfg(text):
        (tmp_path / ORG_FILE).write_text(text)
        return org_config(tmp_path)

    assert cfg("org: [1\n")["org_errors"][0].endswith("not YAML (ParserError)")
    assert cfg("- a\n- b\n") == {
        "org": None,
        "baseline": [],
        "org_errors": [f"{ORG_FILE}: expected a mapping with org and baseline"],
    }
    out = cfg("org: 3\nbaseline: [ok, 7, '']\n")
    assert out["org"] is None and out["baseline"] == ["ok"]
    assert len(out["org_errors"]) == 3
    many = cfg("baseline:\n" + "".join(f"  - s{i}\n" for i in range(MAX_BASELINE + 5)))
    assert len(many["baseline"]) == MAX_BASELINE
    assert "the first 20 are used" in many["org_errors"][0]
    assert cfg("") == {"org": None, "baseline": []}


# --- names to ids -----------------------------------------------------------------------


def test_baseline_names_resolve_to_index_ids(tmp_path):
    root = make_index(tmp_path / "i")
    repo = _repo(tmp_path, "org: fx\nbaseline: [typed-python, fx/pnpm-only, no-such-skill]\n")
    p = _session(tmp_path, root).profile_repo(str(repo))
    assert p["org"] == "fx"
    assert p["baseline"] == [skill_id(root, "typed-python"), skill_id(root, "pnpm-only")]
    assert p["baseline_unresolved"] == [
        {"name": "no-such-skill", "reason": "no indexed skill with this name"}
    ]
    assert "org_errors" not in p
    full = _repo(tmp_path / "b", f"baseline: [{skill_id(root, 'tdd-strict')}]\n")
    assert _session(tmp_path, root).profile_repo(str(full))["baseline"] == [
        skill_id(root, "tdd-strict")
    ]


def test_a_name_in_two_sources_needs_the_org_or_a_source(tmp_path):
    root = make_index(tmp_path / "i")
    s = _session(tmp_path, root)
    fx = skill_id(root, "typed-python")
    other = {**s.index.records[fx], "source_id": "other"}
    other["id"] = other["canonical_id"] = "other/typed-python@000000000000"
    s.index.records[other["id"]] = other
    ids, unresolved = s._baseline_ids(None, ["typed-python"])
    assert ids == [] and unresolved[0]["candidates"] == sorted([fx, other["id"]])
    assert s._baseline_ids("fx", ["typed-python"]) == ([fx], [])
    assert s._baseline_ids("fx", ["other/typed-python"]) == ([other["id"]], [])


def test_an_org_the_index_does_not_have_is_reported(tmp_path):
    root = make_index(tmp_path / "i")
    repo = _repo(tmp_path, "org: acme\nbaseline: [typed-python]\n")
    p = _session(tmp_path, root).profile_repo(str(repo))
    assert p["baseline"] == [skill_id(root, "typed-python")]  # the only skill of that name
    assert p["org_errors"] == ["org 'acme' is not a source of this index"]


# --- search: org: true ------------------------------------------------------------------


def test_org_marks_results_and_keeps_the_ranking(tmp_path):
    root = make_index(tmp_path / "i")
    s = _session(tmp_path, root)
    base = {"languages": ["python"], "frameworks": [], "package_managers": [], "tags": []}
    plain = s.search_skills(queries=QUERIES, profile=base)["results"]
    marked = s.search_skills(queries=QUERIES, profile={**base, "org": "fx"})["results"]
    other = s.search_skills(queries=QUERIES, profile={**base, "org": "acme"})["results"]
    assert [r["id"] for r in marked] == [r["id"] for r in plain]
    assert all(r["org"] is True for r in marked)  # every fixture skill is in source fx
    assert [{k: v for k, v in r.items() if k != "org"} for r in marked] == plain
    assert other == plain and not any("org" in r for r in plain)


# --- the org variant's picks ------------------------------------------------------------


def test_baseline_pinned_and_extra_org_picks_under_the_budget(tmp_path):
    """The variant's request: baseline as pinned, 3 picks plus up to 3 org picks as auto.
    Pinned comes first and stays; over the budget the last org picks are dropped first."""
    root = make_index(tmp_path / "i")
    s = _session(tmp_path, root)
    baseline = [skill_id(root, "typed-python")]
    picks = [skill_id(root, n) for n in ("tdd-strict", "pnpm-only", "commit-squash")]
    org_extra = [skill_id(root, n) for n in ("clean-headings", "emoji-headers", "npm-classic")]
    out = s.resolve_and_load(picks + org_extra, baseline)
    assert out["errors"] == [] and out["included"][0] == baseline[0]
    excluded = {e["id"] for e in out["excluded"]}  # the fixtures' known conflicts
    assert excluded == {skill_id(root, "emoji-headers"), skill_id(root, "npm-classic")}
    kept = [i for i in [*baseline, *picks, *org_extra] if i not in excluded]
    assert out["included"] == kept
    assert all(f"({i})" in out["content"] for i in kept)  # all fit in 8,000 tokens

    tight = s.resolve_and_load(picks + org_extra, baseline, max_tokens=60)
    dropped = [e["id"] for e in tight["errors"] if "over max_tokens" in e["error"]]
    assert dropped and dropped == kept[::-1][: len(dropped)]  # from the end
    assert baseline[0] not in dropped or len(dropped) == len(kept)


def test_the_org_variant_differs_only_where_it_says(tmp_path):
    shipped = (ROOT / "assets/router-skill/SKILL.md").read_text()
    variant = (ROOT / "assets/router-skill/variants/org.md").read_text()
    assert len(variant.splitlines()) <= 60
    head = shipped.split("4. Call `search_skills`")[0]
    tail = shipped.split("6. Call `resolve_set`")[1]
    assert variant.startswith(head) and variant.endswith(tail)
    flat = " ".join(variant.split())
    for phrase in (
        "unless there are baseline ids, skip steps 6–7",
        "`org: true` results (your organisation's) in the top 10 may add up to 3 more picks",
        "(8000 tokens by default)",
        "Pin the profile's `baseline` ids.",
    ):
        assert phrase in flat, phrase
    assert json.dumps(shipped) != json.dumps(variant)
