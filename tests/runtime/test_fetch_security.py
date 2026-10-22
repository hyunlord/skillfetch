"""Regression tests for the body fetch: a hostile index record must not delete, read or
download anything outside what the index format allows."""

import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from skillfetch.index import fetch
from skillfetch.index.fetch import BodyCache, FetchError, urllib_fetch

DIGEST = "a" * 64


def _record(**over):
    body = b"---\nname: x\ndescription: y\n---\n"
    rec = {
        "content_hash": DIGEST,
        "fetch_base": "https://raw.githubusercontent.com/o/r/0123/skills/x",
        "files": {"SKILL.md": hashlib.sha256(body).hexdigest()},
    }
    rec.update(over)
    return rec, body


@pytest.mark.parametrize("digest", ["../../victim", "..", "/tmp/x", "A" * 64, "a" * 63, ""])
def test_content_hash_must_be_a_digest_before_anything_is_removed(tmp_path, digest):
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep")
    root = tmp_path / "bodies" / "sub"
    root.mkdir(parents=True)
    rec, body = _record(content_hash=digest)
    with pytest.raises(FetchError):
        BodyCache(root, lambda url: body).materialize(rec)
    assert (victim / "keep.txt").read_text() == "keep"


@pytest.mark.parametrize(
    "base",
    [
        "https://evil.example/skills/x",
        "http://raw.githubusercontent.com/o/r/0123/x",
        "https://raw.githubusercontent.com.evil.example/x",
        "file:///etc",
        "ftp://raw.githubusercontent.com/x",
    ],
)
def test_fetch_base_must_be_github_raw(tmp_path, base):
    rec, body = _record(fetch_base=base)
    urls = []
    with pytest.raises(FetchError, match="refusing fetch_base"):
        BodyCache(tmp_path, lambda url: urls.append(url) or body).materialize(rec)
    assert urls == []


def test_file_urls_only_for_dir_sources(tmp_path):
    src = tmp_path / "skill"
    src.mkdir()
    rec, body = _record(fetch_base=src.as_uri())
    (src / "SKILL.md").write_bytes(body)
    with pytest.raises(FetchError, match="refusing fetch_base"):
        BodyCache(tmp_path / "c", urllib_fetch).materialize(rec)
    folder = BodyCache(tmp_path / "c", urllib_fetch).materialize(rec, allow_file=True)
    assert (folder / "SKILL.md").read_bytes() == body


def test_oversized_files_are_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_FILE_BYTES", 16)
    rec, _ = _record()
    big = b"x" * 17
    rec["files"] = {"SKILL.md": hashlib.sha256(big).hexdigest()}
    with pytest.raises(FetchError, match="larger than 16 bytes"):
        BodyCache(tmp_path, lambda url: big).materialize(rec)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        if self.path == "/big":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"x" * 64)
        elif self.path == "/same":
            self.send_response(302)
            self.send_header("Location", "/big")
            self.end_headers()
        else:  # off-host redirect
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_redirects_stay_on_the_same_host(server):
    with pytest.raises(FetchError, match="refusing redirect"):
        urllib_fetch(f"{server}/elsewhere")


def test_network_reads_are_capped(server, monkeypatch):
    monkeypatch.setattr(fetch, "MAX_FILE_BYTES", 32)
    with pytest.raises(FetchError, match="larger than 32 bytes"):
        urllib_fetch(f"{server}/same")  # same-host redirect is followed, then capped
    monkeypatch.setattr(fetch, "MAX_FILE_BYTES", 64)
    assert urllib_fetch(f"{server}/big") == b"x" * 64


def test_read_capped_reads_one_byte_past_the_limit():
    class R:
        def __init__(self):
            self.asked = []

        def read(self, n):
            self.asked.append(n)
            return b"y" * n

    r = R()
    with pytest.raises(FetchError):
        fetch.read_capped(r, 10, "u")
    assert r.asked == [11]


@pytest.mark.parametrize("rel", ["..\\..\\x", "a\\b.md", "C:x", "C:/x", "refs/a:b", "../x", "/x"])
def test_index_file_paths_with_separators_or_drives_are_refused(tmp_path, rel):
    rec, body = _record()
    rec["files"][rel] = rec["files"]["SKILL.md"]
    urls = []
    with pytest.raises(FetchError, match="refusing file path"):
        BodyCache(tmp_path / "c", lambda url: urls.append(url) or body).materialize(rec)
    assert not (tmp_path / "x").exists()


def test_a_joined_path_must_stay_under_its_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "outside").mkdir()
    (root / "sub").symlink_to(tmp_path / "outside", target_is_directory=True)
    assert fetch.safe_join(root, "a/b.md") == root / "a" / "b.md"
    with pytest.raises(FetchError, match="outside"):
        fetch.safe_join(root, "sub/x.md")
    with pytest.raises(FetchError, match="outside"):
        fetch.verified(root, {"sub/x.md": DIGEST})
