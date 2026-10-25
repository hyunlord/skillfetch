"""Discover (index-format.md §6): find repositories that could become corpus sources, and
check each one without a model.

Three channels feed the candidate list:
- GitHub code search for SKILL.md files, split into size ranges because one query returns
  at most 1,000 results. GitHub reports far more SKILL.md files than one run can page
  through at code search's 10 requests a minute, so each run covers a few ranges and the
  next run continues from there (the range offset follows the ISO week);
- GitHub repository search by topic (agent-skills, claude-skills, ...);
- list sources from the config file: awesome lists and registry pages or APIs whose text
  names GitHub repositories (skills.sh, Skillselion).

Repositories already in sources.yaml or in data/discover/seen.jsonl (evaluated before) are
left out. The top candidates are shallow-cloned and pre-checked with the same lint, scan,
license and hashing code the ingest pipeline uses: SKILL.md count, lint and scan pass
rates, licenses, name and content-hash overlap with the current index, locale copies,
last commit and stars. Nothing here calls a model or a paid API, and nothing writes to an
index or to sources.yaml.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from skillfetch.ingest.build import _locale_paths, _norm_name
from skillfetch.ingest.injection import load_rules, scan_skill
from skillfetch.ingest.licenses import (
    LICENSE_FILES,
    REDISTRIBUTABLE,
    classify_text,
    root_license,
    skill_license,
)
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.provenance import openskills_upstream, parse_third_party_doc
from skillfetch.ingest.skillfile import content_hash, discover_skills, read_skill, read_text
from skillfetch.ingest.sources import Source
from skillfetch.ingest.upstream_licenses import GitHubClient, _safe_repo

DEFAULT_CONFIG = Path("discover.yaml")
DEFAULT_OUT = Path("data/discover")
SEEN_FILE = "seen.jsonl"
REPORT_FILE = "discover-report.md"
ROWS_FILE = "discover.jsonl"
SEARCH_CAP = 1000  # results GitHub returns for one search query
PER_PAGE = 100
ISSUE_START = "<!-- skillfetch-discover:start -->"
ISSUE_END = "<!-- skillfetch-discover:end -->"
ISSUE_MAX = 60_000  # GitHub caps an issue body or comment at 65,536 characters
_GITHUB_LINK = r"github\.com/(?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9._-]+)"
_REPO_URL = re.compile(r"^https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$")


class CodeSearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = "SKILL.md"
    size_step: int = 100  # bytes per size range
    size_max: int = 20_000  # the last range is "size >= size_max"
    shards_per_run: int = 12
    pages_per_shard: int = 3
    pause: float = 6.5  # seconds between code search requests (10 a minute)


class ListSource(BaseModel):
    """A page or API whose text names GitHub repositories. `pattern` must have the named
    groups `owner` and `repo`; `url` may use {page} (1-based) and {offset} (page × step)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    url: str
    pattern: str = _GITHUB_LINK
    pages: int = 1
    step: int = 0

    @field_validator("url")
    @classmethod
    def _https(cls, url: str) -> str:
        if not url.startswith("https://"):
            raise ValueError(f"list source url {url!r}: https only")
        return url

    @field_validator("pattern")
    @classmethod
    def _groups(cls, pattern: str) -> str:
        if not {"owner", "repo"} <= set(re.compile(pattern).groupindex):
            raise ValueError(f"pattern {pattern!r} needs the groups owner and repo")
        return pattern


class DiscoverConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_search: CodeSearch = CodeSearch()
    repo_topics: list[str] = []
    topic_pages: int = 1
    lists: list[ListSource] = []
    exclude_forks: bool = True
    exclude_archived: bool = True
    max_checks: int = 25  # candidates cloned and pre-checked per run
    max_repo_kb: int = 200_000  # larger repositories are reported, not cloned


def load_config(path: Path) -> DiscoverConfig:
    return DiscoverConfig.model_validate(yaml.safe_load(path.read_text()) or {})


class Fetch(Protocol):
    def __call__(self, url: str) -> str | None: ...


