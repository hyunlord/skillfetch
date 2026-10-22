"""Fetch a skill's files from its pinned source and verify them (index-format.md §1.8).

The only network access at runtime: GET <fetch_base>/<relpath> for the files listed in the
index record, each checked against its sha256. A verified folder is cached under
<cache>/<content_hash>/ and re-verified before every use. Nothing is executed.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import urlopen

DEFAULT_BODY_CACHE = Path("~/.skillfetch/cache").expanduser()
FETCH_TIMEOUT_S = 20
_SCHEMES = ("https://", "http://", "file://")

Fetcher = Callable[[str], bytes]


class FetchError(RuntimeError):
    pass


def urllib_fetch(url: str) -> bytes:
    if not url.startswith(_SCHEMES):
        raise FetchError(f"refusing to fetch {url!r}: unsupported scheme")
    with urlopen(url, timeout=FETCH_TIMEOUT_S) as response:  # noqa: S310 (scheme checked)
        return response.read()


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

    def materialize(self, record: dict) -> Path:
        """The verified skill folder for an index record, fetched unless cached.
        Raises FetchError on a missing manifest, a fetch error or any hash mismatch."""
        files, base = record.get("files") or {}, record.get("fetch_base")
        digest = record.get("content_hash")
        if not files or not base or not digest or "SKILL.md" not in files:
            raise FetchError("no file manifest in the index record; rebuild the index")
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
