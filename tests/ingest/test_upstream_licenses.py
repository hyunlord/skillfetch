"""Upstream license lookup (index-format.md §1.8). A fake GitHub client; no network."""

import base64

from skillfetch.ingest.upstream_licenses import (
    RepoLicenses,
    license_finding,
    nearest_license,
    read_repo,
)

MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person"
APACHE = "          Apache License\n          Version 2.0, January 2004\n"


class FakeGitHub:
    def __init__(self, repos):
        self.repos = repos  # "owner/name" -> {path: text}
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        parts = path.split("/")
        key = f"{parts[1]}/{parts[2].split('?')[0]}"
        files = self.repos.get(key)
        if files is None:
            return None
        if len(parts) == 3:
            return {"full_name": key}
        if parts[3] == "git":
            tree = [{"path": p, "type": "blob"} for p in files]
            return {"sha": "c0ffee", "tree": tree}
        if parts[3] == "contents":
            file = "/".join(parts[4:]).split("?")[0]
            text = files[file].encode()
            return {"encoding": "base64", "content": base64.b64encode(text).decode()}
        return None


def test_nearest_license_walks_up_the_upstream_path():
    repo = RepoLicenses("r", "ok", "c", {"LICENSE": "MIT", "docs/pdf/LICENSE.txt": "proprietary"})
    assert nearest_license(repo, "docs/pdf") == ("docs/pdf/LICENSE.txt", "proprietary")
    assert nearest_license(repo, "docs/xlsx") == ("LICENSE", "MIT")
    assert nearest_license(RepoLicenses("r", "ok", "c", {}), "a/b") is None


def test_read_repo_classifies_license_files_and_caches(tmp_path):
    gh = FakeGitHub(
        {"o/r": {"LICENSE": MIT, "skills/a/SKILL.md": "x", "skills/b/LICENSE.txt": APACHE}}
    )
    repo = read_repo(gh, "https://github.com/o/r", tmp_path)
    assert (repo.status, repo.commit) == ("ok", "c0ffee")
    assert repo.files == {"LICENSE": "MIT", "skills/b/LICENSE.txt": "Apache-2.0"}
    calls = len(gh.calls)
    assert read_repo(gh, "https://github.com/o/r", tmp_path).files == repo.files
    assert len(gh.calls) == calls  # second read from the cache


def test_unreachable_and_non_github_repos(tmp_path):
    gh = FakeGitHub({})
    assert read_repo(gh, "https://github.com/gone/away", tmp_path).status == "unreachable"
    assert read_repo(gh, "https://gitlab.com/o/r", tmp_path).status == "unreachable"


def test_three_license_sources():
    repos = {
        "https://github.com/o/mit": RepoLicenses("m", "ok", "c", {"LICENSE": "MIT"}),
        "https://github.com/o/bare": RepoLicenses("b", "ok", "c", {}),
        "https://github.com/o/gone": RepoLicenses("g", "unreachable"),
    }
    up = lambda repo: {"repo": repo, "path": "skills/x"}  # noqa: E731
    own = license_finding("Apache-2.0", "LICENSE.txt", up("https://github.com/o/bare"), repos)
    assert (own.license_source, own.license, own.origin) == (
        "explicit",
        "Apache-2.0",
        "skill:LICENSE.txt",
    )
    via = license_finding("unknown", "none", up("https://github.com/o/mit"), repos)
    assert (via.license_source, via.license, via.redistributable) == ("explicit", "MIT", True)
    assert via.origin == "upstream:https://github.com/o/mit/LICENSE"
    bare = license_finding("unknown", "none", up("https://github.com/o/bare"), repos)
    assert (bare.license_source, bare.redistributable) == ("upstream_no_license", False)
    for upstream in (up("https://github.com/o/gone"), None):
        assert license_finding("unknown", "none", upstream, repos).license_source == (
            "upstream_unknown"
        )