class HttpFetch:
    """GET an https URL as text; None on any failure, with the reason in `last_error`."""

    last_error: str | None = None

    def __call__(self, url: str) -> str | None:
        self.last_error = None
        if not url.startswith("https://"):
            self.last_error = "not https"
            return None
        try:
            req = Request(url, headers={"User-Agent": "skillfetch-discover"})
            with urlopen(req, timeout=30) as r:
                return r.read(5_000_000).decode("utf-8", "replace")
        except HTTPError as exc:
            self.last_error = f"HTTP {exc.code}"
        except (OSError, ValueError) as exc:
            self.last_error = type(exc).__name__
        return None


http_fetch = HttpFetch()


RATE_WAIT_MAX = 900.0  # seconds; a longer wait skips the request ("rate-limited, skipped")
RATE_SKIPPED = "rate-limited, skipped"
RATE_BUDGET = 1800.0  # seconds of rate-limit waiting per run, all requests together
BUDGET_SKIPPED = "budget exhausted, skipped"
_TRY_AGAIN = re.compile(r"try again in ([0-9.]+)\s*s", re.I)
_STATUS = re.compile(r"^HTTP/\S+\s+(\d{3})")


def retry_wait(
    status: int | None, headers: dict[str, str], message: str, now: float
) -> float | None:
    """Seconds GitHub asks for before a retry, when the failure is a rate limit (429, or 403
    with a rate-limit sign); None for any other failure. Order: the retry-after header, the
    message's "try again in N s", x-ratelimit-reset when no requests remain, else 60 s."""
    exhausted = headers.get("x-ratelimit-remaining") == "0"
    limited = status == 429 or (
        status == 403 and ("retry-after" in headers or exhausted or "rate limit" in message.lower())
    )
    if not limited:
        return None
    if (after := headers.get("retry-after", "").strip()).isdigit():
        return float(after)
    if m := _TRY_AGAIN.search(message):
        return float(m.group(1))
    if exhausted and (reset := headers.get("x-ratelimit-reset", "").strip()).isdigit():
        return max(0.0, float(reset) - now)
    return 60.0


def _split_include(stdout: str) -> tuple[int | None, dict[str, str], str]:
    """`gh api --include` output: status line and headers, a blank line, the body."""
    text = stdout.replace("\r\n", "\n")
    head, _, body = text.partition("\n\n")
    lines = head.split("\n")
    m = _STATUS.match(lines[0]) if lines else None
    if m is None:  # no header block: the whole output is the body
        return None, {}, text
    headers = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if sep:
            headers[key.strip().lower()] = value.strip()
    return int(m.group(1)), headers, body


class GhApi:
    """GitHubClient over `gh api` (its token: GH_TOKEN in CI). None on failure, with the
    reason in `last_error` (gh's message, which carries the HTTP status). A rate-limited
    request waits as long as GitHub asks and is retried once; a wait over `max_wait` skips it,
    and so does a wait that would take the run's total past `budget` (after which
    `budget_exhausted` is set). `retries`, `waited` (seconds) and `skipped` count what
    happened."""

    def __init__(
        self,
        run=subprocess.run,
        sleep=time.sleep,
        clock=time.time,
        max_wait=RATE_WAIT_MAX,
        budget=RATE_BUDGET,
    ):
        self._run, self._sleep, self._clock = run, sleep, clock
        self.max_wait, self.budget = max_wait, budget
        self.last_error: str | None = None
        self.retries = 0
        self.waited = 0.0
        self.skipped = 0
        self.budget_exhausted = False

    def _once(self, path: str) -> tuple[dict | None, str | None, float | None]:
        proc = self._run(["gh", "api", "--include", path], capture_output=True, text=True)
        status, headers, body = _split_include(proc.stdout or "")
        if proc.returncode == 0:
            return json.loads(body), None, None
        lines = [ln.strip() for ln in (proc.stderr or "").splitlines() if ln.strip()]
        message = lines[-1] if lines else f"exit {proc.returncode}"
        return None, message[:200], retry_wait(status, headers, message, self._clock())

    def get(self, path: str) -> dict | None:
        self.last_error = None
        data, message, wait = self._once(path)
        if message is None:
            return data
        if wait is not None:
            if wait > self.max_wait:
                self.skipped += 1
                self.last_error = f"{RATE_SKIPPED} (asked to wait {wait:.0f} s)"
                return None
            if self.waited + wait > self.budget:
                self.skipped += 1
                self.budget_exhausted = True
                self.last_error = (
                    f"{BUDGET_SKIPPED} (asked to wait {wait:.0f} s, {self.waited:.0f} s of "
                    f"{self.budget:.0f} s used)"
                )
                return None
            self._sleep(wait)
            self.retries += 1
            self.waited += wait
            data, message, _ = self._once(path)
            if message is None:
                return data
            message = f"after one retry: {message}"
        self.last_error = message
        return None


