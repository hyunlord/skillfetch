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

# Only Markdown is scanned: it is what an agent reads as instructions. License texts
# (LICENSE.md, the OFL that ships with fonts) are legal boilerplate, not instructions.
TEXT_SUFFIXES = frozenset({".md"})
_LEGAL_STEMS = frozenset({"license", "licence", "copying", "notice", "ofl"})
_NEGATED = re.compile(r"(?:\bnot|\bnever|n't|\bno|\bwithout)\s+(?:[\w'-]+\s+){0,2}$", re.I)
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_AUTOLINK = re.compile(r"<https?://[^>]*>", re.I)
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
_MAX_EVIDENCE = 160
MAX_SCAN_LINE = 2000  # longer lines are reported, not matched (ReDoS guard)
LONG_LINE_RULE = "scan.line-too-long"


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    family: str
    pattern: str
    target: Literal["line", "outside_links", "html_comment", "line_with_lead_in"] = "line"
    allow_negated: bool = False
    allow_quoted: bool = False
    case_sensitive: bool = False
    within: str | None = None  # second stage: must match inside the `pattern` match
    unless: str | None = None  # a `pattern` match does not count if this is found inside it
    effect: Literal["fail", "warn", "info"] | None = None  # overrides the family's effect

    def compiled(self) -> re.Pattern[str]:
        return _compile(self.pattern, self.case_sensitive)

    def compiled_within(self) -> re.Pattern[str] | None:
        return _compile(self.within, self.case_sensitive) if self.within else None

    def compiled_unless(self) -> re.Pattern[str] | None:
        return _compile(self.unless, False) if self.unless else None


@cache
def _compile(pattern: str, case_sensitive: bool) -> re.Pattern[str]:
    return re.compile(pattern, 0 if case_sensitive else re.I)


class RuleSet(BaseModel):
    version: int
    effects: dict[str, Literal["fail", "warn", "info"]]
    script_dirs: list[str]
    script_extensions: list[str]
    rules: list[Rule]


class Hit(BaseModel):
    rule_id: str
    family: str
    effect: Literal["fail", "warn", "info"]
    file: str
    line_no: int
    line: str
    quoted: bool = False  # every match was inside quotation marks: downgraded to info


class ScanResult(BaseModel):
    failures: list[Hit] = []
    warnings: list[Hit] = []
    infos: list[Hit] = []  # shown, but neither a failure nor a warning (rules v6)
    scripts: list[str] = []
    # scripts that use the network, run commands, delete files or read secrets: what each one
    # does, by SCRIPT_RISKS (rules v7)
    risky_scripts: dict[str, list[str]] = {}

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
    within, unless = rule.compiled_within(), rule.compiled_unless()
    for m in rule.compiled().finditer(text):
        if within is not None and not within.search(m.group()):
            continue
        if unless is not None and unless.search(m.group()):
            continue
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
    hits: list[Hit] = [
        Hit(
            rule_id=LONG_LINE_RULE,
            family="hidden",
            effect="warn",
            file=file,
            line_no=n,
            line=_evidence(line),
        )
        for n, line in enumerate(lines, 1)
        if len(line) > MAX_SCAN_LINE
    ]
    for rule in rules.rules:
        if rule.target == "html_comment":
            for m in _HTML_COMMENT.finditer(text):
                if how := _matches(rule, m.group(1)):
                    line_no = text.count("\n", 0, m.start()) + 1
                    hits.append(_hit(rule, rules, file, line_no, lines[line_no - 1], how))
            continue
        for line_no, line in enumerate(lines, 1):
            if len(line) > MAX_SCAN_LINE:
                continue
            target = _outside_links(line) if rule.target == "outside_links" else line
            if rule.target == "line_with_lead_in" and line_no > 1:
                lead = lines[line_no - 2].rstrip()
                if lead.endswith(":") and len(lead) <= MAX_SCAN_LINE:
                    target = f"{lead} {line}"  # "Load the rules from:" / next line: the URL
            if how := _matches(rule, target):
                hits.append(_hit(rule, rules, file, line_no, line, how))
    # an info hit adds nothing on a line where its family already warns or fails
    louder = {(h.line_no, h.family) for h in hits if h.effect != "info"}
    hits = [h for h in hits if h.effect != "info" or (h.line_no, h.family) not in louder]
    return sorted(hits, key=lambda h: (h.file, h.line_no, h.rule_id))


