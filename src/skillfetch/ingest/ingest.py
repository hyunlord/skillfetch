"""`skillfetch ingest <dir>`: lint → injection scan → extract (cache first) for every skill.

Index building (index-format §1.6–§2) is not implemented yet; extraction results live in
the extract cache.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from skillfetch.ingest.extract import DEFAULT_MODEL, Extractor, ExtractRecord
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.skillfile import content_hash, discover_skills


@dataclass
class Outcome:
    skill_id: str
    content_hash: str
    source: Literal["api", "cache", "missing", "skipped"]
    record: ExtractRecord | None = None
    reason: str | None = None


def _skill_id(root: Path, skill_dir: Path) -> str:
    return skill_dir.name if skill_dir == root else skill_dir.relative_to(root).as_posix()


def extract_dir(
    root: Path,
    cache: ExtractCache,
    extractor: Extractor | None,
    *,
    model: str | None = None,
    jobs: int = 4,
) -> list[Outcome]:
    """Extract every skill under root. With extractor=None only the cache is consulted.

    Skills failing lint or the injection scan are never sent. API errors propagate (and are
    not cached), so a rerun resumes; model-output failures are cached like successes."""
    model = extractor.model if extractor else (model or DEFAULT_MODEL)
    outcomes: list[Outcome] = []
    todo: list[tuple[Outcome, Path]] = []
    for skill_dir in discover_skills(root):
        outcome = Outcome(_skill_id(root, skill_dir), content_hash(skill_dir), "missing")
        outcomes.append(outcome)
        if not lint_skill(skill_dir).ok:
            outcome.source, outcome.reason = "skipped", "lint_failed"
        elif not scan_skill(skill_dir).ok:
            outcome.source, outcome.reason = "skipped", "scan_failed"
        elif (cached := cache.get(outcome.content_hash, model)) is not None:
            outcome.source, outcome.record = "cache", cached
        elif extractor is not None:
            todo.append((outcome, skill_dir))

    def run(item: tuple[Outcome, Path]) -> None:
        outcome, skill_dir = item
        record = extractor.extract(skill_dir, outcome.skill_id, outcome.content_hash)
        cache.put(record)
        outcome.source, outcome.record = "api", record

    if todo:
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            for _ in pool.map(run, todo):  # re-raises the first API error
                pass
    return outcomes


def _usd(value: float | None) -> str:
    return "$?" if value is None else f"${value:.5f}"


def render_cost_log(outcomes: list[Outcome]) -> str:
    lines = []
    width = max((len(o.skill_id) for o in outcomes), default=0)
    api_cost, api_calls, cached = 0.0, 0, 0
    unknown_price = False
    for o in outcomes:
        head = f"{o.source:<7} {o.skill_id:<{width}}"
        if o.record is None:
            note = o.reason or "not in cache (run with --with-api)"
            lines.append(f"{head}  {note}")
            continue
        r, u = o.record, o.record.usage
        cost = r.cost_usd
        detail = (
            f"{r.status:<14} in {u.input_tokens} (cache r {u.cache_read_input_tokens}, "
            f"w {u.cache_creation_input_tokens}) out {u.output_tokens}  {_usd(cost)}"
        )
        extras = []
        if r.dropped:
            extras.append(f"{len(r.dropped)} dropped")
        if r.repaired:
            extras.append(f"{len(r.repaired)} line fixes")
        if r.error:
            extras.append(r.error.splitlines()[0][:80])
        lines.append(f"{head}  {detail}" + (f"  [{'; '.join(extras)}]" if extras else ""))
        if o.source == "api":
            api_calls += len(r.attempts)
            unknown_price |= cost is None
            api_cost += cost or 0.0
        else:
            cached += 1
    missing = sum(o.source == "missing" for o in outcomes)
    skipped = sum(o.source == "skipped" for o in outcomes)
    total = f"${api_cost:.4f}" + (" (+ unpriced model)" if unknown_price else "")
    lines.append(
        f"API calls: {api_calls}, cost this run {total} · from cache: {cached} · "
        f"skipped: {skipped} · {missing} not in cache (run with --with-api)"
    )
    return "\n".join(lines)