def _why(client) -> str:
    return getattr(client, "last_error", None) or "no response"


def repo_key(owner: str, name: str) -> str | None:
    """'owner/name' lowercased, or None for something that cannot be a repository."""
    name = name.removesuffix(".git")
    return f"{owner}/{name}".lower() if _safe_repo(owner, name) else None


def known_repos(sources: Iterable[Source], seen_path: Path) -> set[str]:
    """Repositories already in sources.yaml or already evaluated (seen.jsonl)."""
    known = set()
    for source in sources:
        m = _REPO_URL.match(source.url.strip())
        if m and (key := repo_key(*m.groups())):
            known.add(key)
    if seen_path.is_file():
        for line in seen_path.read_text().splitlines():
            if line.strip():
                known.add(json.loads(line)["repo"].lower())
    return known


@dataclass
class Candidate:
    repo: str  # owner/name as first seen
    channels: Counter = field(default_factory=Counter)  # "code", "topic:<t>", "list:<id>"
    skill_md_seen: int = 0  # SKILL.md paths seen in code search results
    meta: dict | None = None  # GitHub repository object

    def rank(self) -> tuple:
        stars = (self.meta or {}).get("stargazers_count") or 0
        return (-len(self.channels), -self.skill_md_seen, -stars, self.repo.lower())


@dataclass
class ShardStat:
    size: str
    total: int | None  # total_count GitHub reported; None if the request failed
    fetched: int
    truncated: bool  # more results than this run read (the 1,000 cap or the page limit)
    error: str | None = None  # why a page failed


@dataclass
class Found:
    candidates: dict[str, Candidate] = field(default_factory=dict)
    shards: list[ShardStat] = field(default_factory=list)
    shard_count: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (request, reason)

    def add(self, owner: str, name: str, channel: str, meta: dict | None = None) -> Candidate:
        key = repo_key(owner, name)
        if key is None:
            return Candidate(f"{owner}/{name}")
        cand = self.candidates.setdefault(key, Candidate(f"{owner}/{name.removesuffix('.git')}"))
        cand.channels[channel] += 1
        if meta and cand.meta is None:
            cand.meta = meta
        return cand


def size_shards(cfg: CodeSearch) -> list[str]:
    """Size qualifiers covering every size: 0..step-1, step..2·step-1, ..., >=size_max."""
    shards = [f"{lo}..{lo + cfg.size_step - 1}" for lo in range(0, cfg.size_max, cfg.size_step)]
    return [*shards, f">={cfg.size_max}"]


def shards_for_run(shards: list[str], per_run: int, week: int) -> list[str]:
    """The ranges this run searches: per_run consecutive ranges, starting where the previous
    week's run stopped (wrapping around)."""
    n = len(shards)
    start = (week * per_run) % n
    return [shards[(start + i) % n] for i in range(min(per_run, n))]


def search_code(client: GitHubClient, cfg: CodeSearch, week: int, found: Found) -> None:
    shards = size_shards(cfg)
    found.shard_count = len(shards)
    first = True
    for shard in shards_for_run(shards, cfg.shards_per_run, week):
        if getattr(client, "budget_exhausted", False):  # the rest is not requested
            found.shards.append(ShardStat(shard, None, 0, True, BUDGET_SKIPPED))
            continue
        total, fetched, error = None, 0, None
        for page in range(1, cfg.pages_per_shard + 1):
            if not first and cfg.pause:
                time.sleep(cfg.pause)
            first = False
            q = quote_plus(f"filename:{cfg.filename} size:{shard}")
            path = f"search/code?q={q}&per_page={PER_PAGE}&page={page}"
            data = client.get(path)
            if not data:
                error = _why(client)
                found.failed.append((path, error))
                break
            total = data.get("total_count", 0)
            items = data.get("items", [])
            for item in items:
                owner, _, name = item.get("repository", {}).get("full_name", "").partition("/")
                if owner and name:
                    found.add(owner, name, "code").skill_md_seen += 1
            fetched += len(items)
            if len(items) < PER_PAGE or fetched >= min(total, SEARCH_CAP):
                break
        truncated = total is None or fetched < total
        found.shards.append(ShardStat(shard, total, fetched, truncated, error))


