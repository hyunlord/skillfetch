"""Dedup rules 3 and 4 (same name: same publisher at different commits; one source with
collapse_same_name) and upstream repo names."""

from pathlib import Path

import pytest

from skillfetch.ingest.build import Built, SkillRecord, dedup
from skillfetch.ingest.snapshot import Snapshot
from skillfetch.ingest.sources import Source
from skillfetch.ingest.upstream_licenses import read_repo


def _built(sid, name, publisher, commit, date, digest, path=None):
    source = Source(id=sid, kind="dir", url="/x", publisher=publisher, publisher_trust="known")
    rid = f"{sid}/{name}@{digest[:12]}"
    record = SkillRecord(
        id=rid, canonical_id=rid, name=name, title=name, description="", source_id=sid,
        publisher=publisher, publisher_trust="known", commit=commit, path=path or name,
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


def _copies(paths):
    return [
        _built("ecc", "pdf", "acme", "a" * 40, None, f"{i}" * 64, path)
        for i, path in enumerate(paths, 1)
    ]


def test_collapse_same_name_groups_translations_under_the_copy_without_a_locale():
    copies = _copies(
        ["docs/ja-JP/skills/pdf", "docs/es/skills/pdf", "pi/core/skills/pdf", "skills/pdf"]
    )
    groups = dedup(copies, frozenset({"ecc"}))
    canon = copies[3].record.id
    assert groups == {canon: sorted(b.record.id for b in copies)}
    assert {b.record.canonical_id for b in copies} == {canon}


def test_collapse_same_name_prefers_a_bare_folder_that_is_not_a_locale():
    # es sits next to ja-JP, so it is a locale; pi has no tagged sibling, so it is not
    copies = _copies(["docs/ja-JP/skills/pdf", "docs/es/skills/pdf", "pi/core/skills/pdf"])
    dedup(copies, frozenset({"ecc"}))
    assert {b.record.canonical_id for b in copies} == {copies[2].record.id}
    shallow = _copies(["docs/zh-CN/pdf", "docs/zh-TW/skills/pdf", "docs/es/skills/pdf"])
    dedup(shallow, frozenset({"ecc"}))  # all localized: the shallower path wins
    assert {b.record.canonical_id for b in shallow} == {shallow[0].record.id}


def test_without_collapse_same_name_the_copies_stay_separate():
    copies = _copies(["docs/ja-JP/skills/pdf", "skills/pdf"])
    assert dedup(copies) == {} and dedup(copies, frozenset({"other"})) == {}
    assert [b.record.canonical_id for b in copies] == [b.record.id for b in copies]


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
