"""`skillfetch sync`: the published index, as a tarball on a GitHub release (index-format.md
§2). `pack` writes the tarball and its sha256 for a release; `sync` downloads the newest
release that carries one, checks the sha256, unpacks it, verifies every file against the
manifest (`Index.load`) and swaps it into place. Nothing is executed.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index, IndexLoadError

DEFAULT_REPO = "hyunlord/skillfetch"
ASSET_PREFIX = "skillfetch-index-"
ASSET_SUFFIX = ".tar.gz"
TOP = "index"  # every member of the tarball lives under index/
TIMEOUT_S = 60

Getter = Callable[[str, dict[str, str]], bytes]


class SyncError(RuntimeError):
    pass


def urllib_get(url: str, headers: dict[str, str]) -> bytes:
    if not url.startswith("https://"):
        raise SyncError(f"refusing to download {url!r}: https only")
    with urlopen(Request(url, headers=headers), timeout=TIMEOUT_S) as response:  # noqa: S310
        return response.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- pack (maintainers) -------------------------------------------------------------------


def asset_name(manifest: dict) -> str:
    built = (manifest.get("built_at") or "unknown").replace(":", "").replace("-", "")
    return f"{ASSET_PREFIX}{built}{ASSET_SUFFIX}"


def pack(index_dir: Path, out_dir: Path) -> tuple[Path, Path]:
    """The verified index as `<out>/skillfetch-index-<built_at>.tar.gz` plus a `.sha256`
    file. Only manifest.json and the files it lists go in; the archive is reproducible
    (sorted members, zero mtimes and owners)."""
    index = Index.load(index_dir)
    names = ["manifest.json", *sorted(index.manifest.get("files") or {})]
    buf = io.BytesIO()
    # gzip header mtime fixed too, so the same index packs to the same bytes
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT, compresslevel=9) as tar:
        for name in names:
            data = (index.root / name).read_bytes()
            info = tarfile.TarInfo(f"{TOP}/{name}")
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    data = _gzip_zero_mtime(buf.getvalue())
    out_dir.mkdir(parents=True, exist_ok=True)
    tarball = out_dir / asset_name(index.manifest)
    tarball.write_bytes(data)
    checksum = tarball.with_name(tarball.name + ".sha256")
    checksum.write_text(f"{_sha256(data)}  {tarball.name}\n")
    return tarball, checksum


def _gzip_zero_mtime(data: bytes) -> bytes:
    return data[:4] + b"\0\0\0\0" + data[8:]  # bytes 4-7 of a gzip header: MTIME


# --- sync (users) -------------------------------------------------------------------------


@dataclass
class Release:
    tag: str
    tarball_url: str
    checksum_url: str
    name: str


def find_release(repo: str, tag: str | None, get: Getter, headers: dict[str, str]) -> Release:
    """The release `tag`, or the newest release (drafts and pre-releases skipped) with an
    index tarball and its .sha256 attached."""
    api = f"https://api.github.com/repos/{repo}/releases"
    try:
        if tag:
            releases = [json.loads(get(f"{api}/tags/{tag}", headers))]
        else:
            releases = json.loads(get(f"{api}?per_page=30", headers))
    except (OSError, ValueError) as exc:
        raise SyncError(f"cannot list releases of {repo}: {exc}") from exc
    for rel in releases:
        if not tag and (rel.get("draft") or rel.get("prerelease")):
            continue
        assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
        for name, url in sorted(assets.items(), reverse=True):
            if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
                checksum = assets.get(name + ".sha256")
                if checksum:
                    return Release(rel["tag_name"], url, checksum, name)
    where = f"release {tag}" if tag else f"any release of {repo}"
    raise SyncError(f"no {ASSET_PREFIX}*{ASSET_SUFFIX} with a .sha256 on {where}")


def _members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Regular files under index/, nothing else: no links, devices, absolute paths or ..."""
    out = []
    for m in tar.getmembers():
        path = PurePosixPath(m.name)
        if m.isdir() and path.parts == (TOP,):
            continue
        if not m.isfile():
            raise SyncError(f"refusing archive member {m.name!r}: not a regular file")
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 2 or path.parts[0] != TOP:
            raise SyncError(f"refusing archive member {m.name!r}: outside {TOP}/")
        out.append(m)
    return out


def unpack(data: bytes, into: Path) -> Path:
    """Unpack a tarball into `into`; return the index directory (not yet verified)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for m in _members(tar):
                target = into.joinpath(*PurePosixPath(m.name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(m).read())
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise SyncError(f"cannot unpack the index tarball: {exc}") from exc
    return into / TOP


def install(data: bytes, dest: Path) -> Index:
    """Verify and swap a downloaded tarball into `dest`. The old index stays in place
    until the new one has passed `Index.load`."""
    dest = dest.expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".sync-", dir=dest.parent))
    try:
        new = unpack(data, work)
        try:
            Index.load(new)
        except IndexLoadError as exc:
            raise SyncError(f"downloaded index does not verify: {exc}") from exc
        old = work / "previous"
        if dest.exists():
            os.replace(dest, old)
        try:
            os.replace(new, dest)
        except OSError:
            if old.exists():
                os.replace(old, dest)  # put the previous index back
            raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return Index.load(dest)


def _same(dest: Path, data: bytes) -> bool:
    """`dest` already holds this tarball's index (same manifest bytes)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            new = tar.extractfile(f"{TOP}/manifest.json").read()
        return (dest / "manifest.json").read_bytes() == new and _verifies(dest)
    except (KeyError, OSError, tarfile.TarError, AttributeError):
        return False


def _verifies(dest: Path) -> bool:
    try:
        Index.load(dest)
    except IndexLoadError:
        return False
    return True


@dataclass
class SyncResult:
    source: str  # release tag or file path
    index: Index
    changed: bool


def sync(
    dest: Path = DEFAULT_INDEX_DIR,
    repo: str = DEFAULT_REPO,
    tag: str | None = None,
    tarball: Path | None = None,
    get: Getter = urllib_get,
    token: str | None = None,
) -> SyncResult:
    """Download (or read `tarball`), verify, install. A local tarball is checked against
    `<tarball>.sha256` when that file exists; a release tarball always is."""
    if tarball is not None:
        data, source = tarball.read_bytes(), str(tarball)
        checksum = tarball.with_name(tarball.name + ".sha256")
        expected = checksum.read_text().split()[0] if checksum.is_file() else None
    else:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "skillfetch-sync"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        release = find_release(repo, tag, get, headers)
        download = {"User-Agent": "skillfetch-sync"}
        try:
            data = get(release.tarball_url, download)
            expected = get(release.checksum_url, download).decode().split()[0]
        except (OSError, ValueError, IndexError) as exc:
            raise SyncError(f"cannot download {release.name}: {exc}") from exc
        source = f"{repo}@{release.tag} ({release.name})"
    if expected is not None and _sha256(data) != expected:
        raise SyncError(f"{source}: sha256 does not match its .sha256 file")
    dest = dest.expanduser()
    if _same(dest, data):
        return SyncResult(source, Index.load(dest), changed=False)
    return SyncResult(source, install(data, dest), changed=True)
