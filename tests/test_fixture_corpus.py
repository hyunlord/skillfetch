"""Integrity of the hand-labelled fixture corpus (the contract for resolve/)."""

import json

import pytest
import yaml
from conftest import RELATION_KEYS, SKILLS_DIR, fixture_skill_dirs, load_expected

SKILL_DIRS = fixture_skill_dirs()


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    _, fm, _ = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_corpus_size_meets_v01_targets():
    expected = load_expected()
    counts = {rel: sum(1 for v in expected.values() if v == rel) for rel in RELATION_KEYS}
    assert len(SKILL_DIRS) >= 15
    assert counts["conflict"] >= 10
    assert counts["redundant"] >= 5


def test_expected_pairs_reference_existing_skills():
    names = {d.name for d in SKILL_DIRS}
    for pair in load_expected():
        assert pair <= names, f"unknown skill in expected.yaml: {sorted(pair - names)}"


def test_every_skill_dir_has_constraints_file():
    on_disk = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    assert on_disk == {d.name for d in SKILL_DIRS}, "skill dir without SKILL.md"
    for d in SKILL_DIRS:
        assert (d / "constraints.json").is_file(), f"{d.name}: missing constraints.json"


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda d: d.name)
def test_frontmatter_name_matches_dir(skill_dir):
    fm = _frontmatter((skill_dir / "SKILL.md").read_text())
    assert fm["name"] == skill_dir.name
    assert fm["description"]


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda d: d.name)
def test_evidence_lines_quote_the_skill(skill_dir):
    lines = (skill_dir / "SKILL.md").read_text().splitlines()
    data = json.loads((skill_dir / "constraints.json").read_text())
    for c in data["constraints"]:
        ev = c["evidence"]
        assert ev["text"].strip(), f"{skill_dir.name}: empty evidence text"
        assert 1 <= ev["line_no"] <= len(lines), f"{skill_dir.name}: line_no out of range"
        assert ev["text"] in lines[ev["line_no"] - 1], (
            f"{skill_dir.name}:{ev['line_no']} does not contain {ev['text']!r}"
        )
