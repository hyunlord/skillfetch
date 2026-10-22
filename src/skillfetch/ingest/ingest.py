"""`skillfetch ingest <dir>`: lint → injection scan → extract (cache first) for every skill.

Index building (index-format §1.6–§2) is not implemented yet; extraction results live in
the extract cache.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from skillfetch.ingest import credentials
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
        elif (cached := cache.get(outcome.content_hash, model, skill_dir)) is not None:
            outcome.source, outcome.record = "cache", cached
        elif extractor is not None:
            todo.append((outcome, skill_dir))

    fresh = run_extractions(
        [(skill_dir, o.skill_id, o.content_hash) for o, skill_dir in todo], cache, extractor, jobs
    )
    for outcome, _ in todo:
        outcome.source, outcome.record = "api", fresh[outcome.content_hash]
    return outcomes


def run_extractions(
    items: list[tuple[Path, str, str]],
    cache: ExtractCache,
    extractor: Extractor,
    jobs: int = 4,
    errors: dict[str, str] | None = None,
) -> dict[str, ExtractRecord]:
    """Extract (skill_dir, skill_id, content_hash) items in parallel, once per distinct
    content, caching each record. A request that fails (connection, provider or SDK error)
    is not cached: its content hash and error go into `errors` and the run continues, so a
    rerun retries only those. Without an `errors` dict the first such error propagates.
    Rejected credentials are not a per-skill error: they stop the run. Error texts are
    redacted (providers echo key material in them)."""
    secrets = credentials.redaction_secrets()
    unique: dict[str, tuple[Path, str]] = {}
    for skill_dir, skill_id, digest in items:
        unique.setdefault(digest, (skill_dir, skill_id))

    def run(digest: str) -> tuple[str, ExtractRecord | None]:
        skill_dir, skill_id = unique[digest]
        try:
            record = extractor.extract(skill_dir, skill_id, digest)
        except Exception as exc:
            if errors is None or credentials.is_auth_error(exc):
                raise
            errors[digest] = credentials.redact(f"{type(exc).__name__}: {str(exc)[:300]}", *secrets)
            return digest, None
        cache.put(record)
        return digest, record

    if not unique:
        return {}
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return {d: r for d, r in pool.map(run, unique) if r is not None}


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
