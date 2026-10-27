"""The runtime tools as plain functions over one server session (no MCP SDK here).

Every tool returns JSON-serializable dicts. resolve_set follows constraints.md §5 through
`resolve.resolve_set`; resolutions are cached per session by set_id for load_skills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from skillfetch.index.fetch import BodyCache, FetchError
from skillfetch.index.find import DEFAULT_FIND_K, find_skills
from skillfetch.index.loader import Index
from skillfetch.index.profile import profile_repo
from skillfetch.index.search import (
    DEFAULT_K,
    DEFAULT_TIERS,
    MAX_QUERIES,
    ONE_LINE_CHARS,
    Searcher,
)
from skillfetch.ingest.extract import DEFAULT_MODEL
from skillfetch.ingest.extract_cache import DEFAULT_CACHE_DIR, ExtractCache
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.local_scan import Lookup, scan_target
from skillfetch.ingest.remote import RemoteError, checkout, parse_github_url
from skillfetch.ingest.skillfile import content_hash, read_skill
from skillfetch.resolve import resolve_set
from skillfetch.resolve.models import Skill
from skillfetch.resolve.relation import DEFAULT_CAP

PATH_PREFIX = "path:"
# constraints.md §5 step 4
DEFAULT_MAX_TOKENS = 8000  # load_skills budget for the concatenated bodies
MAX_QUERY_CHARS = 2000  # longer queries are cut (the result says truncated)
MAX_K = 200
MAX_AUTO_IDS = 20  # resolve_set candidates per call (pinned ids are not limited)
# scan_skill never extracts (the server uses no model): skills found in neither the index nor
# the extract cache are left out of the contradiction check, and the report says so
SCAN_EXTRACTION = (
    "not extracted: the MCP server uses no model; run `skillfetch scan <target> --claude-code` "
    "to check these skills for contradictions"
)


class Profile(BaseModel):
    """The `profile` argument of search_skills: profile_repo's output, or the same shape."""

    model_config = ConfigDict(extra="ignore")
    languages: list[str] = []
    frameworks: list[str] = []
    package_managers: list[str] = []
    tags: list[str] = []


def _invalid(arg: str, exc: ValidationError) -> dict:
    return {
        "error": f"invalid {arg}",
        "details": [
            {"loc": ".".join(map(str, e["loc"])), "msg": e["msg"]}
            for e in exc.errors(include_url=False)
        ],
    }


def scan_json(target: str, lookup: Lookup, parse=parse_github_url, checkout_fn=checkout) -> dict:
    """`skillfetch scan <target> --json`: a local folder, or a GitHub URL shallow-cloned into a
    temporary folder and deleted. Nothing is installed or run, and no model is called (skills
    in neither the index nor the extract cache skip the contradiction check, and the report
    says so). A missing folder, a refused URL or a failed clone returns {error}."""
    if not isinstance(target, str) or not target.strip():
        return {"error": "invalid target: pass a local folder or a GitHub URL"}
    try:
        report = scan_target(target.strip(), lookup, parse=parse, checkout_fn=checkout_fn)
    except NotADirectoryError:
        return {"error": f"not a folder: {target}"}
    except RemoteError as exc:
        return {"error": str(exc)}
    if report.skipped:
        report.extraction = SCAN_EXTRACTION
    return report.model_dump(mode="json")


@dataclass
class LocalSkill:
    """A pinned `path:/abs/dir` skill, checked ad hoc (lint + scan, cached constraints)."""

    id: str
    dir: Path
    content_hash: str
    skill: Skill
    note: str | None = None


