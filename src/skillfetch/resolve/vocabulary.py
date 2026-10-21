"""Controlled subject vocabulary (constraints.md §1.1).

The extractor maps constraints onto these terms; resolve/ uses the `exclusive`
flag: for an exclusive subject, two different known choices from the same
ecosystem cannot both be followed ("always npm" vs "always pnpm"), even when
neither skill forbids the other's choice.

`polarity` and `implied_artifact` are used by extraction post-processing
(ingest/extract.py): a negative subject names something rules usually remove,
and an implied artifact is the only place the subject (or subject + object)
can occur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

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
    # Allowed objects (null is always allowed). None = open: any object, as for tool names
    # or values. A closed term keeps extracted objects comparable across skills: "of what
    # you did" and "every change you made" both just restate `summary-at-end`.
    objects: tuple[str, ...] | None = ()
    # "negative": the subject names something rules usually get rid of (trailing whitespace,
    # a preamble), so "strip/remove X" is a ban on X, never a requirement.
    polarity: Literal["neutral", "negative"] = "neutral"
    # The only artifact the subject can occur in, and per-object overrides
    # (emoji in general has none; emoji "in headers" only occurs in markdown).
    implied_artifact: str | None = None
    object_artifacts: tuple[tuple[str, str], ...] = ()


def implied_artifact(term: Term | None, obj: str | None) -> str | None:
    if term is None:
        return None
    if obj is not None:
        for name, artifact in term.object_artifacts:
            if normalize_term(name) == normalize_term(obj):
                return artifact
    return term.implied_artifact


def _eco(name: str, *choices: str) -> Ecosystem:
    return Ecosystem(name, frozenset(normalize_term(c) for c in choices))


def _t(
    group: str,
    name: str,
    *objects: str,
    open_: bool = False,
    polarity: Literal["neutral", "negative"] = "neutral",
    artifact: str | None = None,
    object_artifacts: tuple[tuple[str, str], ...] = (),
) -> Term:
    return Term(
        name,
        group,
        objects=None if open_ else objects,
        polarity=polarity,
        implied_artifact=artifact,
        object_artifacts=object_artifacts,
    )


VOCABULARY: tuple[Term, ...] = (
    _t("formatting", "emoji", "in headers", object_artifacts=(("in headers", "markdown"),)),
    _t(
        "formatting",
        "headers",
        "short",
        "sentence case",
        "title case",
        "numbered",
        artifact="markdown",
    ),
    _t("formatting", "bullet-points"),
    _t("formatting", "code-blocks", "language tag"),
    _t("formatting", "line-length", open_=True),
    _t("formatting", "trailing-whitespace", polarity="negative"),
    _t("language", "type-hints", "public functions", artifact="code"),
    _t("language", "docstrings", "public functions", artifact="code"),
    _t(
        "language",
        "comments",
        "on non-obvious code",
        "restating the code",
        "todo",
        artifact="code",
    ),
    _t("language", "naming-convention", open_=True),
    _t("language", "error-handling", open_=True),
    _t("language", "logging", "print statements", "secrets"),
    _t("process", "tests-first"),
    _t("process", "commit-granularity", "squash", "atomic", artifact="commit-message"),
    _t("process", "branch-naming", open_=True),
    _t("process", "pr-size", open_=True),
    _t("process", "review-before-merge"),
    _t("output", "response-length", "short", "detailed"),
    _t("output", "preamble", polarity="negative", artifact="response"),
    _t("output", "summary-at-end", artifact="response"),
    _t("output", "ask-before-acting", "destructive actions"),
    _t("output", "explain-reasoning", artifact="response"),
    # Several linters routinely run side by side, so `linter` is not exclusive.
    _t("tooling", "linter", open_=True),
    Term(
        "package-manager",
        "tooling",
        exclusive=True,
        objects=None,
        ecosystems=(
            _eco("javascript", "npm", "pnpm", "yarn", "bun"),
            _eco("python", "pip", "uv", "poetry", "pipenv", "pdm"),
            # conda manages environments across languages and routinely hosts pip
            # installs, so it does not exclude the python tools above.
            _eco("conda", "conda", "mamba", "micromamba"),
        ),
    ),
    Term(
        "formatter",
        "tooling",
        exclusive=True,
        objects=None,
        implied_artifact="code",
        ecosystems=(
            _eco("javascript", "prettier", "biome", "dprint"),
            _eco("python", "black", "ruff", "yapf", "autopep8"),
        ),
    ),
    Term(
        "test-runner",
        "tooling",
        exclusive=True,
        objects=None,
        implied_artifact="tests",
        ecosystems=(
            _eco("javascript", "jest", "vitest", "mocha", "ava"),
            _eco("python", "pytest", "unittest", "nose2"),
        ),
    ),
    Term(
        "build-tool",
        "tooling",
        exclusive=True,
        objects=None,
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