def search_topics(client: GitHubClient, topics: list[str], pages: int, found: Found) -> None:
    for topic in topics:
        for page in range(1, pages + 1):
            q = quote_plus(f"topic:{topic}")
            path = (
                f"search/repositories?q={q}&sort=updated&order=desc&per_page={PER_PAGE}&page={page}"
            )
            data = client.get(path)
            if not data:
                found.failed.append((path, _why(client)))
                break
            items = data.get("items", [])
            for repo in items:
                owner, _, name = repo.get("full_name", "").partition("/")
                if owner and name:
                    found.add(owner, name, f"topic:{topic}", meta=repo)
            if len(items) < PER_PAGE:
                break


def read_lists(fetch: Fetch, lists: list[ListSource], found: Found) -> None:
    for src in lists:
        pattern = re.compile(src.pattern)
        for i in range(src.pages):
            url = src.url.format(page=i + 1, offset=i * src.step)
            text = fetch(url)
            if text is None:
                found.failed.append((url, _why(fetch)))
                break
            hits = {(m["owner"], m["repo"]) for m in pattern.finditer(text)}
            for owner, name in sorted(hits):
                found.add(owner, name, f"list:{src.id}")
            if not hits:
                break


def select(
    found: Found, known: set[str], client: GitHubClient, cfg: DiscoverConfig
) -> tuple[list[Candidate], dict[str, int]]:
    """Drop known repositories, forks and archived ones; return the candidates in rank order
    with metadata for the first max_checks, and how many were dropped for each reason."""
    dropped: Counter = Counter()
    pool = []
    for key, cand in found.candidates.items():
        if key in known:
            dropped["in sources.yaml or seen.jsonl"] += 1
        else:
            pool.append(cand)
    pool.sort(key=Candidate.rank)
    out: list[Candidate] = []
    with_meta = 0
    for cand in pool:
        if with_meta < cfg.max_checks:
            if cand.meta is None:
                cand.meta = client.get(f"repos/{cand.repo}")
                if cand.meta is None:
                    found.failed.append((f"repos/{cand.repo}", _why(client)))
            meta = cand.meta or {}
            full = meta.get("full_name")
            renamed = repo_key(*full.split("/", 1)) if full and "/" in full else None
            if renamed and renamed in known:  # a renamed repository already listed
                dropped["in sources.yaml or seen.jsonl"] += 1
                continue
            if cfg.exclude_forks and meta.get("fork"):
                dropped["fork"] += 1
                continue
            if cfg.exclude_archived and meta.get("archived"):
                dropped["archived"] += 1
                continue
            with_meta += 1
        out.append(cand)
    return out, dict(dropped)


STALE_NAME_MIN = 0.5  # name overlap at or above this ...
STALE_HASH_MAX = 0.1  # ... and content-hash overlap below this: the index has older copies


@dataclass
class IndexView:
    names: set[str]
    hashes: set[str]
    sources: dict[str, set[str]] = field(default_factory=dict)  # normalized name -> source ids

    @classmethod
    def load(cls, index_dir: Path) -> IndexView | None:
        path = index_dir / "skills.jsonl"
        if not path.is_file():
            return None
        view = cls(set(), set())
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                name = _norm_name(rec.get("name", ""))
                view.names.add(name)
                view.hashes.add(rec.get("content_hash", ""))
                view.sources.setdefault(name, set()).add(rec.get("source_id", "?"))
        return view


def _share(n: int, d: int) -> float | None:
    return round(n / d, 3) if d else None


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


