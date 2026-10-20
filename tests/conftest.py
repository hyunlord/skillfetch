import json
from functools import cache
from pathlib import Path

import yaml

from skillfetch.resolve.models import Constraint, Skill

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SKILLS_DIR = FIXTURES_DIR / "skills"
EXPECTED_PATH = FIXTURES_DIR / "expected.yaml"

RELATION_KEYS = ("conflict", "redundant", "subsumes", "tension", "needs_review")


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
def load_corpus() -> dict[str, Skill]:
    return {d.name: load_fixture_skill(d) for d in fixture_skill_dirs()}


def load_expected() -> dict[frozenset[str], str]:
    """Labelled skill-level relations, keyed by unordered pair of skill names.

    Directional `subsumes` entries are labelled "subsumes:<superset>".
    """
    raw = yaml.safe_load(EXPECTED_PATH.read_text())
    expected: dict[frozenset[str], str] = {}
    for relation in RELATION_KEYS:
        for a, b in raw.get(relation) or []:
            pair = frozenset((a, b))
            assert len(pair) == 2, f"self-pair in expected.yaml: {a}"
            assert pair not in expected, f"pair listed twice in expected.yaml: {a}, {b}"
            expected[pair] = f"subsumes:{a}" if relation == "subsumes" else relation
    return expected


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
