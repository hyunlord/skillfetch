"""sources.yaml (index-format.md §1.1)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from skillfetch.ingest.sources import Source, load_sources

REPO = Path(__file__).parent.parent.parent


def test_repo_sources_file_loads():
    sources = load_sources(REPO / "sources.yaml")
    by_id = {s.id: s for s in sources}
    anthropics = by_id["anthropics-skills"]
    assert (anthropics.kind, anthropics.root, anthropics.publisher_trust) == (
        "git",
        "skills/",
        "verified",
    )
    assert anthropics.license == "per-skill"
    uasl = by_id["uasl"]
    assert (uasl.publisher_trust, uasl.license, uasl.root) == ("unknown", "per-skill", "skills/")
    assert uasl.third_party_doc == "docs/THIRD_PARTY_SOURCE_REPOS.md"


def test_git_source_needs_a_ref():
    with pytest.raises(ValidationError, match="need a ref"):
        Source(id="x", kind="git", url="u", publisher="p", publisher_trust="known")


def test_duplicate_ids_rejected(tmp_path):
    entry = "- {id: a, kind: dir, url: /tmp/a, publisher: p, publisher_trust: unknown}\n"
    path = tmp_path / "sources.yaml"
    path.write_text(entry * 2)
    with pytest.raises(ValueError, match="duplicate"):
        load_sources(path)
