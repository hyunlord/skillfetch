"""Dedup rule 3 (same name and publisher at different commits) and upstream repo names."""

from pathlib import Path

import pytest

from skillfetch.ingest.build import Built, SkillRecord, dedup
from skillfetch.ingest.snapshot import Snapshot
from skillfetch.ingest.sources import Source
from skillfetch.ingest.upstream_licenses import read_repo


def _built(sid, name, publisher, commit, date, digest):
    source = Source(id=sid, kind="dir", url="/x", publisher=publisher, publisher_trust="known")
    rid = f"{sid}/{name}@{digest[:12]}"
    record = SkillRecord(
        id=rid, canonical_id=rid, name=name, title=name, description="", source_id=sid,
        publisher=publisher, publisher_trust="known", commit=commit, path=name,
        source_url="", content_hash=digest, status="ok", token_estimate=1,
        license="unknown", redistributable=False, license_origin="none",
    )  # fmt: skip
    return Built(record, Path("/x"), Snapshot(source, Path("/x"), commit, date))


def test_same_name_and_publisher_at_different_commits_keep_the_newest():
    old = _built("mirror-a", "pdf", "acme", "a" * 40, "2026-01-01T00:00:00Z", "1" * 64)
    new = _built("mirror-b", "PDF", "acme", "b" * 40, "2026-06-01T00:00:00Z", "2" * 64)
    other = _built("mirror-c", "pdf", "someone-else", "c" * 40, "2026-07-01T00:00:00Z", "3" * 64)
    groups = dedup([old, new, other])
    assert groups == {new.record.id: sorted([old.record.id, new.record.id])}
    assert old.record.canonical_id == new.record.id
    assert other.record.canonical_id == other.record.id


def test_same_name_at_the_same_commit_is_not_a_duplicate():
    a = _built("s", "pdf", "acme", "a" * 40, None, "1" * 64)
    b = _built("s", "pdf", "acme", "a" * 40, None, "2" * 64)
    assert dedup([a, b]) == {}


class _NoCalls:
    def get(self, path):
        raise AssertionError(f"no request expected, got {path}")


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/../x",
        "https://github.com/owner/..",
        "https://github.com/owner/a..b",
        "https://github.com/ow?ner/repo",
        "https://github.com/%2e%2e/repo",
        "https://github.com/-owner/repo",
    ],
)
def test_odd_owner_or_repo_names_are_not_requested(tmp_path, url):
    out = read_repo(_NoCalls(), url, tmp_path)
    assert out.status == "unreachable"
    assert list(tmp_path.iterdir()) == []