def precheck(repo_dir: Path, index: IndexView | None) -> dict:
    """Model-free checks of every skill folder in a checked-out repository."""
    dirs = discover_skills(repo_dir)
    rules = load_rules()
    rows = []
    for d in dirs:
        rel = d.relative_to(repo_dir).as_posix() if d != repo_dir else ""
        try:
            doc = read_skill(d)
            fm = doc.frontmatter or {}
            name = fm.get("name") if isinstance(fm.get("name"), str) else d.name
            own = skill_license(d, doc.frontmatter, "per-skill")
            rows.append(
                {
                    "dir": d,
                    "path": rel,
                    "name": _norm_name(name or d.name),
                    "lint": lint_skill(d).ok,
                    "scan": scan_skill(d, rules).ok,
                    "hash": content_hash(d),
                    "license": own.license,
                    "own_license": own.origin != "none",
                    "upstream": upstream_marked(d, doc.frontmatter),
                }
            )
        except (OSError, UnicodeError, ValueError):
            rows.append(
                {
                    "dir": d,
                    "path": rel,
                    "name": _norm_name(d.name),
                    "lint": False,
                    "scan": False,
                    "hash": "",
                    "license": "unknown",
                    "own_license": False,
                    "upstream": False,
                }
            )
    n = len(rows)
    upstream_share = _share(sum(r["upstream"] for r in rows), n)
    third_party = third_party_list(repo_dir)
    aggregator = bool(third_party) or (upstream_share or 0) >= AGGREGATOR_UPSTREAM_SHARE
    from_root = 0
    if not aggregator:  # the repository is the skills' upstream: its license files apply
        for r in rows:
            if not r["own_license"] and not r["upstream"]:
                found = nearest_repo_license(repo_dir, r["dir"])
                if found:
                    r["license"] = found[1]
                    from_root += 1
    by_name = Counter(r["name"] for r in rows)
    locale = _locale_paths([r["path"] for r in rows])
    copies = sum(1 for r in rows if by_name[r["name"]] > 1 and r["path"] in locale)
    licenses = Counter(r["license"] for r in rows)
    out = {
        "skills": n,
        "lint_pass": _share(sum(r["lint"] for r in rows), n),
        "scan_pass": _share(sum(r["scan"] for r in rows), n),
        "root_license": root_license(repo_dir),
        "aggregator": aggregator,
        "upstream_marked": upstream_share,
        "third_party_list": third_party,
        "license_from_repo": from_root,
        "skill_licenses": dict(licenses.most_common()),
        "redistributable": _share(sum(v for k, v in licenses.items() if k in REDISTRIBUTABLE), n),
        "name_in_index": None,
        "hash_in_index": None,
        "stale_in_index": None,
        "index_sources": None,
        "locale_copies": _share(copies, n),
    }
    if index is not None and n:
        named = [r for r in rows if r["name"] in index.names]
        out["name_in_index"] = _share(len(named), n)
        out["hash_in_index"] = _share(sum(r["hash"] in index.hashes for r in rows), n)
        out["stale_in_index"] = (
            out["name_in_index"] >= STALE_NAME_MIN and out["hash_in_index"] < STALE_HASH_MAX
        )
        sources = Counter(s for r in named for s in index.sources.get(r["name"], ()))
        out["index_sources"] = dict(sources.most_common()) or None
    return out


Checkout = Callable[[str, str], tuple[Path, str | None]]  # (repo, ref) -> (dir, commit date)


