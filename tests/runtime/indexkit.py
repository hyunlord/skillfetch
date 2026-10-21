"""Build a small real index from fixture skills (a `dir` source, oracle extraction)."""

import json
import shutil
from pathlib import Path

from conftest import SKILLS_DIR, OracleClient, _ns, oracle

from skillfetch.ingest.backends import AnthropicBackend
from skillfetch.ingest.build import build_index
from skillfetch.ingest.extract import Extractor
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.sources import Source

NAMES = (
    "commit-squash",
    "atomic-commits",
    "emoji-headers",
    "clean-headings",
    "pnpm-only",
    "npm-classic",
    "typed-python",
    "tdd-strict",
)
# richer metadata than the plain oracle, so search has something to match
META = {
    "pnpm-only": {
        "keywords": ["pnpm", "javascript", "package manager"],
        "synthetic_queries": ["install dependencies in a node project"],
        "tags": {"languages": ["javascript"], "frameworks": [], "phase": [], "domain": ["tooling"]},
    },
    "typed-python": {
        "keywords": ["type hints", "python", "mypy"],
        "synthetic_queries": ["add type annotations to this python module"],
        "tags": {"languages": ["python"], "frameworks": [], "phase": [], "domain": ["backend"]},
    },
    "emoji-headers": {
        "keywords": ["emoji", "markdown", "headers"],
        "synthetic_queries": ["make my readme headings friendlier"],
        "tags": {"languages": [], "frameworks": [], "phase": ["format"], "domain": ["docs"]},
    },
}


class MetaOracle(OracleClient):
    def create(self, **request):
        self.requests.append(request)
        response = oracle(request)
        data = json.loads(response["content"][0]["text"])
        name = data["summary"].split()[0]
        data.update(META.get(name, {}))
        data["summary"] = f"{name}: {data['summary']}"
        response["content"][0]["text"] = json.dumps(data)
        return _ns(response)


def make_index(tmp_path: Path, names=NAMES, *, trust="verified") -> Path:
    src = tmp_path / "src"
    for name in names:
        shutil.copytree(SKILLS_DIR / name, src / "skills" / name)
        (src / "skills" / name / "LICENSE").write_text(
            "MIT License\n\nPermission is hereby granted"
        )
    source = Source(
        id="fx",
        kind="dir",
        url=str(src),
        root="skills/",
        publisher="fixtures",
        publisher_trust=trust,
    )
    out = tmp_path / "index"
    build_index(
        [source],
        out_dir=out,
        work_dir=tmp_path / "work",
        cache=ExtractCache(tmp_path / "cache"),
        extractor=Extractor(AnthropicBackend(MetaOracle(), "claude-sonnet-5")),
    )
    return out


def skill_id(index_dir: Path, name: str) -> str:
    for line in (index_dir / "skills.jsonl").read_text().splitlines():
        record = json.loads(line)
        if record["name"] == name:
            return record["id"]
    raise KeyError(name)
