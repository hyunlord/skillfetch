"""`skillfetch sync`: pack an index for a release, download and verify it (no network: the
GitHub API and downloads go through a fake getter)."""

import io
import json
import tarfile

import pytest
from indexkit import make_index

from skillfetch.cli import main
from skillfetch.index import sync as s
from skillfetch.index.loader import Index

NAMES = ("commit-squash", "atomic-commits")


@pytest.fixture
def packed(tmp_path):
    index_dir = make_index(tmp_path, NAMES)
    tarball, checksum = s.pack(index_dir, tmp_path / "dist")
    return index_dir, tarball, checksum


def _github(tarball, checksum, *, tag="index-1", extra=()):
    """A getter serving one release listing and its two assets."""
    base = "https://github.com/o/r/releases/download"
    release = {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": tarball.name, "browser_download_url": f"{base}/{tag}/{tarball.name}"},
            {"name": checksum.name, "browser_download_url": f"{base}/{tag}/{checksum.name}"},
        ],
    }
    routes = {
        "https://api.github.com/repos/o/r/releases?per_page=30": json.dumps(
            [*extra, release]
        ).encode(),
        f"https://api.github.com/repos/o/r/releases/tags/{tag}": json.dumps(release).encode(),
        f"{base}/{tag}/{tarball.name}": tarball.read_bytes(),
        f"{base}/{tag}/{checksum.name}": checksum.read_bytes(),
    }
    seen = []

    def get(url, headers, limit):
        seen.append((url, headers, limit))
        return routes[url]

    get.seen = seen
    return get


def test_pack_is_reproducible_and_holds_only_manifest_files(packed, tmp_path):
    index_dir, tarball, checksum = packed
    again, _ = s.pack(index_dir, tmp_path / "dist2")
    assert tarball.read_bytes() == again.read_bytes()
    assert tarball.name.startswith("skillfetch-index-") and tarball.name.endswith(".tar.gz")
    assert checksum.read_text().split() == [s._sha256(tarball.read_bytes()), tarball.name]
    (index_dir / "stray.txt").write_text("not in the manifest")
    with tarfile.open(s.pack(index_dir, tmp_path / "dist3")[0]) as tar:
        names = tar.getnames()
    manifest = json.loads((index_dir / "manifest.json").read_text())
    assert sorted(names) == sorted(f"index/{n}" for n in ["manifest.json", *manifest["files"]])


def test_sync_installs_the_newest_release(packed, tmp_path):
    _, tarball, checksum = packed
    draft = {"tag_name": "draft", "draft": True, "assets": []}
    get = _github(tarball, checksum, extra=[draft])
    dest = tmp_path / "home" / "index"
    result = s.sync(dest, "o/r", get=get, token="t0ken")
    assert result.changed and result.source == f"o/r@index-1 ({tarball.name})"
    assert len(Index.load(dest).records) == 2
    api_headers = get.seen[0][1]
    assert api_headers["Authorization"] == "Bearer t0ken"
    # the token goes to the API only, not to the download host
    assert all("Authorization" not in h for url, h, _ in get.seen if "api.github.com" not in url)
    # every read carries a cap: the tarball 64 MB, listings and checksums 8 MB
    assert {limit for url, _, limit in get.seen if url.endswith(".tar.gz")} == {s.MAX_INDEX_BYTES}
    assert {limit for url, _, limit in get.seen if not url.endswith(".tar.gz")} == {
        s.MAX_META_BYTES
    }
    again = s.sync(dest, "o/r", get=_github(tarball, checksum))
    assert not again.changed


def test_sync_by_tag(packed, tmp_path):
    _, tarball, checksum = packed
    result = s.sync(
        tmp_path / "idx", "o/r", tag="index-7", get=_github(tarball, checksum, tag="index-7")
    )
    assert result.source.startswith("o/r@index-7")


def test_a_bad_checksum_leaves_the_old_index(packed, tmp_path):
    index_dir, tarball, checksum = packed
    dest = tmp_path / "idx"
    s.sync(dest, tarball=tarball)
    before = (dest / "manifest.json").read_bytes()
    checksum.write_text("0" * 64 + f"  {tarball.name}\n")
    with pytest.raises(s.SyncError, match="sha256 does not match"):
        s.sync(dest, "o/r", get=_github(tarball, checksum))
    assert (dest / "manifest.json").read_bytes() == before


