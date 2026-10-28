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
MAX_CHARS = 60_000  # per request (scan --review) and per scan_skill(review=true) answer
MAX_CHUNKS = 5  # scan --review reads at most this many requests' worth of a skill
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
    # files (or "<file> from line <n>") left unread: past MAX_CHUNKS requests, or past MAX_CHARS
    # for the host agent. Shown as "partly reviewed"; the advice is then at least CAUTION.
    not_reviewed: list[str] = []
    # a request failed, was cut off or refused (no findings JSON): "review incomplete: read this
    # skill yourself"; the advice is then at least CAUTION (docs/design/review.md §2)
    error: str | None = None
    requests: int = 0  # scan --review: claude -p requests for this skill
    cost_usd: float | None = None
    # host mode only: the checklist and the numbered files the host agent reads
    checklist: str | None = None
    files: list[ReviewFile] | None = None


def text_files(skill_dir: Path) -> list[tuple[str, str]]:
    """(path, text) of SKILL.md, then the folder's other text and script files in path order.
    Symbolic links are never read."""
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
    return [
        (rel, (skill_dir / rel).read_bytes().decode("utf-8", errors="replace")) for rel in paths
    ]


def review_files(
    skill_dir: Path, max_chars: int = MAX_CHARS
) -> tuple[list[tuple[str, str]], list[str]]:
    """text_files up to max_chars in all (the files that fit, in order); plus the paths left
    out. What scan_skill(review=true) hands the host agent."""
    files, left, used = [], [], 0
    for rel, text in text_files(skill_dir):
        if used + len(text) > max_chars:
            left.append(rel)
            continue
        files.append((rel, text))
        used += len(text)
    return files, left


class Part(BaseModel):
    """A file, or a run of its lines, in one request."""

    path: str
    text: str
    start: int = 1  # the file's line number of the first line
    whole: bool = True


def review_chunks(
    skill_dir: Path,
    chunk_chars: int = MAX_CHARS,
    max_chunks: int = MAX_CHUNKS,
    skill_md_only: bool = False,
) -> tuple[list[list[Part]], list[tuple[str, str]], list[str]]:
    """The skill's text files packed into requests of at most chunk_chars each, in order; a file
    longer than that is split between lines, keeping its line numbers. Returns (requests, the
    files read in full or in part, what is left unread past max_chunks requests).
    `skill_md_only` reads SKILL.md alone (a research pass over many skills, numbers.md §32);
    the other files are then neither read nor listed."""
    all_files = text_files(skill_dir)
    if skill_md_only:
        all_files = [(rel, text) for rel, text in all_files if rel == "SKILL.md"]
    pieces: list[Part] = []
    for rel, text in all_files:
        if len(text) <= chunk_chars:
            pieces.append(Part(path=rel, text=text))
            continue
        lines, buf, start = text.split("\n"), [], 1
        for i, line in enumerate(lines, 1):
            line = line[:chunk_chars]  # a line longer than a request is cut
            if buf and sum(len(x) + 1 for x in buf) + len(line) > chunk_chars:
                pieces.append(Part(path=rel, text="\n".join(buf), start=start, whole=False))
                buf, start = [], i
            buf.append(line)
        pieces.append(Part(path=rel, text="\n".join(buf), start=start, whole=False))
    chunks: list[list[Part]] = []
    size = 0
    left: list[str] = []
    for part in pieces:
        if chunks and size + len(part.text) <= chunk_chars:
            chunks[-1].append(part)
            size += len(part.text)
        elif len(chunks) < max_chunks:
            chunks.append([part])
            size = len(part.text)
        elif not any(x == part.path or x.startswith(f"{part.path} from line ") for x in left):
            # once per file: the whole file, or where its unread lines start
            read_any = any(p.path == part.path for c in chunks for p in c)
            left.append(f"{part.path} from line {part.start}" if read_any else part.path)
    read = {p.path for c in chunks for p in c}
    files = [(rel, text) for rel, text in all_files if rel in read]
    return chunks, files, left


def numbered(text: str, start: int = 1) -> str:
    return "\n".join(f"{i}| {line}" for i, line in enumerate(text.split("\n"), start))


def request_text(parts: list[Part], part: int = 1, of: int = 1) -> str:
    """One request. A skill in one request reads "Review this skill." and its whole files; a
    skill split over several says which part it is, and a split file says where it starts."""
    blocks = []
    for p in parts:
        head = p.path if p.whole else f"{p.path} (from line {p.start})"
        blocks.append(f"=== FILE: {head} ===\n{numbered(p.text, p.start)}")
    intro = "Review this skill." if of == 1 else f"Review this skill (part {part} of {of})."
    return intro + "\n\n" + "\n\n".join(blocks)


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
