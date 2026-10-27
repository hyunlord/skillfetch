"""`skillfetch scan https://github.com/<owner>/<repo>[/tree/<ref>[/<path>]]`: a shallow clone
into a temporary folder, scanned there and deleted afterwards. Nothing is installed; no hook,
script or submodule of the repository runs, and symbolic links are checked out as plain files
(index-format.md §5.1)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_GITHUB = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9][A-Za-z0-9-]{0,38})/(?P<repo>[A-Za-z0-9._-]+?)"
    r"(?:\.git)?(?:/tree/(?P<ref>[^/\s]+)(?P<path>(?:/[^\s]*)?))?/?$"
)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_PART = re.compile(r"^[A-Za-z0-9._@+-]+$")


class RemoteError(RuntimeError):
    pass


@dataclass(frozen=True)
class RemoteTarget:
    url: str  # as given, for the report
    clone_url: str
    ref: str | None  # branch, tag or full commit sha; None = the default branch
    subpath: str  # folder inside the repository to scan; "" = the whole repository


def is_remote(target: str) -> bool:
    return target.startswith(("https://", "http://"))


def parse_github_url(url: str) -> RemoteTarget:
    m = _GITHUB.match(url.strip())
    if m is None:
        raise RemoteError(
            f"not a GitHub repository URL: {url!r} "
            "(expected https://github.com/<owner>/<repo>[/tree/<ref>[/<path>]])"
        )
    ref = m["ref"]
    if ref is not None and (ref.startswith("-") or not _SAFE_PART.match(ref)):
        raise RemoteError(f"refusing ref {ref!r}")
    parts = [p for p in (m["path"] or "").split("/") if p]
    if any(p in (".", "..") or not _SAFE_PART.match(p) for p in parts):
        raise RemoteError(f"refusing path {m['path']!r}")
    return RemoteTarget(
        url=url.strip().rstrip("/"),
        clone_url=f"https://github.com/{m['owner']}/{m['repo']}.git",
        ref=ref,
        subpath="/".join(parts),
    )


def _git(args: list[str], cwd: Path | None = None, allow_file: bool = False) -> str:
    config = ["-c", "core.symlinks=false", "-c", "core.hooksPath=/dev/null"]
    if not allow_file:
        config += ["-c", "protocol.file.allow=never"]
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    proc = subprocess.run(
        ["git", *config, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )
    if proc.returncode != 0:
        raise RemoteError(f"git {args[0]} failed: {proc.stderr.strip()[:300]}")
    return proc.stdout.strip()


@contextmanager
def checkout(target: RemoteTarget, allow_file: bool = False) -> Iterator[tuple[Path, str]]:
    """(folder to scan, commit sha) of a depth-1 checkout, deleted on exit. `allow_file` lets
    the test suite clone a local file:// repository."""
    tmp = Path(tempfile.mkdtemp(prefix="skillfetch-scan-"))
    repo = tmp / "repo"
    try:
        if target.ref is not None and _SHA.match(target.ref):
            _git(["init", "-q", str(repo)], allow_file=allow_file)
            _git(
                ["fetch", "-q", "--depth", "1", "--no-tags", "--", target.clone_url, target.ref],
                cwd=repo,
                allow_file=allow_file,
            )
            _git(["checkout", "-q", "FETCH_HEAD"], cwd=repo, allow_file=allow_file)
        else:
            branch = ["--branch", target.ref] if target.ref else []
            _git(
                [
                    "clone",
                    "-q",
                    "--depth",
                    "1",
                    "--single-branch",
                    "--no-tags",
                    *branch,
                    "--",
                    target.clone_url,
                    str(repo),
                ],
                allow_file=allow_file,
            )
        commit = _git(["rev-parse", "HEAD"], cwd=repo, allow_file=allow_file)
        folder = (repo / target.subpath) if target.subpath else repo
        if not folder.resolve().is_relative_to(repo.resolve()) or not folder.is_dir():
            raise RemoteError(f"no folder {target.subpath!r} at {target.ref or 'HEAD'}")
        yield folder, commit
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
