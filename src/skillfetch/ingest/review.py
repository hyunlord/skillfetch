"""Semantic review (docs/design/review.md): a fixed checklist applied to a skill's files by a
model, on top of the rule-based scan. Every finding quotes its line, and the quote is checked
against the file.

- `ClaudeReviewer` (review_claude.py): `skillfetch scan --review`, one isolated `claude -p` per
  skill with the user's own Claude Code login (as `--claude-code` extraction runs), cached.
- `host_review`: what the MCP tool `scan_skill(review=true)` returns for the host agent to apply
  itself: the checklist and the files with line numbers. The server never calls a model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from importlib import resources
from pathlib import Path

from pydantic import BaseModel

from skillfetch.ingest.injection import load_rules

CHECKLIST = resources.files("skillfetch.ingest").joinpath("review_checklist.md").read_text()
CHECKLIST_SHA = hashlib.sha256(CHECKLIST.encode()).hexdigest()
CATEGORIES = (
    "send-out",
    "remote-instructions",
    "destructive",
    "disable-safeguards",
    "conceal",
    "authority",
    "hidden-text",
)
MAX_CHARS = 60_000
TEXT_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".toml"}
DEFAULT_CACHE = Path("~/.skillfetch/review-cache").expanduser()
FORMAT = (
    "\nReply with one JSON object and nothing else:\n"
    '{"findings": [{"category": one of ' + json.dumps(list(CATEGORIES)) + ', "file": "<path as '
    'given>", "line": <line number>,\n"quote": "<the line, exactly as written>", "why": "<one '
    'sentence>"}]}\n'
)
SYSTEM = CHECKLIST + FORMAT


class ReviewFinding(BaseModel):
    category: str
    file: str
    line: int
    quote: str
    why: str


class ReviewFile(BaseModel):
    path: str
    text: str  # "<line number>| <line>" per line


class Review(BaseModel):
    by: str  # "claude -p (<model>)", or "host agent" for scan_skill(review=true)
    checklist_sha: str = CHECKLIST_SHA
    findings: list[ReviewFinding] = []
    unverified: int = 0  # findings whose quote is in no file sent: dropped
    not_reviewed: list[str] = []  # files past MAX_CHARS
    error: str | None = None
    cost_usd: float | None = None
    # host mode only: the checklist and the numbered files the host agent reads
    checklist: str | None = None
    files: list[ReviewFile] | None = None


def review_files(
    skill_dir: Path, max_chars: int = MAX_CHARS
) -> tuple[list[tuple[str, str]], list[str]]:
    """(path, text) of SKILL.md, then the folder's other text and script files in path order,
    up to max_chars in all; plus the paths left out. Symbolic links are never read."""
    exts = TEXT_EXTENSIONS | set(load_rules().script_extensions)
    paths = []
    for dirpath, dirnames, filenames in os.walk(skill_dir, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in filenames:
            p = Path(dirpath) / name
            if p.is_symlink() or p.suffix.lower() not in exts:
                continue
            paths.append(p.relative_to(skill_dir).as_posix())
    paths.sort(key=lambda r: (r != "SKILL.md", r))
    files, left, used = [], [], 0
    for rel in paths:
        text = (skill_dir / rel).read_bytes().decode("utf-8", errors="replace")
        if used + len(text) > max_chars:
            left.append(rel)
            continue
        files.append((rel, text))
        used += len(text)
    return files, left


def numbered(text: str) -> str:
    return "\n".join(f"{i}| {line}" for i, line in enumerate(text.split("\n"), 1))


def request_text(files: list[tuple[str, str]]) -> str:
    parts = [f"=== FILE: {rel} ===\n{numbered(text)}" for rel, text in files]
    return "Review this skill.\n\n" + "\n\n".join(parts)


_PREFIX = re.compile(r"^\d+\|\s?")


def _norm(s: str) -> str:
    return " ".join(s.split())


def verify(raw: list[dict], files: list[tuple[str, str]]) -> tuple[list[ReviewFinding], int]:
    """Keep the findings whose quote occurs in the cited line; else move them to the first line
    of the same file (or of any file) that holds it; drop the rest (counted)."""
    lines = {rel: text.split("\n") for rel, text in files}
    kept, dropped = [], 0
    for f in raw:
        if not isinstance(f, dict) or f.get("category") not in CATEGORIES:
            dropped += 1
            continue
        # the model may copy the "<n>| " prefix the request adds
        quote = _norm(_PREFIX.sub("", str(f.get("quote", "")).strip()).strip("`"))
        if not quote:
            dropped += 1
            continue
        rel, line = str(f.get("file", "")), f.get("line")
        where = None
        cited = rel in lines and isinstance(line, int) and 1 <= line <= len(lines[rel])
        if cited and quote in _norm(lines[rel][line - 1]):
            where = (rel, line)
        if where is None:
            order = ([rel] if rel in lines else []) + [r for r in lines if r != rel]
            where = next(
                ((r, i) for r in order for i, ln in enumerate(lines[r], 1) if quote in _norm(ln)),
                None,
            )
        if where is None:
            dropped += 1
            continue
        kept.append(
            ReviewFinding(
                category=f["category"],
                file=where[0],
                line=where[1],
                quote=lines[where[0]][where[1] - 1].strip(),
                why=str(f.get("why", "")).strip(),
            )
        )
    return kept, dropped


def host_review(skill_dir: Path) -> Review:
    files, left = review_files(skill_dir)
    return Review(
        by="host agent",
        checklist=CHECKLIST,
        files=[ReviewFile(path=rel, text=numbered(text)) for rel, text in files],
        not_reviewed=left,
    )
