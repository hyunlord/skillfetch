"""Load a built index (index-format.md §2) and verify it against its manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from skillfetch.resolve.models import Constraint, PairVerdict, Skill

DEFAULT_INDEX_DIR = Path("~/.skillfetch/index").expanduser()
REQUIRED = ("manifest.json", "skills.jsonl", "constraints.jsonl")


def tilde(path: Path) -> str:
    """A path for display: under the home directory as `~/...`."""
    full, home = str(Path(path).resolve()), str(Path.home().resolve())
    return "~" + full[len(home) :] if full.startswith(home + "/") else str(path)


class IndexLoadError(RuntimeError):
    """The index is missing, incomplete, or does not match its manifest."""


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@dataclass
class Index:
    root: Path
    manifest: dict
    records: dict[str, dict]  # skill id -> skills.jsonl record
    constraints: dict[str, list[Constraint]] = field(default_factory=dict)
    dupgroups: dict[str, list[str]] = field(default_factory=dict)
    pairs: dict[frozenset[str], PairVerdict] = field(default_factory=dict)  # pairs.jsonl

    @classmethod
    def load(cls, root: Path) -> Index:
        root = Path(root).expanduser()
        for name in REQUIRED:
            if not (root / name).is_file():
                raise IndexLoadError(f"{root}: missing {name}; build one with `skillfetch ingest`")
        manifest = json.loads((root / "manifest.json").read_text())
        for rel, digest in (manifest.get("files") or {}).items():
            path = root / rel
            if not path.is_file():
                raise IndexLoadError(f"{root}: {rel} is listed in the manifest but missing")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise IndexLoadError(f"{root}: {rel} does not match its manifest hash")
        records = {r["id"]: r for r in _jsonl(root / "skills.jsonl")}
        constraints: dict[str, list[Constraint]] = {}
        for row in _jsonl(root / "constraints.jsonl"):
            sid = row.pop("skill_id")
            constraints.setdefault(sid, []).append(Constraint.model_validate(row))
        groups_path = root / "dupgroups.json"
        dupgroups = json.loads(groups_path.read_text()) if groups_path.is_file() else {}
        pairs_path = root / "pairs.jsonl"
        pairs = {}
        if pairs_path.is_file():
            for row in _jsonl(pairs_path):
                verdict = PairVerdict.model_validate(row)
                pairs[verdict.key] = verdict
        return cls(root, manifest, records, constraints, dupgroups, pairs)

    def verdicts(self) -> dict[frozenset[str], str]:
        return {key: p.verdict for key, p in self.pairs.items()}

    def skill(self, skill_id: str) -> Skill:
        """The resolve/ view of an indexed skill (constraints carry their fan_out flags)."""
        if skill_id not in self.records:
            raise KeyError(skill_id)
        return Skill(
            id=skill_id,
            constraints=self.constraints.get(skill_id, []),
            tags=self.records[skill_id].get("tags") or {},
            produces=self.records[skill_id].get("produces") or [],
            consumes=self.records[skill_id].get("consumes") or [],
        )

    def canonical(self) -> list[dict]:
        """Records that are their own canonical (duplicates collapsed)."""
        return [r for r in self.records.values() if r.get("canonical_id", r["id"]) == r["id"]]
