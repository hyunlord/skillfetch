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
_EXCLUDING = re.compile(r"\b(?:except|not|instead\s+of|rather\s+than|other\s+than)\b", re.I)
_WORD = re.compile(r"[a-z0-9]+")


def lookup(subject: str) -> Term | None:
    return _BY_NAME.get(normalize_term(subject))


def choice_of(term: Term | None, obj: str | None) -> tuple[str, str] | None:
    """(ecosystem, choice) if `obj` names exactly one known alternative of `term`.

    Matching is on whole words of the normalized object, so "pnpm workspaces" is
    pnpm. Objects naming no known alternative, or more than one ("npm or yarn"),
    return None, and so do objects that name an alternative to exclude it ("anything
    except npm", "not yarn", "pnpm instead of npm"): the relation then needs review.
    """
    if term is None or obj is None:
        return None
    if _EXCLUDING.search(obj):
        return None
    words = set(_WORD.findall(normalize_term(obj)))
    found = [(eco.name, choice) for eco in term.ecosystems for choice in eco.choices & words]
    return found[0] if len(found) == 1 else None


# --- conditions (constraints.md §1) -----------------------------------------------------------
#
# A condition limits a rule to a language, a framework or a kind of file ("django", "docx",
# "migrations"). Extraction post-processing removes a condition only when it reads like a
# clause: a situation ("when fixing a bug"), a purpose ("if they make it friendlier"). Any
# other phrase is kept; an unlisted name such as "latex" or "blazor" is a real condition.
# (Until v5 conditions were closed against word lists, which nulled docx, latex, blazor, ...)


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_CLAUSE_WORDS = _words(
    """when whenever if unless once after before while during until wherever where whether
    because since so i me you we us they them he she it its their your our is are was were
    be been being am has have had do does did can could should would will must may might
    shall"""
)
MAX_CONDITION_WORDS = 6


_RAW_WORD = re.compile(r"[A-Za-z0-9]+")


def _acronyms(text: str) -> set[str]:
    return {w.lower() for w in _RAW_WORD.findall(text) if len(w) >= 2 and w.isupper()}


def condition_is_clause(condition: str, evidence: str = "") -> bool:
    """A condition phrased as a clause: a subordinating word, a pronoun, an auxiliary or
    modal verb, or more than MAX_CONDITION_WORDS words. An acronym is not a clause word: an
    all-caps word of two or more letters in the condition or, since extraction lowercases
    conditions, on the evidence line ("for US transfers" -> condition "us transfers")."""
    words = _RAW_WORD.findall(condition)
    if len(words) > MAX_CONDITION_WORDS:
        return True
    acronyms = _acronyms(condition) | _acronyms(evidence)
    return any(w.lower() in _CLAUSE_WORDS and w.lower() not in acronyms for w in words)


# --- free-text subjects that contain a term -----------------------------------------------------


def term_words(text: str) -> set[str]:
    return set(_WORD.findall(normalize_term(text)))


def contained_term(subject: str) -> tuple[Term, set[str]] | None:
    """The vocabulary term all of whose words occur in a free-text subject (the longest one),
    with the subject's remaining words. None for a subject that already is a term."""
    if lookup(subject) is not None:
        return None
    words = term_words(subject)
    found = [t for t in VOCABULARY if term_words(t.name) <= words]
    if not found:
        return None
    term = max(found, key=lambda t: len(term_words(t.name)))
    return term, words - term_words(term.name)
