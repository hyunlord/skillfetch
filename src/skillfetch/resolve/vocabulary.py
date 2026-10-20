"""Controlled subject vocabulary (constraints.md §1.1).

The extractor maps constraints onto these terms; resolve/ uses the `exclusive`
flag: for an exclusive subject, two different known choices from the same
ecosystem cannot both be followed ("always npm" vs "always pnpm"), even when
neither skill forbids the other's choice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from skillfetch.resolve.terms import normalize_term


@dataclass(frozen=True)
class Ecosystem:
    name: str
    choices: frozenset[str]


@dataclass(frozen=True)
class Term:
    name: str
    group: str
    exclusive: bool = False
    ecosystems: tuple[Ecosystem, ...] = field(default=())


def _eco(name: str, *choices: str) -> Ecosystem:
    return Ecosystem(name, frozenset(normalize_term(c) for c in choices))


def _terms(group: str, *names: str) -> list[Term]:
    return [Term(name, group) for name in names]


VOCABULARY: tuple[Term, ...] = (
    *_terms(
        "formatting",
        "emoji",
        "headers",
        "bullet-points",
        "code-blocks",
        "line-length",
        "trailing-whitespace",
    ),
    *_terms(
        "language",
        "type-hints",
        "docstrings",
        "comments",
        "naming-convention",
        "error-handling",
        "logging",
    ),
    *_terms(
        "process",
        "tests-first",
        "commit-granularity",
        "branch-naming",
        "pr-size",
        "review-before-merge",
    ),
    *_terms(
        "output",
        "response-length",
        "preamble",
        "summary-at-end",
        "ask-before-acting",
        "explain-reasoning",
    ),
    # Several linters routinely run side by side, so `linter` is not exclusive.
    Term("linter", "tooling"),
    Term(
        "package-manager",
        "tooling",
        exclusive=True,
        ecosystems=(
            _eco("javascript", "npm", "pnpm", "yarn", "bun"),
            _eco("python", "pip", "uv", "poetry", "pipenv", "pdm", "conda"),
        ),
    ),
    Term(
        "formatter",
        "tooling",
        exclusive=True,
        ecosystems=(
            _eco("javascript", "prettier", "biome", "dprint"),
            _eco("python", "black", "ruff", "yapf", "autopep8"),
        ),
    ),
    Term(
        "test-runner",
        "tooling",
        exclusive=True,
        ecosystems=(
            _eco("javascript", "jest", "vitest", "mocha", "ava"),
            _eco("python", "pytest", "unittest", "nose2"),
        ),
    ),
    Term(
        "build-tool",
        "tooling",
        exclusive=True,
        ecosystems=(
            _eco("javascript", "vite", "webpack", "esbuild", "rollup", "parcel", "rspack"),
            _eco("jvm", "maven", "gradle", "sbt"),
        ),
    ),
)

_BY_NAME = {normalize_term(t.name): t for t in VOCABULARY}
_WORD = re.compile(r"[a-z0-9]+")


def lookup(subject: str) -> Term | None:
    return _BY_NAME.get(normalize_term(subject))


def choice_of(term: Term | None, obj: str | None) -> tuple[str, str] | None:
    """(ecosystem, choice) if `obj` names exactly one known alternative of `term`.

    Matching is on whole words of the normalized object, so "pnpm workspaces" is
    pnpm. Objects naming no known alternative, or more than one ("npm or yarn"),
    return None.
    """
    if term is None or obj is None:
        return None
    words = set(_WORD.findall(normalize_term(obj)))
    found = [(eco.name, choice) for eco in term.ecosystems for choice in eco.choices & words]
    return found[0] if len(found) == 1 else None