@dataclass
class Session:
    index: Index
    extract_cache: ExtractCache = field(default_factory=lambda: ExtractCache(DEFAULT_CACHE_DIR))
    model: str | None = None  # extraction key for pinned paths; default: the index's
    bodies: BodyCache = field(default_factory=BodyCache)
    searcher: Searcher | None = None
    resolutions: dict[str, dict] = field(default_factory=dict)  # set_id -> resolve_set output
    local: dict[str, LocalSkill] = field(default_factory=dict)
    profiles: dict[str, dict] = field(default_factory=dict)  # resolved repo path -> profile
    # Options for #26 (docs/design/router-cost.md), off by default:
    # profile_root: when search_skills gets no profile, use profile_repo(profile_root), so
    # the router can skip its profile_repo call (`serve --auto-profile`: the server's cwd);
    # summary_chars: the compact summary length (`serve --summary-chars`).
    profile_root: Path | None = None
    summary_chars: int = ONE_LINE_CHARS
    # scan_skill's URL parser and shallow checkout (tests clone a local file:// repository)
    scan_parse: object = parse_github_url
    scan_checkout: object = checkout

    def __post_init__(self):
        if self.model is None:  # look up cached extractions made the way the index was built
            self.model = self.index.manifest.get("extract_model") or DEFAULT_MODEL
        if self.searcher is None:
            self.searcher = Searcher(self.index, self.summary_chars)

    # --- profile_repo ---------------------------------------------------------------------------

    def profile_repo(self, path: str) -> dict:
        key = str(Path(path).expanduser().resolve())
        if key not in self.profiles:
            self.profiles[key] = profile_repo(Path(key))
        return self.profiles[key]

    # --- scan_skill ---------------------------------------------------------------------------

    def scan_skill(self, target: str) -> dict:
        """The scan_skill tool: scan_json with this session's index and extract cache."""
        lookup = Lookup(self.index, self.extract_cache, self.model)
        return scan_json(target, lookup, self.scan_parse, self.scan_checkout)

    # --- find_skills ----------------------------------------------------------------------------

    def find_skills(self, want: str, k: int = DEFAULT_FIND_K) -> dict:
        """The index's top matches for a request the user made (index/find.py)."""
        return find_skills(self.index, self.searcher, want, k)

    # --- search_skills ------------------------------------------------------------------------

    def search_skills(
        self,
        query: str | None = None,
        profile: dict | None = None,
        k: int = DEFAULT_K,
        tiers: list[str] | None = None,
        verbose: bool = False,
        queries: list[str] | None = None,
    ) -> dict:
        """Results only (the queries are not echoed). `queries` (1-MAX_QUERIES) wins over
        `query`; several are each searched and RRF-merged. A query over MAX_QUERY_CHARS is
        cut and the result carries truncated: true; k is capped at MAX_K; a profile that
        does not match `Profile`, or bad queries, are refused with a structured error."""
        if queries is None:
            queries = [query] if query is not None else []
        if not (
            1 <= len(queries) <= MAX_QUERIES
            and all(isinstance(q, str) and q.strip() for q in queries)
        ):
            return {
                "error": f"invalid queries: pass query, or queries with 1-{MAX_QUERIES} "
                "non-empty strings"
            }
        if profile is None and self.profile_root is not None:
            profile = self.profile_repo(str(self.profile_root))
        if profile is not None:
            try:
                profile = Profile.model_validate(profile).model_dump()
            except ValidationError as exc:
                return _invalid("profile", exc)
        tiers = list(tiers or DEFAULT_TIERS)
        truncated = any(len(q) > MAX_QUERY_CHARS for q in queries)
        results = self.searcher.search_many(
            [q[:MAX_QUERY_CHARS] for q in queries], profile, min(k, MAX_K), tiers, verbose=verbose
        )
        out: dict = {"results": results}
        if truncated:
            out["truncated"] = True
        return out

    # --- resolve_set ---------------------------------------------------------------------------

    def _local(self, skill_id: str) -> tuple[LocalSkill | None, str | None]:
        path = Path(skill_id.removeprefix(PATH_PREFIX)).expanduser()
        if not path.is_absolute():
            return None, f"{skill_id}: a pinned path must be absolute"
        if not (path / "SKILL.md").is_file():
            return None, f"{skill_id}: no SKILL.md in {path}"
        lint = lint_skill(path)
        if not lint.ok:
            return None, f"{skill_id}: fails lint ({', '.join(i.rule for i in lint.errors)})"
        scan = scan_skill(path)
        if not scan.ok:
            rules = ", ".join(sorted({h.rule_id for h in scan.failures}))
            return None, f"{skill_id}: fails the injection scan ({rules})"
        digest = content_hash(path)
        record = self.extract_cache.get(digest, self.model, path)
        constraints = record.constraints() if record is not None else []
        note = None
        if record is None or record.status != "ok":
            note = (
                f"{skill_id}: no extracted constraints (run `skillfetch ingest {path} "
                "--with-api`); included without conflict checks"
            )
        local = LocalSkill(skill_id, path, digest, Skill(id=skill_id, constraints=constraints))
        local.note = note
        return local, None

    def _skill(self, skill_id: str, notes: list[str], errors: list[dict]) -> Skill | None:
        if skill_id.startswith(PATH_PREFIX):
            local, error = self._local(skill_id)
            if error:
                errors.append({"id": skill_id, "error": error})
                return None
            self.local[skill_id] = local
            if local.note:
                notes.append(local.note)
            return local.skill
        if skill_id not in self.index.records:
            errors.append({"id": skill_id, "error": "unknown skill id"})
            return None
        record = self.index.records[skill_id]
        if record.get("status") != "ok":
            reason = record.get("not_extracted_reason") or record.get("status")
            notes.append(f"{skill_id}: no extracted constraints ({reason}); not conflict-checked")
        return self.index.skill(skill_id)

    def resolve_set(self, auto_ids: list[str], pinned_ids: list[str] | None = None) -> dict:
        if len(auto_ids) > MAX_AUTO_IDS:
            return {
                "error": f"auto_ids: at most {MAX_AUTO_IDS} candidates per call "
                f"(got {len(auto_ids)}); pick fewer from the search results"
            }
        notes: list[str] = []
        errors: list[dict] = []
        pinned = [s for i in pinned_ids or [] if (s := self._skill(i, notes, errors))]
        auto = []
        for i in auto_ids:
            if i.startswith(PATH_PREFIX):  # a local skill is the user's choice: pin it
                errors.append({"id": i, "error": "path: ids go in pinned_ids, not auto_ids"})
            elif s := self._skill(i, notes, errors):
                auto.append(s)
        cap = self.index.manifest.get("conflict_cap") or DEFAULT_CAP  # as the index was built
        resolution = resolve_set(auto, pinned, self.index.verdicts(), cap).model_dump(mode="json")
        out = {**resolution, "notes": notes, "errors": errors}
        self.resolutions[resolution["set_id"]] = out
        return out

    # --- load_skills ---------------------------------------------------------------------------

    def _folder(self, skill_id: str) -> Path:
        if skill_id in self.local:
            local = self.local[skill_id]
            if content_hash(local.dir) != local.content_hash:
                raise FetchError("changed on disk since resolve_set; resolve again")
            return local.dir
        record = self.index.records[skill_id]
        return self.bodies.materialize(record, allow_file=self._dir_source(record))

    def _dir_source(self, record: dict) -> bool:
        """file:// fetch bases are expected only from a `dir` source (manifest.sources)."""
        kinds = {s.get("id"): s.get("kind") for s in self.index.manifest.get("sources") or []}
        return kinds.get(record.get("source_id")) == "dir"

    def load_skills(self, set_id: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict:
        """Bodies in precedence order. Each skill stands alone: a fetch, cache or read
        failure refuses that skill (listed in errors) and the others still load. Over
        `max_tokens`, skills are dropped from the end of the precedence list until the
        rest fits; each drop is listed in errors."""
        resolution = self.resolutions.get(set_id)
        if resolution is None:
            return {"set_id": set_id, "error": "unknown set_id; call resolve_set first"}
        bodies, errors = [], []
        for skill_id in resolution["precedence"]:
            try:
                folder = self._folder(skill_id)
                doc = read_skill(folder)
            except FetchError as exc:
                errors.append({"id": skill_id, "error": str(exc)})  # refused: no body
                continue
            except OSError as exc:  # cache rename, read: this skill only
                errors.append({"id": skill_id, "error": f"{type(exc).__name__}: {exc}"})
                continue
            body = "\n".join(doc.body_lines).strip()
            record = self.index.records.get(skill_id, {})
            title = record.get("title") or (doc.frontmatter or {}).get("name") or skill_id
            bodies.append((skill_id, title, folder, body))
        while bodies and sum(len(b[3]) // 4 for b in bodies) > max_tokens:
            skill_id, _, _, body = bodies.pop()  # the lowest precedence goes first
            errors.append(
                {
                    "id": skill_id,
                    "error": f"dropped: the set is over max_tokens={max_tokens} "
                    f"(this skill ~{len(body) // 4} tokens); pass a larger max_tokens to load it",
                }
            )
        sections, loaded = [], []
        for skill_id, title, folder, body in bodies:
            sections.append(f"## {len(sections) + 1}. {title} ({skill_id})\n\n{body}")
            loaded.append(
                {
                    "id": skill_id,
                    "title": title,
                    "path": str(folder),
                    "token_estimate": len(body) // 4,
                }
            )
        content = "\n\n".join(sections)
        return {
            "set_id": set_id,
            "skills": loaded,
            "content": content,
            "errors": errors,
        }

    # --- resolve_and_load ----------------------------------------------------------------------

    def resolve_and_load(
        self,
        auto_ids: list[str],
        pinned_ids: list[str] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        """resolve_set then load_skills in one call: the resolution's set_id, included,
        excluded, warnings and notes, the loaded content, and both steps' errors (resolve's
        first). Excluded skills are never loaded. An input error of resolve_set is returned
        as is."""
        resolution = self.resolve_set(auto_ids, pinned_ids)
        if "error" in resolution:
            return resolution
        loaded = self.load_skills(resolution["set_id"], max_tokens)
        return {
            "set_id": resolution["set_id"],
            "included": resolution["included"],
            "excluded": resolution["excluded"],
            "warnings": resolution["warnings"],
            "notes": resolution["notes"],
            "content": loaded["content"],
            "errors": resolution["errors"] + loaded["errors"],
        }