def check_candidates(
    cands: list[Candidate],
    cfg: DiscoverConfig,
    checkout: Checkout,
    index: IndexView | None,
) -> list[dict]:
    rows = []
    for i, cand in enumerate(cands):
        meta = cand.meta or {}
        row = {
            "repo": meta.get("full_name") or cand.repo,
            "url": f"https://github.com/{meta.get('full_name') or cand.repo}",
            "channels": dict(sorted(cand.channels.items())),
            "skill_md_seen": cand.skill_md_seen,
            "stars": meta.get("stargazers_count"),
            "pushed_at": meta.get("pushed_at"),
            "repo_license": (meta.get("license") or {}).get("spdx_id"),
            "status": "not_checked",
        }
        if i < cfg.max_checks:
            if not meta:
                row["status"] = "unreachable"
            elif (meta.get("size") or 0) > cfg.max_repo_kb:
                row["status"] = "too_large"
            else:
                try:
                    path, commit_date = checkout(row["repo"], meta.get("default_branch") or "main")
                except Exception as exc:  # any clone failure is reported, not raised
                    row.update(status="clone_failed", error=str(exc)[:200])
                else:
                    try:
                        row.update(precheck(path, index), last_commit=commit_date)
                        row["status"] = "checked" if row["skills"] else "no_skills"
                    except Exception as exc:  # one broken repository does not stop the run
                        row.update(
                            status="check_failed", error=f"{type(exc).__name__}: {exc}"[:200]
                        )
        rows.append(row)
    return rows


def git_checkout(work_dir: Path) -> Checkout:
    """Shallow clone through the snapshot stage (https only, cached per commit)."""
    from skillfetch.ingest.snapshot import snapshot

    def run(repo: str, ref: str) -> tuple[Path, str | None]:
        source = Source(
            id=f"discover-{repo.replace('/', '--')}",
            kind="git",
            url=f"https://github.com/{repo}",
            ref=ref,
            publisher=repo.split("/")[0],
            publisher_trust="unknown",
        )
        snap = snapshot(source, work_dir)
        return snap.path, snap.commit_date

    return run


@dataclass
class Run:
    day: str
    week: int
    rows: list[dict]
    found: Found
    dropped: dict[str, int]
    known: int
    index: bool
    rate: dict = field(default_factory=dict)  # retries, waited (s), skipped
    partial: list[str] = field(default_factory=list)  # phases that stopped with an error


def discover(
    cfg: DiscoverConfig,
    client: GitHubClient,
    fetch: Fetch,
    known: set[str],
    checkout: Checkout,
    index: IndexView | None,
    today: date,
) -> Run:
    """Every phase runs even when an earlier one stopped with an error; such a phase is
    named in `partial`, and the report says the result is partial."""
    week = today.isocalendar().week
    found = Found()
    partial: list[str] = []

    def phase(name: str, fn):
        try:
            return fn()
        except Exception as exc:  # report what was gathered, not a traceback
            partial.append(f"{name}: {type(exc).__name__}: {exc}"[:300])
            return None

    phase("code search", lambda: search_code(client, cfg.code_search, week, found))
    phase("topic search", lambda: search_topics(client, cfg.repo_topics, cfg.topic_pages, found))
    phase("list sources", lambda: read_lists(fetch, cfg.lists, found))
    picked = phase("selection", lambda: select(found, known, client, cfg))
    if picked is None:  # fall back to the raw ranking, nothing cloned
        pool = [c for k, c in found.candidates.items() if k not in known]
        picked = (sorted(pool, key=Candidate.rank), {})
        cfg = cfg.model_copy(update={"max_checks": 0})
    cands, dropped = picked
    rows = phase("pre-check", lambda: check_candidates(cands, cfg, checkout, index)) or []
    rate = {k: getattr(client, k, 0) for k in ("retries", "waited", "skipped")}
    rate["budget_exhausted"] = getattr(client, "budget_exhausted", False)
    return Run(
        today.isoformat(), week, rows, found, dropped, len(known), index is not None, rate, partial
    )


def _pct(v: float | None) -> str:
    return "–" if v is None else f"{v * 100:.0f}%"


def _cell(v) -> str:
    return "–" if v is None else str(v).replace("|", "\\|")


def _aggregator(r: dict) -> str:
    if "aggregator" not in r:
        return "–"
    if not r["aggregator"]:
        return "no"
    if r.get("third_party_list"):
        return f"yes: {r['third_party_list']}"
    return f"yes: {_pct(r.get('upstream_marked'))} upstream-marked"