def _hit(rule: Rule, rules: RuleSet, file: str, line_no: int, line: str, how: str) -> Hit:
    quoted = how == "quoted"
    return Hit(
        rule_id=rule.id,
        family=rule.family,
        effect="info" if quoted else rule.effect or rules.effects[rule.family],
        file=file,
        line_no=line_no,
        line=_evidence(line),
        quoted=quoted,
    )


# What makes a bundled script worth reading before install (rules v7, evals/scan-accuracy/): in the
# sample, scripts judged worth a look called the network, ran commands, deleted files or read
# secrets; local helpers that only compute were judged fine.
SCRIPT_RISKS = {
    "network": re.compile(
        r"\b(?:requests\.(?:get|post|put|delete|patch|request)|urllib|http\.client|httpx|aiohttp|"
        r"fetch\(|axios|XMLHttpRequest|Invoke-WebRequest|Invoke-RestMethod|boto3|"
        r"socket\.socket|net/http|reqwest|WebClient|curl\s|wget\s)"
    ),
    "runs commands": re.compile(
        r"\b(?:subprocess|os\.system|os\.popen|child_process|execSync|spawnSync|"
        r"Popen|ShellExecute|Runtime\.getRuntime|eval\s*\(|exec\s*\(|\bsudo\s)"
    ),
    "deletes files": re.compile(
        r"\b(?:os\.remove|os\.unlink|shutil\.rmtree|rmSync|rimraf|fs\.rm|fs\.unlink|"
        r"Remove-Item|send2trash|\.unlink\(|rm\s+-[a-zA-Z]*r[a-zA-Z]*f?\b)"
    ),
    "reads secrets": re.compile(
        r"(?:os\.environ|getenv|process\.env|ENV\[)[^\n]{0,40}(?:KEY|TOKEN|SECRET|PASSWORD)|"
        r"~/\.ssh|\.aws/credentials"
    ),
}
_MAX_SCRIPT_BYTES = 500_000


def script_risks(path: Path) -> list[str]:
    try:
        if path.stat().st_size > _MAX_SCRIPT_BYTES:
            return ["over 500 KB, not read"]
        text = read_text(path)
    except (OSError, UnicodeError):
        return []
    return [what for what, rx in SCRIPT_RISKS.items() if rx.search(text)]


def _is_script(path: Path, rel: str, rules: RuleSet) -> bool:
    if rel.split("/", 1)[0] in rules.script_dirs:
        return True
    if path.suffix.lower() in rules.script_extensions:
        return True
    return os.access(path, os.X_OK)


def scan_skill(skill_dir: Path, rules: RuleSet | None = None) -> ScanResult:
    rules = rules or load_rules()
    hits: list[Hit] = []
    skill_md = skill_dir / SKILL_FILE
    if skill_md.is_file() and not skill_md.is_symlink():
        hits += scan_text(read_text(skill_md), SKILL_FILE, rules)
    scripts, risky = [], {}
    for path in skill_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        if _is_script(path, rel, rules):
            scripts.append(rel)
            if what := script_risks(path):
                risky[rel] = what
        elif path.suffix.lower() in TEXT_SUFFIXES and path.stem.lower() not in _LEGAL_STEMS:
            hits += scan_text(read_text(path), rel, rules)
    result = ScanResult(scripts=scripts, risky_scripts=risky)
    for hit in hits:
        {"fail": result.failures, "warn": result.warnings, "info": result.infos}[hit.effect].append(
            hit
        )
    return result
