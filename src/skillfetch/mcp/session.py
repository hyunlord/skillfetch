"""The runtime tools as plain functions over one server session (no MCP SDK here).

Every tool returns JSON-serializable dicts. resolve_set follows constraints.md §5 through
`resolve.resolve_set`; resolutions are cached per session by set_id for load_skills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skillfetch.index.fetch import BodyCache, FetchError
from skillfetch.index.loader import Index
from skillfetch.index.search import DEFAULT_TIERS, Searcher
from skillfetch.ingest.extract import DEFAULT_MODEL
from skillfetch.ingest.extract_cache import DEFAULT_CACHE_DIR, ExtractCache
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.skillfile import content_hash, read_skill
from skillfetch.resolve import resolve_set
from skillfetch.resolve.models import Skill

PATH_PREFIX = "path:"
# constraints.md §5 step 4
PRECEDENCE_HEADER = (
    "Skills are listed in precedence order. If two instructions disagree, follow the earlier one."
)


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
    model: str = DEFAULT_MODEL
    bodies: BodyCache = field(default_factory=BodyCache)
    searcher: Searcher | None = None
    resolutions: dict[str, dict] = field(default_factory=dict)  # set_id -> resolve_set output
    local: dict[str, LocalSkill] = field(default_factory=dict)

    def __post_init__(self):
        if self.searcher is None:
            self.searcher = Searcher(self.index)

    # --- search_skills ------------------------------------------------------------------------

    def search_skills(
        self,
        query: str,
        profile: dict | None = None,
        k: int = 10,
        tiers: list[str] | None = None,
    ) -> dict:
        tiers = list(tiers or DEFAULT_TIERS)
        return {"query": query, "results": self.searcher.search(query, profile, k, tiers)}

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
        record = self.extract_cache.get(digest, self.model)
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
        notes: list[str] = []
        errors: list[dict] = []
        pinned = [s for i in pinned_ids or [] if (s := self._skill(i, notes, errors))]
        auto = [s for i in auto_ids if (s := self._skill(i, notes, errors))]
        resolution = resolve_set(auto, pinned).model_dump(mode="json")
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
        return self.bodies.materialize(self.index.records[skill_id])

    def load_skills(self, set_id: str) -> dict:
        resolution = self.resolutions.get(set_id)
        if resolution is None:
            return {"set_id": set_id, "error": "unknown set_id; call resolve_set first"}
        sections, loaded, errors = [], [], []
        for skill_id in resolution["precedence"]:
            try:
                folder = self._folder(skill_id)
            except FetchError as exc:
                errors.append({"id": skill_id, "error": str(exc)})  # refused: no body
                continue
            doc = read_skill(folder)
            body = "\n".join(doc.body_lines).strip()
            record = self.index.records.get(skill_id, {})
            title = record.get("title") or (doc.frontmatter or {}).get("name") or skill_id
            sections.append(f"## {len(sections) + 1}. {title} ({skill_id})\n\n{body}")
            loaded.append(
                {
                    "id": skill_id,
                    "title": title,
                    "path": str(folder),
                    "token_estimate": len(body) // 4,
                }
            )
        content = "\n\n".join([PRECEDENCE_HEADER, *sections]) if sections else ""
        return {
            "set_id": set_id,
            "precedence_header": PRECEDENCE_HEADER,
            "skills": loaded,
            "content": content,
            "errors": errors,
        }
