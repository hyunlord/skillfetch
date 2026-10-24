"""Snapshot stage (index-format.md §1.2): a source at one commit, on local disk.

Git sources are shallow-cloned into work/<source_id>/<commit>/ and reused while the ref
resolves to the same commit. `dir` sources are used in place.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from skillfetch.ingest.sources import Source

DEFAULT_WORK_DIR = Path("~/.skillfetch/work").expanduser()
_SHA = re.compile(r"^[0-9a-f]{40}$")
# git transports are code paths of their own (ext::, ssh options, file): https only. The
# test suite adds file:// for its local fixture repos.
GIT_URL_PREFIXES: tuple[str, ...] = ("https://",)


class SnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class Snapshot:
    source: Source
    path: Path
    commit: str  # full sha; "local" for dir sources
    commit_date: str | None  # ISO 8601 committer date

    @property
    def skills_root(self) -> Path:
        return self.path / self.source.root

    @property
    def skills_roots(self) -> list[Path]:
        """The directories discovery starts from: `roots` when given, else `root`."""
        return [self.path / r for r in self.source.roots] or [self.skills_root]


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SnapshotError(f"git {' '.join(args[:2])} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _check_git_source(url: str, ref: str) -> None:
    if not url.startswith(GIT_URL_PREFIXES):
        raise SnapshotError(f"refusing git url {url!r}: only {', '.join(GIT_URL_PREFIXES)}")
    if ref.startswith("-"):
        raise SnapshotError(f"refusing ref {ref!r}")


def resolve_ref(url: str, ref: str) -> str:
    _check_git_source(url, ref)
    if _SHA.match(ref):
        return ref
    out = _git("ls-remote", "--", url, ref)
    for line in out.splitlines():
        sha, name = line.split("\t", 1)
        if name in (f"refs/heads/{ref}", f"refs/tags/{ref}", f"refs/tags/{ref}^{{}}", ref):
            return sha
    raise SnapshotError(f"ref {ref!r} not found in {url}")


def snapshot(source: Source, work_dir: Path = DEFAULT_WORK_DIR) -> Snapshot:
    if source.kind == "dir":
        return Snapshot(source, Path(source.url), "local", None)
    if source.kind != "git":
        raise SnapshotError(f"source {source.id!r}: kind {source.kind!r} is not supported yet")
    _check_git_source(source.url, source.ref or "")
    commit = resolve_ref(source.url, source.ref or "")
    dest = work_dir / source.id / commit
    if not (dest / ".git").is_dir():
        tmp = dest.with_name(dest.name + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        if _SHA.match(source.ref or ""):
            _git("init", "-q", str(tmp))
            _git("fetch", "-q", "--depth", "1", "--", source.url, commit, cwd=tmp)
            _git("checkout", "-q", "FETCH_HEAD", cwd=tmp)
        else:
            _git("clone", "-q", "--depth", "1", "--branch", source.ref, "--", source.url, str(tmp))
        head = _git("rev-parse", "HEAD", cwd=tmp)
        if head != commit:  # the ref moved between ls-remote and clone
            shutil.rmtree(tmp, ignore_errors=True)
            raise SnapshotError(f"{source.id}: {source.ref} moved to {head} while cloning; retry")
        tmp.rename(dest)
    date = _git("log", "-1", "--format=%cI", cwd=dest)
    return Snapshot(source, dest, commit, date)
