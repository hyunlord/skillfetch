"""The runtime takes the conflict cap the index was built with (manifest.conflict_cap):
there is no module-level setting to forget."""

import json

from indexkit import make_index, skill_id

from skillfetch.index.loader import Index
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.mcp.session import Session

NAMES = ("emoji-headers", "plain-markdown")


def _with_cap(root, cap):
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["conflict_cap"] = cap  # manifest.json is not in its own file list
    (root / "manifest.json").write_text(json.dumps(manifest))
    return Index.load(root)


def test_resolve_set_uses_the_manifest_cap(tmp_path):
    root = make_index(tmp_path, NAMES)
    ids = [skill_id(root, n) for n in NAMES]
    cache = ExtractCache(tmp_path / "xc")
    default = Session(_with_cap(root, "all"), extract_cache=cache).resolve_set(ids)
    assert default["included"] == ids and default["warnings"]
    vocab = Session(_with_cap(root, "vocabulary"), extract_cache=cache).resolve_set(ids)
    assert vocab["included"] == ids[:1]
    assert vocab["excluded"][0]["reason"] == "conflict"
