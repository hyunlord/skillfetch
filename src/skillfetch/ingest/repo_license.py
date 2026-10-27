"""Which license applies to a skill that states none of its own (index-format.md §1.8, the
rule discover's pre-check and `skillfetch scan` share): outside an aggregator, and for a skill
that names no upstream, the nearest license file above the skill folder, up to the repository
root. An aggregator copies skills from other repositories, so its own license files say
nothing about them."""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

from skillfetch.ingest.licenses import LICENSE_FILES, classify_text
from skillfetch.ingest.provenance import openskills_upstream, parse_third_party_doc
from skillfetch.ingest.skillfile import discover_skills, read_skill, read_text

AGGREGATOR_UPSTREAM_SHARE = 0.1  # this share of upstream-marked skills makes an aggregator
_UPSTREAM_KEYS = ("upstream", "source", "source_url", "origin", "original", "repository")
_THIRD_PARTY_FILE = re.compile(r"^(third[-_ ]?party|upstreams?|credits|attribution)", re.I)
_THIRD_PARTY_HEADING = re.compile(
    r"^#{1,6}\s.*\b(third[- ]party|upstream|credits|attribution)", re.I | re.M
)
_LINKED_REPO = re.compile(r"github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)")


def upstream_marked(skill_dir: Path, frontmatter: dict | None) -> bool:
    """The skill says it came from elsewhere: an `.openskills.json` upstream (§1.1), or a
    frontmatter field such as `upstream:` or `source:` holding a GitHub URL."""
    if openskills_upstream(skill_dir) is not None:
        return True
    fm = frontmatter or {}
    return any(isinstance(fm.get(k), str) and "github.com/" in fm[k] for k in _UPSTREAM_KEYS)


def third_party_list(repo_dir: Path) -> str | None:
    """Where the repository lists third-party upstreams: a root file named like
    THIRD_PARTY*/UPSTREAM*/CREDITS*/ATTRIBUTION*, or a README section with such a heading
    and links to at least three other GitHub repositories, or UASL's `- Upstream:` format.
    None when there is none."""
    for path in sorted(repo_dir.iterdir()):
        if path.is_file() and not path.is_symlink() and _THIRD_PARTY_FILE.match(path.name):
            return path.name
    for name in ("README.md", "readme.md", "README"):
        path = repo_dir / name
        if not path.is_file() or path.is_symlink():
            continue
        text = read_text(path)
        if parse_third_party_doc(text):
            return f"{name} (Upstream lines)"
        if m := _THIRD_PARTY_HEADING.search(text):
            repos = {f"{o}/{r}".lower() for o, r in _LINKED_REPO.findall(text[m.start() :])}
            if len(repos) >= 3:
                return f"{name} ({m.group(1).lower()} section)"
    return None


def nearest_repo_license(repo_dir: Path, skill_dir: Path) -> tuple[str, str] | None:
    """(license file, license) of the nearest license file above the skill folder, up to the
    repository root: the --upstream-licenses rule (§1.8) with the repository as the upstream."""
    folder = skill_dir.parent if skill_dir != repo_dir else repo_dir
    while True:
        for name in LICENSE_FILES:
            path = folder / name
            if path.is_file() and not path.is_symlink():
                rel = path.relative_to(repo_dir).as_posix()
                return rel, classify_text(read_text(path)) or "unrecognized"
        if folder == repo_dir or repo_dir not in folder.parents:
            return None
        folder = folder.parent


def is_aggregator(third_party: str | None, upstream_share: float | None) -> bool:
    return bool(third_party) or (upstream_share or 0) >= AGGREGATOR_UPSTREAM_SHARE


def repo_root(folder: Path) -> Path:
    """The nearest folder at or above `folder` with a `.git`; `folder` itself if none."""
    folder = folder.resolve()
    for d in (folder, *folder.parents):
        if (d / ".git").exists():
            return d
    return folder


def _frontmatter(skill_dir: Path) -> dict | None:
    try:
        return read_skill(skill_dir).frontmatter
    except (OSError, UnicodeError, ValueError):
        return None


class RepoLicenses:
    """The repository-level half of the rule for one repository: whether it is an aggregator
    (judged over all its SKILL.md folders, as discover does; computed on first use) and the
    license file a skill without its own license falls back to."""

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir.resolve()

    @cached_property
    def third_party(self) -> str | None:
        return third_party_list(self.repo_dir)

    @cached_property
    def upstream_share(self) -> float | None:
        dirs = discover_skills(self.repo_dir)
        marked = sum(upstream_marked(d, _frontmatter(d)) for d in dirs)
        return round(marked / len(dirs), 3) if dirs else None

    @property
    def aggregator(self) -> bool:
        return is_aggregator(self.third_party, self.upstream_share)

    def inherited(self, skill_dir: Path, frontmatter: dict | None) -> tuple[str, str] | None:
        """(license file relative to the repository root, license) for a skill without its
        own license; None in an aggregator, for a skill naming an upstream, or with no file."""
        skill_dir = skill_dir.resolve()
        if self.aggregator or upstream_marked(skill_dir, frontmatter):
            return None
        if skill_dir != self.repo_dir and self.repo_dir not in skill_dir.parents:
            return None
        return nearest_repo_license(self.repo_dir, skill_dir)
