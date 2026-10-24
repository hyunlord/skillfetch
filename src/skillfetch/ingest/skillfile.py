"""Reading, discovering and hashing skill folders (index-format.md §1.2)."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILL_FILE = "SKILL.md"
CONSTRAINTS_FILE = "constraints.json"  # pre-extracted constraints sidecar (local scan, §5)
_SKIP_DIRS = frozenset({"node_modules", "__pycache__"})


@dataclass(frozen=True)
class SkillDoc:
    dir: Path
    lines: list[str]
    frontmatter: dict | None
    frontmatter_error: str | None
    frontmatter_error_kind: str | None  # "missing" | "unclosed" | "invalid"
    frontmatter_error_line: int | None
    body_start: int  # 1-based line number of the first body line

    @property
    def body_lines(self) -> list[str]:
        return self.lines[self.body_start - 1 :]


def read_text(path: Path) -> str:
    text = path.read_bytes().decode("utf-8", errors="replace")
    return text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def read_skill(skill_dir: Path) -> SkillDoc:
    """Parse SKILL.md. Raises FileNotFoundError if it does not exist."""
    lines = read_text(skill_dir / SKILL_FILE).split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    def fail(kind: str, message: str, line: int, body_start: int = 1) -> SkillDoc:
        return SkillDoc(skill_dir, lines, None, message, kind, line, body_start)

    if not lines or lines[0].strip() != "---":
        return fail("missing", "SKILL.md must start with a '---' frontmatter block", 1)
    close = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
    if close is None:
        return fail("unclosed", "frontmatter block is never closed with '---'", 1)
    try:
        data = yaml.safe_load("\n".join(lines[1:close]))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 2 if mark is not None else 1
        problem = getattr(exc, "problem", exc)
        return fail("invalid", f"frontmatter is not valid YAML: {problem}", line, close + 2)
    if not isinstance(data, dict):
        return fail("invalid", "frontmatter must be a YAML mapping", 1, close + 2)
    return SkillDoc(skill_dir, lines, data, None, None, None, close + 2)


def _regular(path: Path) -> bool:
    """A regular file, not a symbolic link (links are skipped everywhere: a skill folder from
    an untrusted source must not make us read, hash or fetch a file outside it)."""
    return path.is_file() and not path.is_symlink()


def discover_skills(
    root: Path, exclude: tuple[str, ...] | list[str] = (), base: Path | None = None
) -> list[Path]:
    """Skill folders under root (a folder with SKILL.md), sorted. Hidden folders, vendored
    dependencies and symbolic links are skipped; folders inside a skill belong to it.
    `exclude` adds folders not to enter: an fnmatch pattern on the folder name, or, when it
    has a "/", on its path relative to `base` (default: root)."""
    if _regular(root / SKILL_FILE):
        return [root]
    base = base or root

    def skipped(folder: Path) -> bool:
        rel = folder.relative_to(base).as_posix()
        return any(
            fnmatch.fnmatch(rel if "/" in pattern else folder.name, pattern.rstrip("/"))
            for pattern in exclude
        )

    found = []
    for current, dirs, files in os.walk(root):  # does not follow directory links
        if SKILL_FILE in files and Path(current) != root and _regular(Path(current) / SKILL_FILE):
            found.append(Path(current))
            dirs.clear()
            continue
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in _SKIP_DIRS and not skipped(Path(current) / d)
        ]
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def _normalized_skill_md(skill_dir: Path) -> str:
    lines = [line.rstrip() for line in read_text(skill_dir / SKILL_FILE).split("\n")]
    return "\n".join(lines).strip("\n") + "\n"


def skill_files(skill_dir: Path) -> list[Path]:
    """Files that make up the skill besides SKILL.md: no hidden files, no caches, no
    constraints sidecar, no symbolic links. Sorted by relative path."""
    out = []
    for current, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _SKIP_DIRS]
        for name in files:
            path = Path(current) / name
            rel = path.relative_to(skill_dir).as_posix()
            if name.startswith(".") or rel in (SKILL_FILE, CONSTRAINTS_FILE):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            out.append(path)
    return sorted(out, key=lambda p: p.relative_to(skill_dir).as_posix())


def content_hash(skill_dir: Path) -> str:
    """sha256 over the normalized SKILL.md and (relative path, sha256) of every other file."""
    h = hashlib.sha256()
    h.update(f"{SKILL_FILE}\0".encode())
    h.update(_normalized_skill_md(skill_dir).encode())
    for path in skill_files(skill_dir):
        rel = path.relative_to(skill_dir).as_posix()
        h.update(f"\0{rel}\0{hashlib.sha256(path.read_bytes()).hexdigest()}".encode())
    return h.hexdigest()
