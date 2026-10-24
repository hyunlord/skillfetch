"""Corpus sources (index-format.md §1.1), read from sources.yaml."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["git", "dir", "tarball"]
    url: str
    ref: str | None = None
    root: str = ""
    # More than one skills directory in the snapshot (e.g. skills/ and plugins/*/skills/
    # spelled out); replaces `root`.
    roots: list[str] = []
    # Folders discovery does not enter, as a folder name ("template") or a path relative
    # to the snapshot ("tests/fixtures"); fnmatch patterns. Hidden folders, node_modules
    # and __pycache__ are always skipped.
    exclude: list[str] = []
    publisher: str
    publisher_trust: Literal["verified", "known", "unknown"]
    # "per-skill": each skill is licensed by its own LICENSE file or frontmatter, else
    # unknown; otherwise an SPDX id that applies to every skill of the source.
    license: str = "per-skill"
    # Markdown file (relative to the snapshot) listing the source's third-party upstreams.
    third_party_doc: str | None = None

    @model_validator(mode="after")
    def _safe_id(self):
        # the id names directories (work/<id>/, index ids): no separators, no traversal
        if not _ID.match(self.id) or ".." in self.id:
            raise ValueError(f"source id {self.id!r}: use letters, digits, '.', '_' and '-'")
        return self

    @model_validator(mode="after")
    def _safe_paths(self):
        if self.roots and self.root:
            raise ValueError(f"source {self.id!r}: give root or roots, not both")
        for path in [self.root, *self.roots, *self.exclude]:
            if path.startswith("/") or ".." in Path(path).parts:
                raise ValueError(f"source {self.id!r}: {path!r} must stay inside the snapshot")
        return self

    @model_validator(mode="after")
    def _ref_for_git(self):
        if self.kind == "git" and not self.ref:
            raise ValueError(f"source {self.id!r}: git sources need a ref")
        return self


def load_sources(path: Path) -> list[Source]:
    raw = yaml.safe_load(path.read_text()) or []
    sources = [Source.model_validate(entry) for entry in raw]
    ids = [s.id for s in sources]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate source ids")
    return sources
