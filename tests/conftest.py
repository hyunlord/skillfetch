import json
from functools import cache
from pathlib import Path

import yaml

from skillfetch.resolve.models import Constraint, Skill

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SKILLS_DIR = FIXTURES_DIR / "skills"
EXPECTED_PATH = FIXTURES_DIR / "expected.yaml"

RELATION_KEYS = ("conflict", "redundant", "tension", "needs_review")


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
    """Labelled skill-level relations, keyed by unordered pair of skill names."""
    raw = yaml.safe_load(EXPECTED_PATH.read_text())
    expected: dict[frozenset[str], str] = {}
    for relation in RELATION_KEYS:
        for a, b in raw.get(relation) or []:
            pair = frozenset((a, b))
            assert len(pair) == 2, f"self-pair in expected.yaml: {a}"
            assert pair not in expected, f"pair listed twice in expected.yaml: {a}, {b}"
            expected[pair] = relation
    return expected
