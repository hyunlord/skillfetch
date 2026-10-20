from pathlib import Path

import yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SKILLS_DIR = FIXTURES_DIR / "skills"
EXPECTED_PATH = FIXTURES_DIR / "expected.yaml"

RELATION_KEYS = ("conflict", "redundant", "tension", "needs_review")


def fixture_skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file())


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
