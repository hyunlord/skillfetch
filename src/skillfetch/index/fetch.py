"""Fetch a skill's files from its pinned source and verify them (index-format.md §1.8).

The only network access at runtime: GET <fetch_base>/<relpath> for the files listed in the
index record, each checked against its sha256. A verified folder is cached under
<cache>/<content_hash>/ and re-verified before every use. Nothing is executed.

The index is input, so nothing in a record is trusted: the content hash must be a sha256
hex digest (it names a directory that is replaced), fetch_base must be a
raw.githubusercontent.com URL (file:// only for skills of a `dir` source), redirects
must stay on the same host, and no file may exceed MAX_FILE_BYTES.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, build_opener

DEFAULT_BODY_CACHE = Path("~/.skillfetch/cache").expanduser()
FETCH_TIMEOUT_S = 20
MAX_FILE_BYTES = 8 * 1024 * 1024
GITHUB_RAW = "https://raw.githubusercontent.com/"
_SCHEMES = ("https://", "http://", "file://")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

Fetcher = Callable[[str], bytes]


class FetchError(RuntimeError):
    pass


class _SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlparse(req.full_url), urlparse(newurl)
        if (new.scheme, new.netloc) != (old.scheme, old.netloc):
            raise FetchError(f"refusing redirect from {old.netloc} to {new.scheme}://{new.netloc}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = build_opener(_SameHostRedirect)


def read_capped(response, limit: int, what: str) -> bytes:
    """At most `limit` bytes of a response, read as read(limit + 1): more is refused."""
    data = response.read(limit + 1)
    if len(data) > limit:
        raise FetchError(f"{what}: larger than {limit} bytes")
    return data


def urllib_fetch(url: str) -> bytes:
    if not url.startswith(_SCHEMES):
        raise FetchError(f"refusing to fetch {url!r}: unsupported scheme")
    with _OPENER.open(url, timeout=FETCH_TIMEOUT_S) as response:  # scheme checked above
        return read_capped(response, MAX_FILE_BYTES, url)


def _safe_rel(rel: str) -> PurePosixPath:
    path = PurePosixPath(rel)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise FetchError(f"refusing file path {rel!r} from the index")
    return path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verified(folder: Path, files: dict[str, str]) -> bool:
    """Every listed file is present in `folder` with its sha256."""
    for rel, digest in files.items():
        path = folder / _safe_rel(rel)
        if not path.is_file() or _sha256(path.read_bytes()) != digest:
            return False
    return True


@dataclass
class BodyCache:
    root: Path = DEFAULT_BODY_CACHE
    fetcher: Fetcher = urllib_fetch
    allowed: tuple[str, ...] = (GITHUB_RAW,)  # fetch_base prefixes (tests add a local server)

    def materialize(self, record: dict, allow_file: bool = False) -> Path:
        """The verified skill folder for an index record, fetched unless cached.
        `allow_file`: the record's source is a `dir` source, so file:// is expected.
        Raises FetchError on a missing manifest, a refused URL, a fetch error, an oversized
        file or any hash mismatch."""
        files, base = record.get("files") or {}, record.get("fetch_base")
        digest = record.get("content_hash")
        if not files or not base or not digest or "SKILL.md" not in files:
            raise FetchError("no file manifest in the index record; rebuild the index")
        if not isinstance(digest, str) or not _DIGEST.match(digest):
            raise FetchError(f"refusing content_hash {str(digest)[:80]!r}: not a sha256 digest")
        prefixes = self.allowed + (("file://",) if allow_file else ())
        if not isinstance(base, str) or not base.startswith(prefixes):
            raise FetchError(f"refusing fetch_base {str(base)[:120]!r}: not an allowed source")
        dest = self.root / digest
        if dest.is_dir() and verified(dest, files):
            return dest
        tmp = self.root / f".{digest}.{os.getpid()}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            for rel, want in sorted(files.items()):
                path = _safe_rel(rel)
                url = f"{base.rstrip('/')}/{quote(str(path))}"
                try:
                    data = self.fetcher(url)
                except FetchError:
                    raise
                except Exception as exc:  # network errors of any kind refuse the skill
                    raise FetchError(f"{rel}: fetch failed ({type(exc).__name__}: {exc})") from exc
                if len(data) > MAX_FILE_BYTES:
                    raise FetchError(f"{rel}: larger than {MAX_FILE_BYTES} bytes")
                got = _sha256(data)
                if got != want:
                    raise FetchError(f"{rel}: sha256 mismatch (index {want[:12]}, got {got[:12]})")
                (tmp / path).parent.mkdir(parents=True, exist_ok=True)
                (tmp / path).write_bytes(data)
            shutil.rmtree(dest, ignore_errors=True)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp.rename(dest)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return dest
