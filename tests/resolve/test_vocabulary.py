"""Controlled subject vocabulary (constraints.md §1.1)."""

import pytest

from skillfetch.resolve.relation import normalize_term
from skillfetch.resolve.vocabulary import VOCABULARY, choice_of, lookup


@pytest.mark.parametrize("subject", ["package-manager", "formatter", "test-runner", "build-tool"])
def test_tooling_choices_are_exclusive(subject):
    term = lookup(subject)
    assert term is not None and term.exclusive
    assert term.ecosystems, "an exclusive term needs at least one ecosystem of alternatives"


@pytest.mark.parametrize("subject", ["linter", "naming-convention", "emoji", "type-hints"])
def test_other_terms_are_not_exclusive(subject):
    term = lookup(subject)
    assert term is not None and not term.exclusive


def test_lookup_normalizes():
    assert lookup("Package-Managers").name == "package-manager"
    assert lookup("tests-first").name == "tests-first"
    assert lookup("not-a-term") is None


def test_only_exclusive_terms_have_ecosystems():
    for term in VOCABULARY:
        assert bool(term.ecosystems) == term.exclusive, term.name


def test_alternatives_are_unique_across_ecosystems():
    for term in VOCABULARY:
        seen: set[str] = set()
        for eco in term.ecosystems:
            assert all(normalize_term(alt) == alt for alt in eco.choices), eco.name
            assert not seen & eco.choices, f"{term.name}: {seen & eco.choices}"
            seen |= eco.choices


@pytest.mark.parametrize(
    "obj, expected",
    [
        ("pnpm", ("javascript", "pnpm")),
        ("pnpm workspaces", ("javascript", "pnpm")),
        ("uv", ("python", "uv")),
        ("Poetry", ("python", "poetry")),
        ("conda", ("conda", "conda")),
        ("a conda environment", ("conda", "conda")),
        ("npm or yarn", None),
        ("our in-house installer", None),
        (None, None),
    ],
)
def test_choice_of(obj, expected):
    assert choice_of(lookup("package-manager"), obj) == expected
