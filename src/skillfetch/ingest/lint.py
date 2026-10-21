"""Static lint: the minimal checks we own (index-format.md §1.3)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from pydantic import BaseModel

from skillfetch.ingest.skillfile import SKILL_FILE, SkillDoc, read_skill

MAX_BODY_LINES = 500
MAX_BODY_TOKENS = 5000  # estimated as characters / 4

_INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
_INLINE_CODE = re.compile(r"`+[^`]*`+")
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
# Link targets that stand for a link the reader fills in: "[Title](URL)", "{baseDir}/x.md",
# "${SKILL_DIR}/x", "<path>", "...".
_PLACEHOLDER = re.compile(
    r"[{}$]|^(?:url|uri|link|path|href|target|todo|tbd|placeholder|\.\.\.|…)$", re.IGNORECASE
)


class Issue(BaseModel):
    rule: str
    message: str
    file: str = SKILL_FILE
    line_no: int | None = None


class LintResult(BaseModel):
    errors: list[Issue] = []
    warnings: list[Issue] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def _link_targets(doc: SkillDoc):
    """(line_no, target) for every relative-looking link outside code."""
    in_fence = False
    for line_no, line in enumerate(doc.body_lines, doc.body_start):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        text = _INLINE_CODE.sub("", line)
        targets = [m.group(1) for m in _INLINE_LINK.finditer(text)]
        if ref := _REF_DEF.match(text):
            targets.append(ref.group(1))
        for target in targets:
            target = target.strip("<>").strip()
            if not target or target.startswith("#") or _SCHEME.match(target):
                continue
            yield line_no, target


def _check_link(skill_dir: Path, line_no: int, target: str) -> Issue | None:
    path = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not path:
        return None
    if path.startswith("/"):
        return Issue(
            rule="lint.link-outside-skill",
            message=f"link to absolute path {target!r}; skills must be self-contained",
            line_no=line_no,
        )
    root = skill_dir.resolve()
    resolved = (skill_dir / path).resolve()
    if not resolved.is_relative_to(root):
        return Issue(
            rule="lint.link-outside-skill",
            message=f"link {target!r} points outside the skill folder",
            line_no=line_no,
        )
    if not resolved.exists():
        return Issue(
            rule="lint.broken-link",
            message=f"link target {target!r} does not exist",
            line_no=line_no,
        )
    return None


def lint_skill(skill_dir: Path) -> LintResult:
    result = LintResult()
    if not (skill_dir / SKILL_FILE).is_file():
        result.errors.append(Issue(rule="lint.missing-skill-md", message="no SKILL.md in folder"))
        return result

    doc = read_skill(skill_dir)
    if doc.frontmatter_error is not None:
        result.errors.append(
            Issue(
                rule=f"lint.frontmatter-{doc.frontmatter_error_kind}",
                message=doc.frontmatter_error,
                line_no=doc.frontmatter_error_line,
            )
        )
        if doc.frontmatter_error_kind != "invalid":
            return result  # without a closed block there is no reliable body to check
    else:
        for key in ("name", "description"):
            value = doc.frontmatter.get(key)
            if not isinstance(value, str) or not value.strip():
                result.errors.append(
                    Issue(
                        rule=f"lint.missing-{key}",
                        message=f"frontmatter needs a non-empty '{key}'",
                        line_no=1,
                    )
                )

    body = doc.body_lines
    if len(body) > MAX_BODY_LINES:
        result.warnings.append(
            Issue(
                rule="lint.body-too-long",
                message=f"body has {len(body)} lines (> {MAX_BODY_LINES})",
            )
        )
    tokens = len("\n".join(body)) // 4
    if tokens > MAX_BODY_TOKENS:
        result.warnings.append(
            Issue(
                rule="lint.body-too-many-tokens",
                message=f"body is ~{tokens} tokens (> {MAX_BODY_TOKENS})",
            )
        )

    for line_no, target in _link_targets(doc):
        if _PLACEHOLDER.search(target):
            result.warnings.append(
                Issue(
                    rule="lint.placeholder-link",
                    message=f"link target {target!r} looks like a placeholder; not checked",
                    line_no=line_no,
                )
            )
        elif issue := _check_link(skill_dir, line_no, target):
            result.errors.append(issue)
    return result
