"""Where a skill's license comes from (index-format.md §1.8): its own folder, its upstream
repo, or nowhere we can see.

An aggregated skill (UASL copies most of its skills from other repos, recorded in
`.openskills.json`) is licensed by its upstream author, not by the aggregator. For each
upstream repo we read the file tree once (GitHub git trees API) and look for a license file
on the skill's path, from its upstream folder up to the repo root; the nearest one wins.

`license_source` keeps two facts apart that are easy to conflate:
- `explicit`: a license is stated, in the skill folder or upstream;
- `upstream_no_license`: the upstream repo was found and states no license (all rights
  reserved by default — not the same as "we could not tell");
- `upstream_unknown`: no upstream is recorded, or it could not be read.

All network access goes through `GitHubClient`; results are cached on disk per repo.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from skillfetch.ingest.licenses import REDISTRIBUTABLE, classify_text

DEFAULT_CACHE = Path("~/.skillfetch/upstream-licenses").expanduser()
_LICENSE_FILE = re.compile(r"^(?:licen[cs]e|copying)(?:\.(?:md|txt|rst))?$", re.IGNORECASE)
_GITHUB = re.compile(r"^https?://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$")
LicenseSource = Literal["explicit", "upstream_no_license", "upstream_unknown"]


class GitHubClient(Protocol):
    def get(self, path: str) -> dict | None:
        """GET https://api.github.com/<path>; None on 404 (or any failure)."""
        ...


class GhCli:
    """GitHubClient over the `gh` CLI (uses its authentication)."""

    def get(self, path: str) -> dict | None:
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout)


@dataclass
class RepoLicenses:
    repo: str
    status: Literal["ok", "unreachable"]
    commit: str | None = None
    # license file path -> SPDX id (or "unrecognized") for every license file in the tree
    files: dict[str, str] = field(default_factory=dict)


def _classify_file(client: GitHubClient, owner: str, name: str, path: str, ref: str) -> str:
    blob = client.get(f"repos/{owner}/{name}/contents/{path}?ref={ref}")
    if not blob or blob.get("encoding") != "base64":
        return "unrecognized"
    text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
    return classify_text(text) or "unrecognized"


def read_repo(client: GitHubClient, repo_url: str, cache_dir: Path = DEFAULT_CACHE) -> RepoLicenses:
    m = _GITHUB.match(repo_url.strip())
    if m is None:
        return RepoLicenses(repo_url, "unreachable")
    owner, name = m.groups()
    cached = cache_dir / f"{owner}__{name}.json"
    if cached.is_file():
        data = json.loads(cached.read_text())
        return RepoLicenses(repo_url, data["status"], data.get("commit"), data.get("files", {}))
    info = client.get(f"repos/{owner}/{name}")
    tree = client.get(f"repos/{owner}/{name}/git/trees/HEAD?recursive=1") if info else None
    if not info or not tree:
        out = RepoLicenses(repo_url, "unreachable")
    else:
        commit = tree.get("sha")
        files = {
            e["path"]: _classify_file(client, owner, name, e["path"], commit)
            for e in tree.get("tree", [])
            if e.get("type") == "blob" and _LICENSE_FILE.match(e["path"].rsplit("/", 1)[-1])
        }
        out = RepoLicenses(repo_url, "ok", commit, files)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps({"status": out.status, "commit": out.commit, "files": out.files}))
    return out


@dataclass(frozen=True)
class LicenseFinding:
    license_source: LicenseSource
    license: str  # SPDX id, "proprietary", "unrecognized" or "unknown"
    origin: str  # "skill:<file>", "upstream:<repo>/<path>", or "none"
    redistributable: bool


def nearest_license(repo: RepoLicenses, skill_path: str) -> tuple[str, str] | None:
    """(license file path, license) of the license file nearest to skill_path, walking up
    to the repo root."""
    parts = [p for p in skill_path.strip("/").split("/") if p]
    for depth in range(len(parts), -1, -1):
        prefix = "/".join(parts[:depth])
        hits = sorted(p for p in repo.files if (p.rsplit("/", 1)[0] if "/" in p else "") == prefix)
        if hits:
            return hits[0], repo.files[hits[0]]
    return None


def license_finding(
    skill_license: str,
    skill_origin: str,
    upstream: dict | None,
    repos: dict[str, RepoLicenses],
) -> LicenseFinding:
    """Combine the skill folder's own license (from licenses.skill_license) with its
    upstream's. The skill folder wins; an upstream license applies when the folder has none."""
    if skill_origin != "none":
        return LicenseFinding(
            "explicit", skill_license, f"skill:{skill_origin}", skill_license in REDISTRIBUTABLE
        )
    repo = repos.get(upstream["repo"]) if upstream else None
    if repo is None or repo.status != "ok":
        return LicenseFinding("upstream_unknown", "unknown", "none", False)
    found = nearest_license(repo, upstream.get("path") or "")
    if found is None:
        return LicenseFinding("upstream_no_license", "unknown", "none", False)
    path, spdx = found
    return LicenseFinding(
        "explicit", spdx, f"upstream:{upstream['repo']}/{path}", spdx in REDISTRIBUTABLE
    )
