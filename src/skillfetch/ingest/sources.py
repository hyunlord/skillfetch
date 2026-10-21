"""Corpus sources (index-format.md §1.1), read from sources.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["git", "dir", "tarball"]
    url: str
    ref: str | None = None
    root: str = ""
    publisher: str
    publisher_trust: Literal["verified", "known", "unknown"]
    # "per-skill": each skill is licensed by its own LICENSE file or frontmatter, else
    # unknown; otherwise an SPDX id that applies to every skill of the source.
    license: str = "per-skill"
    # Markdown file (relative to the snapshot) listing the source's third-party upstreams.
    third_party_doc: str | None = None

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
