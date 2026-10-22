"""Index loader and BM25 (index-format.md §2, §4)."""

import json

import pytest
from indexkit import make_index, skill_id

from skillfetch.index.bm25 import BM25, tokenize
from skillfetch.index.loader import Index, IndexLoadError


def test_load_a_built_index(tmp_path):
    root = make_index(tmp_path)
    index = Index.load(root)
    assert len(index.records) == 8
    squash = index.skill(skill_id(root, "commit-squash"))
    assert squash.constraints[0].subject == "commit-granularity"
    assert index.records[squash.id]["files"]["SKILL.md"]
    assert {r["id"] for r in index.canonical()} == set(index.records)


def test_missing_index_is_reported(tmp_path):
    with pytest.raises(IndexLoadError, match="missing manifest.json"):
        Index.load(tmp_path / "nope")


def test_a_tampered_file_fails_the_manifest_check(tmp_path):
    root = make_index(tmp_path)
    path = root / "constraints.jsonl"
    rows = path.read_text().splitlines()
    first = json.loads(rows[0])
    first["directive"] = "forbid" if first["directive"] != "forbid" else "require"
    path.write_text("\n".join([json.dumps(first), *rows[1:]]) + "\n")
    with pytest.raises(IndexLoadError, match="constraints.jsonl does not match"):
        Index.load(root)


def test_tokenize_drops_stopwords_and_punctuation():
    assert tokenize("Refactor the React components, please!") == [
        "refactor",
        "react",
        "components",
        "please",
    ]


def test_bm25_ranks_rarer_and_repeated_terms_higher():
    bm = BM25()
    bm.add("a", {"title": "python type hints", "keywords": "python"}, {"keywords": 2})
    bm.add("b", {"title": "python packaging"})
    bm.add("c", {"title": "markdown emoji"})
    ranked = bm.scores("python type hints")
    assert [d.id for d, _, _ in ranked] == ["a", "b"]
    assert ranked[0][2] == ["python", "type", "hints"]
    assert bm.scores("rust") == []
