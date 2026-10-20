"""On-disk extract cache: one JSON file per (extract_version, model, content_hash).

A skill is extracted once. Changing the prompt bumps EXTRACT_VERSION, which moves every
lookup to a fresh directory; switching models does the same via the model segment.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from skillfetch.ingest.extract import EXTRACT_VERSION, ExtractRecord

DEFAULT_CACHE_DIR = Path("~/.skillfetch/extract-cache").expanduser()


class ExtractCache:
    def __init__(self, root: Path = DEFAULT_CACHE_DIR):
        self.root = root

    def path(self, content_hash: str, model: str) -> Path:
        return self.root / f"v{EXTRACT_VERSION}" / model / f"{content_hash}.json"

    def get(self, content_hash: str, model: str) -> ExtractRecord | None:
        path = self.path(content_hash, model)
        try:
            return ExtractRecord.model_validate_json(path.read_text())
        except (FileNotFoundError, ValidationError, ValueError):
            return None

    def put(self, record: ExtractRecord) -> None:
        path = self.path(record.content_hash, record.model)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(record.model_dump_json(indent=2))
        os.replace(tmp, path)
