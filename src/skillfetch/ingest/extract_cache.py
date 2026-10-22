"""On-disk extract cache: one JSON file per (extract_version, model, content_hash).

A skill is extracted once. The cache keeps the raw exchange with the model (the attempts
and their answers), never the post-processed result: `get` runs `postprocess` against the
skill's SKILL.md on every read, so a change to the post-processing rules reaches every
cached answer at the next build without an API call. Changing the prompt bumps
EXTRACT_VERSION, which moves every lookup to a fresh directory; switching models does the
same via the model segment.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from pydantic import ValidationError

from skillfetch.ingest.extract import (
    EXTRACT_VERSION,
    RAW_FIELDS,
    ExtractRecord,
    postprocess,
    raw,
)
from skillfetch.ingest.skillfile import SKILL_FILE, read_text

DEFAULT_CACHE_DIR = Path("~/.skillfetch/extract-cache").expanduser()
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class ExtractCache:
    def __init__(self, root: Path = DEFAULT_CACHE_DIR):
        self.root = root

    def path(self, content_hash: str, model: str) -> Path:
        """The cache file; `model` (e.g. an index's extract_model) and `content_hash` come from
        outside, so `model` must be a safe relative path and `content_hash` a sha256 digest."""
        from skillfetch.index.fetch import FetchError, safe_join

        if not isinstance(content_hash, str) or not _DIGEST.match(content_hash):
            raise ValueError(f"refusing content_hash {str(content_hash)[:80]!r}: not a sha256")
        base = self.root / f"v{EXTRACT_VERSION}"
        try:
            return safe_join(base, model) / f"{content_hash}.json"
        except FetchError as exc:
            raise ValueError(f"refusing extract model {str(model)[:80]!r}: {exc}") from exc

    def get_raw(self, content_hash: str, model: str) -> ExtractRecord | None:
        """The cached exchange, if its own extract_version, model and content_hash match
        the path it was found under (a file copied to the wrong place is not a hit)."""
        path = self.path(content_hash, model)
        try:
            record = ExtractRecord.model_validate_json(path.read_text())
        except (FileNotFoundError, ValidationError, ValueError):
            return None
        if (record.extract_version, record.model, record.content_hash) != (
            EXTRACT_VERSION,
            model,
            content_hash,
        ):
            return None
        return raw(record)

    def get(self, content_hash: str, model: str, skill_dir: Path) -> ExtractRecord | None:
        """The cached exchange, post-processed against `skill_dir`'s SKILL.md."""
        record = self.get_raw(content_hash, model)
        if record is None:
            return None
        return postprocess(record, read_text(skill_dir / SKILL_FILE))

    def put(self, record: ExtractRecord) -> None:
        path = self.path(record.content_hash, record.model)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(record.model_dump_json(include=set(RAW_FIELDS), indent=2))
        os.replace(tmp, path)
