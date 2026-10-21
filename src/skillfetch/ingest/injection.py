"""Static injection scan (index-format.md §1.4). Rules live in scan_rules.yaml."""

from __future__ import annotations

import os
import re
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from skillfetch.ingest.skillfile import SKILL_FILE, read_text, skill_files

TEXT_SUFFIXES = frozenset({".md", ".markdown", ".mdx", ".txt"})
_NEGATED = re.compile(r"(?:\bnot|\bnever|n't|\bno|\bwithout)\s+(?:[\w'-]+\s+){0,2}$", re.I)
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_AUTOLINK = re.compile(r"<https?://[^>]*>", re.I)
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
_MAX_EVIDENCE = 160


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    family: str
    pattern: str
    target: Literal["line", "outside_links", "html_comment"] = "line"
    allow_negated: bool = False
    allow_quoted: bool = False
    case_sensitive: bool = False
    effect: Literal["fail", "warn"] | None = None  # overrides the family's effect

    def compiled(self) -> re.Pattern[str]:
        return _compile(self.pattern, self.case_sensitive)


@cache
def _compile(pattern: str, case_sensitive: bool) -> re.Pattern[str]:
    return re.compile(pattern, 0 if case_sensitive else re.I)


class RuleSet(BaseModel):
    version: int
    effects: dict[str, Literal["fail", "warn"]]
    script_dirs: list[str]
    script_extensions: list[str]
    rules: list[Rule]


class Hit(BaseModel):
    rule_id: str
    family: str
    effect: Literal["fail", "warn"]
    file: str
    line_no: int
    line: str
    quoted: bool = False  # every match was inside quotation marks: downgraded to warn


class ScanResult(BaseModel):
    failures: list[Hit] = []
    warnings: list[Hit] = []
    scripts: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def has_scripts(self) -> bool:
        return bool(self.scripts)


@cache
def load_rules(path: Path | None = None) -> RuleSet:
    if path is None:
        text = resources.files("skillfetch.ingest").joinpath("scan_rules.yaml").read_text()
    else:
        text = path.read_text()
    raw = yaml.safe_load(text)
    return RuleSet(
        version=raw["version"],
        effects=raw["effects"],
        script_dirs=raw["scripts"]["dirs"],
        script_extensions=raw["scripts"]["extensions"],
        rules=[Rule.model_validate(r) for r in raw["rules"]],
    )


def _evidence(line: str) -> str:
    line = _INVISIBLE.sub(lambda m: f"<U+{ord(m.group()):04X}>", line.strip())
    return line if len(line) <= _MAX_EVIDENCE else line[:_MAX_EVIDENCE] + "…"


def _outside_links(line: str) -> str:
    if _REF_DEF.match(line):
        return ""
    return _AUTOLINK.sub("", _LINK_TARGET.sub("]", line))


def _inside_quotes(text: str, start: int, end: int) -> bool:
    return any(q.start() < start and end < q.end() for q in _QUOTED.finditer(text))


def _matches(rule: Rule, text: str) -> Literal["plain", "quoted"] | None:
    """How the rule matches `text`: "plain", only inside quotation marks ("quoted", for
    rules with allow_quoted), or not at all (None)."""
    quoted = False
    for m in rule.compiled().finditer(text):
        if rule.allow_negated and _NEGATED.search(text[: m.start()]):
            continue
        if rule.allow_quoted and _inside_quotes(text, m.start(), m.end()):
            quoted = True
            continue
        return "plain"
    return "quoted" if quoted else None


def scan_text(text: str, file: str = SKILL_FILE, rules: RuleSet | None = None) -> list[Hit]:
    rules = rules or load_rules()
    lines = text.split("\n")
    hits: list[Hit] = []
    for rule in rules.rules:
        if rule.target == "html_comment":
            for m in _HTML_COMMENT.finditer(text):
                if how := _matches(rule, m.group(1)):
                    line_no = text.count("\n", 0, m.start()) + 1
                    hits.append(_hit(rule, rules, file, line_no, lines[line_no - 1], how))
            continue
        for line_no, line in enumerate(lines, 1):
            target = _outside_links(line) if rule.target == "outside_links" else line
            if how := _matches(rule, target):
                hits.append(_hit(rule, rules, file, line_no, line, how))
    return sorted(hits, key=lambda h: (h.file, h.line_no, h.rule_id))


def _hit(rule: Rule, rules: RuleSet, file: str, line_no: int, line: str, how: str) -> Hit:
    quoted = how == "quoted"
    return Hit(
        rule_id=rule.id,
        family=rule.family,
        effect="warn" if quoted else rule.effect or rules.effects[rule.family],
        file=file,
        line_no=line_no,
        line=_evidence(line),
        quoted=quoted,
    )


def _is_script(path: Path, rel: str, rules: RuleSet) -> bool:
    if rel.split("/", 1)[0] in rules.script_dirs:
        return True
    if path.suffix.lower() in rules.script_extensions:
        return True
    return os.access(path, os.X_OK)


def scan_skill(skill_dir: Path, rules: RuleSet | None = None) -> ScanResult:
    rules = rules or load_rules()
    hits: list[Hit] = []
    if (skill_dir / SKILL_FILE).is_file():
        hits += scan_text(read_text(skill_dir / SKILL_FILE), SKILL_FILE, rules)
    scripts = []
    for path in skill_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        if _is_script(path, rel, rules):
            scripts.append(rel)
        elif path.suffix.lower() in TEXT_SUFFIXES:
            hits += scan_text(read_text(path), rel, rules)
    result = ScanResult(scripts=scripts)
    for hit in hits:
        (result.failures if hit.effect == "fail" else result.warnings).append(hit)
    return result
