"""Checks `skillfetch scan` adds before installing a skill (index-format.md §5.1): size
(SKILL.md tokens, file count, total bytes) and dated claims (prose lines that state a year or
a version number, which may have changed since a model was trained, or be wrong)."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from skillfetch.ingest.skillfile import SKILL_FILE, read_text, skill_files

# Size warnings. A SKILL.md over MAX_SKILL_MD_TOKENS does not fit load_skills' default budget
# on its own; a folder with many or large files is one an agent may spend its turns reading.
MAX_SKILL_MD_TOKENS = 8000  # characters / 4, the convention of token_estimate
MAX_FILES = 20  # SKILL.md and every other file of the skill (skill_files)
MAX_TOTAL_BYTES = 1_000_000

_YEAR = r"\b20[1-3]\d\b"
_VERSION = r"\bv\d+(?:\.\d+)+\b|\b\d+\.\d+\.\d+\b"
_PRODUCTS = (
    r"React|Next\.js|Node(?:\.js)?|Python|TypeScript|Swift|SwiftUI|iOS|iPadOS|macOS|watchOS|"
    r"visionOS|Android|Kotlin|Java|Go|Rust|Vue|Nuxt|Angular|Svelte|SvelteKit|Tailwind(?: CSS)?|"
    r"Django|Rails|Laravel|Spring Boot|PostgreSQL|Postgres|MySQL|Xcode|Expo|Bun|Deno|Vite|"
    r"Pydantic|Prisma|Drizzle|Remix|Astro|Gradle|Terraform|Kubernetes|Docker|\.NET|C#|PHP|Ruby|"
    r"Flutter|Dart|Electron|ESLint|Jest|Vitest|Playwright|Webpack|Turbopack|Opus|Sonnet|Haiku|"
    r"GPT|Gemini|Claude Code|OWASP Top 10|WCAG|ASVS|HTTP|TLS|OAuth|OpenAPI|Material"
)
_PRODUCT_VERSION = rf"\b(?:{_PRODUCTS})[ -]?(?:v)?\d+(?:\.\d+)*\b"
DATED = re.compile(rf"{_YEAR}|{_VERSION}|{_PRODUCT_VERSION}")
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
DATED_NOTE = (
    "states a year or version: it may have changed since the model was trained, "
    "or be wrong; check the official docs"
)
_MAX_LINE = 200


class SkillSize(BaseModel):
    skill_md_tokens: int
    files: int
    total_bytes: int
    warnings: list[str] = []


class DatedLine(BaseModel):
    file: str
    line_no: int
    line: str
    matches: list[str]


def skill_size(skill_dir: Path) -> SkillSize:
    """SKILL.md's tokens (characters / 4), and the files and bytes of the whole skill
    (SKILL.md plus skill_files: no hidden files, caches or symbolic links)."""
    skill_md = skill_dir / SKILL_FILE
    paths = [skill_md, *skill_files(skill_dir)]
    tokens = len(read_text(skill_md)) // 4
    total = sum(p.stat().st_size for p in paths)
    warnings = []
    if tokens > MAX_SKILL_MD_TOKENS:
        warnings.append(f"SKILL.md is ~{tokens:,} tokens (over {MAX_SKILL_MD_TOKENS:,})")
    if len(paths) > MAX_FILES:
        warnings.append(f"{len(paths)} files (over {MAX_FILES})")
    if total > MAX_TOTAL_BYTES:
        limit = MAX_TOTAL_BYTES // 1_000_000
        warnings.append(f"{total / 1_000_000:.1f} MB in total (over {limit} MB)")
    return SkillSize(skill_md_tokens=tokens, files=len(paths), total_bytes=total, warnings=warnings)


def dated_lines(skill_dir: Path) -> list[DatedLine]:
    """Prose lines of the skill's Markdown files (SKILL.md first) that state a year (2010-2039),
    a version number, or a named product with a version. Lines inside fenced code blocks are
    skipped: manifests and code pin versions on purpose."""
    files = [skill_dir / SKILL_FILE] + [p for p in skill_files(skill_dir) if p.suffix == ".md"]
    out = []
    for path in files:
        fenced = False
        for no, line in enumerate(read_text(path).split("\n"), 1):
            if _FENCE.match(line):
                fenced = not fenced
                continue
            if fenced or len(line) > 2000:
                continue
            found = [m.group(0) for m in DATED.finditer(line)]
            if found:
                text = line.strip()
                out.append(
                    DatedLine(
                        file=path.relative_to(skill_dir).as_posix(),
                        line_no=no,
                        line=text if len(text) <= _MAX_LINE else text[: _MAX_LINE - 1] + "…",
                        matches=sorted(set(found)),
                    )
                )
    return out