def render_stale(rows: list[dict]) -> list[str]:
    stale = [r for r in rows if r.get("stale_in_index")]
    if not stale:
        return []
    lines = [
        "",
        "## Older copies in the index",
        "",
        f"Name overlap at least {STALE_NAME_MIN:.0%} and content-hash overlap under "
        f"{STALE_HASH_MAX:.0%}: the index holds these skills, but not this version.",
        "",
        "| repository | SKILL.md | name in index | hash in index "
        "| index sources (matching names) |",
        "|---|---:|---:|---:|---|",
    ]
    for r in sorted(stale, key=lambda r: r["repo"]):
        sources = ", ".join(f"{k} {v}" for k, v in (r.get("index_sources") or {}).items())
        lines.append(
            f"| [{r['repo']}]({r['url']}) | {r['skills']} | {_pct(r['name_in_index'])} | "
            f"{_pct(r['hash_in_index'])} | {sources or '–'} |"
        )
    return lines


def render_table(rows: list[dict]) -> str:
    checked = [r for r in rows if r["status"] != "not_checked"]
    checked.sort(key=lambda r: (r["status"] != "checked", -(r.get("skills") or 0), r["repo"]))
    head = (
        "| repository | status | SKILL.md | lint pass | scan pass | aggregator | "
        "redistributable (own + root) | root license | name in index | hash in index | "
        "older copy in index | locale copies | last commit | stars | found by |\n"
        "|---|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---|"
    )
    lines = [head]
    for r in checked:
        lines.append(
            f"| [{r['repo']}]({r['url']}) | {r['status']} | {_cell(r.get('skills'))} | "
            f"{_pct(r.get('lint_pass'))} | {_pct(r.get('scan_pass'))} | {_aggregator(r)} | "
            f"{_pct(r.get('redistributable'))} | {_cell(r.get('root_license'))} | "
            f"{_pct(r.get('name_in_index'))} | {_pct(r.get('hash_in_index'))} | "
            f"{'yes' if r.get('stale_in_index') else '–'} | "
            f"{_pct(r.get('locale_copies'))} | {_cell((r.get('last_commit') or '')[:10] or None)} "
            f"| {_cell(r.get('stars'))} | {', '.join(r['channels'])} |"
        )
    return "\n".join(lines)


def _failure_kind(request: str) -> str:
    """search/code, search/repositories, repos (metadata) or the list page's host."""
    if request.startswith("https://"):
        return "list " + request.split("/")[2]
    path = request.split("?")[0]
    return "repos" if path.startswith("repos/") else path


def channel_lines(run: Run) -> list[str]:
    """Candidates per channel (code search, each topic, each list source) and the failed
    requests with their reasons: the top of the report."""
    f = run.found
    per = Counter(ch for c in f.candidates.values() for ch in c.channels)
    # distinct repositories per kind; a repository on two lists counts once under lists
    by_kind = Counter(
        k for c in f.candidates.values() for k in {ch.split(":")[0] for ch in c.channels}
    )
    results = sum(s.fetched for s in f.shards)
    topics = ", ".join(f"{k[6:]} {v}" for k, v in sorted(per.items()) if k.startswith("topic:"))
    lists = ", ".join(f"{k[5:]} {v}" for k, v in sorted(per.items()) if k.startswith("list:"))
    fails = Counter((_failure_kind(req), why) for req, why in f.failed)
    fail_text = "; ".join(f"{kind} {n}× ({why})" for (kind, why), n in sorted(fails.items()))
    return [
        f"- Code search (`filename:SKILL.md`): {by_kind['code']} repositories from {results} "
        "results.",
        f"- Topics: {by_kind['topic']} distinct ({topics or 'none'}).",
        f"- List sources: {by_kind['list']} distinct ({lists or 'none'}).",
        f"- All channels: {len(f.candidates)} distinct repositories (a repository can come "
        "from several channels).",
        f"- Failed requests: {len(f.failed)}" + (f": {fail_text}." if fail_text else "."),
        f"- Rate limits: {run.rate.get('retries', 0)} retries after waiting "
        f"{run.rate.get('waited', 0):.0f} s in total (budget {RATE_BUDGET:.0f} s"
        f"{', exhausted' if run.rate.get('budget_exhausted') else ''}); "
        f"{run.rate.get('skipped', 0)} requests skipped (a wait over {RATE_WAIT_MAX:.0f} s, "
        "or past the budget).",
    ]


