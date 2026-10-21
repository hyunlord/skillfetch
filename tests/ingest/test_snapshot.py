"""Snapshot stage (index-format.md §1.2), against local git repos (no network)."""

import pytest
from conftest import SKILLS_DIR, make_git_source

from skillfetch.ingest.snapshot import SnapshotError, snapshot
from skillfetch.ingest.sources import Source


def _source(url, ref="main", kind="git"):
    return Source(
        id="demo",
        kind=kind,
        url=url,
        ref=ref,
        root="skills/",
        publisher="p",
        publisher_trust="known",
    )


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "origin"
    path.mkdir()
    commit = make_git_source(path, {"commit-squash": SKILLS_DIR / "commit-squash"})
    return path, commit


def test_clone_is_keyed_by_the_resolved_commit(tmp_path, repo):
    origin, commit = repo
    snap = snapshot(_source(f"file://{origin}"), tmp_path / "work")
    assert snap.commit == commit
    assert snap.path == tmp_path / "work" / "demo" / commit
    assert (snap.skills_root / "commit-squash" / "SKILL.md").is_file()
    assert snap.commit_date and snap.commit_date[:4].isdigit()


def test_existing_snapshot_is_reused(tmp_path, repo):
    origin, _ = repo
    first = snapshot(_source(f"file://{origin}"), tmp_path / "work")
    marker = first.path / "marker"
    marker.write_text("x")
    second = snapshot(_source(f"file://{origin}"), tmp_path / "work")
    assert second.path == first.path and marker.exists()


def test_ref_can_be_a_pinned_commit(tmp_path, repo):
    origin, commit = repo
    snap = snapshot(_source(f"file://{origin}", ref=commit), tmp_path / "work")
    assert snap.commit == commit and (snap.skills_root / "commit-squash").is_dir()


def test_unknown_ref_is_an_error(tmp_path, repo):
    origin, _ = repo
    with pytest.raises(SnapshotError, match="no-such-branch"):
        snapshot(_source(f"file://{origin}", ref="no-such-branch"), tmp_path / "work")


def test_dir_sources_are_used_in_place(tmp_path, repo):
    origin, _ = repo
    snap = snapshot(_source(str(origin), ref=None, kind="dir"), tmp_path / "work")
    assert snap.path == origin and snap.commit == "local"