def _tarball(tmp_path, members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "link":
                info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    path = tmp_path / "evil.tar.gz"
    path.write_bytes(buf.getvalue())
    return path


@pytest.mark.parametrize(
    "members, message",
    [
        ([("index/../../escape.txt", b"x", "file")], "outside index/"),
        ([("/abs.txt", b"x", "file")], "outside index/"),
        ([("index/link", b"", "link")], "not a regular file"),
        ([("other/manifest.json", b"{}", "file")], "outside index/"),
    ],
)
def test_unsafe_archives_are_refused(tmp_path, members, message):
    with pytest.raises(s.SyncError, match=message):
        s.sync(tmp_path / "idx", tarball=_tarball(tmp_path, members))
    assert not (tmp_path / "idx").exists() and not (tmp_path.parent / "escape.txt").exists()


def test_a_tarball_that_fails_its_manifest_is_refused(packed, tmp_path):
    index_dir, _, _ = packed
    (index_dir / "skills.jsonl").write_text("{}\n")  # no longer matches the manifest
    bad = _tarball(
        tmp_path,
        [(f"index/{p.name}", p.read_bytes(), "file") for p in sorted(index_dir.iterdir())],
    )
    with pytest.raises(s.SyncError, match="does not verify"):
        s.sync(tmp_path / "idx", tarball=bad)
    assert not (tmp_path / "idx").exists()


def test_no_release_with_an_index(tmp_path):
    def get(url, headers, limit):
        return json.dumps(
            [{"tag_name": "v1", "assets": [{"name": "x.whl", "browser_download_url": "u"}]}]
        ).encode()

    with pytest.raises(s.SyncError, match="no skillfetch-index-"):
        s.sync(tmp_path / "idx", "o/r", get=get)


def test_cli_pack_and_install(packed, tmp_path, capsys):
    index_dir, _, _ = packed
    assert main(["sync", "--pack", str(index_dir), "--out", str(tmp_path / "out")]) == 0
    tarball = next((tmp_path / "out").glob("*.tar.gz"))
    dest = tmp_path / "idx"
    assert main(["sync", "--from", str(tarball), "--index", str(dest)]) == 0
    assert "installed:" in capsys.readouterr().out
    assert main(["sync", "--from", str(tarball), "--index", str(dest)]) == 0
    assert "already up to date" in capsys.readouterr().out
    tarball.with_name(tarball.name + ".sha256").write_text("0" * 64 + "  x\n")
    assert main(["sync", "--from", str(tarball), "--index", str(dest)]) == 1
    assert "sha256 does not match" in capsys.readouterr().err


def test_unpacked_size_is_capped(packed, tmp_path, monkeypatch):
    _, tarball, _ = packed
    cap = tarball.stat().st_size  # the download passes; what it unpacks to does not
    monkeypatch.setattr(s, "MAX_INDEX_BYTES", cap)
    with pytest.raises(s.SyncError, match=f"more than {cap} bytes unpacked"):
        s.sync(tmp_path / "idx", tarball=tarball)
    assert not (tmp_path / "idx").exists()


def test_a_local_tarball_over_the_cap_is_not_read(packed, tmp_path, monkeypatch):
    _, tarball, _ = packed
    monkeypatch.setattr(s, "MAX_INDEX_BYTES", 10)
    with pytest.raises(s.SyncError, match="larger than 10 bytes"):
        s.sync(tmp_path / "idx", tarball=tarball)


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://api.github.com/repos/o/r/releases", True),
        ("https://github.com/o/r/releases/download/t/x.tar.gz", True),
        ("https://release-assets.githubusercontent.com/x", True),
        ("http://github.com/o/r", False),
        ("https://github.com.evil.example/x", False),
        ("https://evilgithubusercontent.com/x", False),
        ("https://169.254.169.254/latest", False),
        ("file:///etc/passwd", False),
    ],
)
def test_downloads_and_redirects_stay_on_github(url, ok):
    assert s._github_host(url) is ok
    if not ok:
        with pytest.raises(s.SyncError, match="refusing"):
            s.urllib_get(url, {}, 10)