def _shard_text(s: ShardStat) -> str:
    parts = [] if s.total is None else [f"{s.fetched}/{s.total}"]
    if s.error:
        known = (RATE_SKIPPED, BUDGET_SKIPPED)
        parts.append(next((k for k in known if s.error.startswith(k)), "failed"))
    return ", ".join(parts) or "failed"


def render_report(run: Run) -> str:
    f = run.found
    checked = sum(r["status"] != "not_checked" for r in run.rows)
    covered = ", ".join(f"{s.size} ({_shard_text(s)})" for s in f.shards)
    lines = [
        f"# skillfetch discover, {run.day}",
        "",
        *(
            [
                "**Partial result:** "
                + "; ".join(run.partial)
                + ". Everything below is what was gathered before that.",
                "",
            ]
            if run.partial
            else []
        ),
        *channel_lines(run),
        "",
        "Model-free pre-check of candidate source repositories (index-format.md §6). Nothing "
        "here is admitted: sources.yaml and the index are unchanged.",
        "",
        f"- Left out: {', '.join(f'{k} {v}' for k, v in sorted(run.dropped.items())) or 'none'} "
        f"({run.known} repositories in sources.yaml or seen.jsonl).",
        f"- Pre-checked: {checked}; not checked this run: {len(run.rows) - checked}.",
        f"- Code search, week {run.week}: {len(f.shards)} of {f.shard_count} size ranges "
        f"(results read/total): {covered or 'none'}. Ranges marked with fewer read than total "
        "were cut by GitHub's 1,000-result cap or the page limit.",
        f"- Index for overlap: {'loaded' if run.index else 'not found (overlap columns empty)'}.",
        "",
        "Columns: shares are of the repository's SKILL.md folders. aggregator = at least "
        f"{AGGREGATOR_UPSTREAM_SHARE:.0%} of its skills name an upstream (`.openskills.json` or "
        "a frontmatter `upstream:`/`source:` GitHub URL), or it has a third-party list (a "
        "THIRD_PARTY/UPSTREAM/CREDITS file, or a README section of that name linking three or "
        "more repositories). redistributable (own + root) = the skill's own LICENSE or "
        "frontmatter is permissive, or, outside an aggregator and for a skill naming no "
        "upstream, the nearest license file up to the repository root is (the "
        "--upstream-licenses rule, §1.8). name/hash in index = same normalized name / same "
        "content_hash as an index record; older copy in index = name overlap "
        f"≥ {STALE_NAME_MIN:.0%} and hash overlap < {STALE_HASH_MAX:.0%}. locale copies = "
        "folders under a locale segment that share their name with another folder (§1.6).",
        "",
        render_table(run.rows),
        *render_stale(run.rows),
    ]
    rest = [r for r in run.rows if r["status"] == "not_checked"][:50]
    if rest:
        lines += ["", f"Next candidates (not checked this run, first {len(rest)}):", ""]
        lines += [f"- {r['repo']} ({', '.join(r['channels'])})" for r in rest]
    return "\n".join(lines) + "\n"


def write_outputs(run: Run, out: Path) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    report, rows = out / REPORT_FILE, out / ROWS_FILE
    report.write_text(render_report(run))
    meta = {
        "day": run.day,
        "week": run.week,
        "shards": [asdict(s) for s in run.found.shards],
        "failed": [{"request": r, "reason": why} for r, why in run.found.failed],
        "rate": run.rate,
        "partial": run.partial,
    }
    rows.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in [{"run": meta}, *run.rows]) + "\n"
    )
    return report, rows


def issue_body(body: str, report: str) -> str | None:
    """The issue body with the report between the discover markers, or None when the body
    has no markers (then the report goes into a comment)."""
    start, end = body.find(ISSUE_START), body.find(ISSUE_END)
    if start < 0 or end < start:
        return None
    return body[: start + len(ISSUE_START)] + "\n" + report.strip() + "\n" + body[end:]


def fit_issue(report: str) -> str:
    if len(report) <= ISSUE_MAX:
        return report
    return (
        report[:ISSUE_MAX].rsplit("\n", 1)[0]
        + "\n\n(truncated; full report in the run's artifact)\n"
    )
