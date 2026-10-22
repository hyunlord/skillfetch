import json
from functools import cache
from pathlib import Path

import pytest

from skillfetch.ingest.calibrate import LABEL_KEYS, load_labels
from skillfetch.resolve.models import Constraint, Skill

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SKILLS_DIR = FIXTURES_DIR / "skills"
EXPECTED_PATH = FIXTURES_DIR / "expected.yaml"

RELATION_KEYS = LABEL_KEYS


def fixture_skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file())


def load_fixture_skill(skill_dir: Path) -> Skill:
    data = json.loads((skill_dir / "constraints.json").read_text())
    constraints = [
        Constraint.model_validate({**raw, "id": f"{skill_dir.name}#c{i}"})
        for i, raw in enumerate(data["constraints"], 1)
    ]
    return Skill(id=skill_dir.name, constraints=constraints)


@cache
def load_corpus(cap: str = "all") -> dict[str, Skill]:
    """The fixture skills with their fan-out flags: fan-out is a property of the corpus
    (constraints.md §3 row 14a), so the contract is checked with it, as scan does."""
    from skillfetch.resolve.relation import fan_out_map

    return fan_out_map({d.name: load_fixture_skill(d) for d in fixture_skill_dirs()}, cap)


def load_expected() -> dict[frozenset[str], str]:
    """Labelled skill-level relations, keyed by unordered pair of skill names.

    Directional `subsumes` entries are labelled "subsumes:<superset>"."""
    return load_labels(EXPECTED_PATH)


DEFAULT_BODY = "# Title\n\nSome background text.\n"


def write_skill(
    root: Path,
    name: str,
    body: str = DEFAULT_BODY,
    *,
    frontmatter: str | None = None,
    files: dict[str, str] | None = None,
) -> Path:
    """Write a throwaway skill folder for ingest tests."""
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    if frontmatter is None:
        frontmatter = f"---\nname: {name}\ndescription: A test skill.\n---\n"
    (skill_dir / "SKILL.md").write_text(frontmatter + body)
    for rel, content in (files or {}).items():
        path = skill_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return skill_dir


# --- recorded API responses -------------------------------------------------------------------

RESPONSES_DIR = FIXTURES_DIR / "extract" / "responses"


def _ns(value):
    from types import SimpleNamespace

    if isinstance(value, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_ns(v) for v in value]
    return value


def recorded(name: str) -> dict:
    return json.loads((RESPONSES_DIR / name).read_text())


class FakeClient:
    """Replays recorded Messages API responses; records every request it receives.

    Each entry is a response dict, or a callable(request) -> response dict."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.requests: list[dict] = []
        self.messages = self

    def create(self, **request):
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeClient: unexpected API call")
        nxt = self._responses.pop(0)
        return _ns(nxt(request) if callable(nxt) else nxt)


def oracle(request: dict) -> dict:
    """A recorded-shape response that extracts exactly the hand labels of the fixture skill
    named in the request (a perfect extractor), for pipeline and CLI tests."""
    import re

    text = request["messages"][0]["content"]
    name = re.search(r"\| name: (\S+)", text).group(1)
    skill = load_corpus()[name]
    result = {
        "summary": f"{name} summary",
        "keywords": [name],
        "tags": {"languages": [], "frameworks": [], "phase": [], "domain": []},
        "synthetic_queries": [f"use {name}"],
        "constraints": [c.model_dump(mode="json", exclude={"id"}) for c in skill.constraints],
        "consumes": [],
        "produces": [],
        "requires_tools": [],
    }
    return {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps(result)}],
        "usage": {
            "input_tokens": 400,
            "output_tokens": 300,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 2400,
        },
    }


class OracleClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.messages = self

    def create(self, **request):
        self.requests.append(request)
        return _ns(oracle(request))


class FakeOpenAIClient:
    """Replays recorded Chat Completions responses (`client.chat.completions.create`).

    Entries are response dicts, exceptions to raise, or callables(request)."""

    def __init__(self, *responses):
        from types import SimpleNamespace

        self._responses = list(responses)
        self.requests: list[dict] = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **request):
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeOpenAIClient: unexpected API call")
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return _ns(nxt(request) if callable(nxt) else nxt)


class FakeBadRequest(Exception):
    """Shaped like openai.BadRequestError: status_code and the offending `param`."""

    status_code = 400

    def __init__(self, param):
        super().__init__(f"Unsupported parameter: {param}")
        self.param = param


def make_git_source(path: Path, skills: dict[str, Path], branch: str = "main") -> str:
    """A local git repo with skills/<name>/ copied from fixture skill dirs; returns the
    HEAD commit. Used as a `kind: git` source through a file:// URL."""
    import shutil
    import subprocess

    for name, src in skills.items():
        shutil.copytree(src, path / "skills" / name)
    run = lambda *a: subprocess.run(["git", *a], cwd=path, check=True, capture_output=True)  # noqa: E731
    run("init", "-q", "-b", branch)
    run("add", "-A")
    run("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return run("rev-parse", "HEAD").stdout.decode().strip()


@pytest.fixture(autouse=True)
def _local_git_repos(monkeypatch):
    """Fixture git sources are local repos (file://); production allows https only."""
    from skillfetch.ingest import snapshot

    monkeypatch.setattr(snapshot, "GIT_URL_PREFIXES", ("https://", "file://"))
