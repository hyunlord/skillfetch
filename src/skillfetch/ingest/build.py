"""`skillfetch ingest --sources`: build an index (index-format.md §1–§3).

snapshot -> lint -> injection scan -> extract -> dedup -> tier -> index + manifest.
The index is written to a temporary directory and swapped in when complete.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from skillfetch.ingest.extract import (
    DEFAULT_MODEL,
    EXTRACT_VERSION,
    Extractor,
    ExtractRecord,
    revalidate,
)
from skillfetch.ingest.extract_cache import ExtractCache
from skillfetch.ingest.ingest import run_extractions
from skillfetch.ingest.injection import load_rules, scan_skill
from skillfetch.ingest.licenses import skill_license
from skillfetch.ingest.lint import lint_skill
from skillfetch.ingest.provenance import openskills_upstream, parse_third_party_doc
from skillfetch.ingest.skillfile import (
    SKILL_FILE,
    content_hash,
    discover_skills,
    read_skill,
    read_text,
    skill_files,
)
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR, Snapshot, snapshot
from skillfetch.ingest.sources import Source
from skillfetch.ingest.upstream_licenses import DEFAULT_CACHE as DEFAULT_LICENSE_CACHE
from skillfetch.ingest.upstream_licenses import (
    GitHubClient,
    LicenseSource,
    license_finding,
    read_repo,
)
from skillfetch.resolve import relation as relation_mod
from skillfetch.resolve.models import Constraint, Skill
from skillfetch.resolve.relation import constraint_identity, mark_fan_out

SCHEMA_VERSION = 1
KEYWORD_JACCARD = 0.8
_TRUST_RANK = {"verified": 0, "known": 1, "unknown": 2}
Status = Literal["ok", "lint_failed", "scan_failed", "extract_failed", "too_large", "not_extracted"]


class SkillRecord(BaseModel):
    """One line of skills.jsonl / rejected.jsonl (index-format.md §3)."""

    id: str
    canonical_id: str
    name: str
    title: str
    description: str
    summary: str = ""
    source_id: str
    publisher: str
    publisher_trust: str
    commit: str
    path: str  # skill folder, relative to the snapshot root
    source_url: str
    # every file of the skill folder (SKILL.md included) -> sha256 of its raw bytes, and the
    # base URL they are fetched from at runtime: <fetch_base>/<relpath> (index-format §1.8)
    files: dict[str, str] = {}
    fetch_base: str | None = None
    content_hash: str
    tier: Literal["A", "B", "C"] | None = None
    status: Status
    tags: dict[str, list[str]] = {}
    keywords: list[str] = []
    synthetic_queries: list[str] = []
    consumes: list[str] = []
    produces: list[str] = []
    requires_tools: list[str] = []
    has_scripts: bool = False
    scripts: list[str] = []
    token_estimate: int
    lint: dict = {}
    scan: dict = {}
    extract_version: int = EXTRACT_VERSION
    constraint_count: int = 0
    license: str
    redistributable: bool
    license_origin: str
    # explicit (skill folder or upstream states a license) / upstream_no_license (upstream
    # found, states none) / upstream_unknown (no upstream, or not read): §1.8
    license_source: LicenseSource = "upstream_unknown"
    upstream: dict | None = None
    adjusted: list[str] = []
    dropped: list[str] = []
    extract_error: str | None = None
    # why a skill that passed lint and scan has no constraints: "too_large" keeps its tier
    not_extracted_reason: (
        Literal["too_large", "no cache entry", "api_error", "pending_answer"] | None
    ) = None


@dataclass
class Built:
    record: SkillRecord
    skill_dir: Path
    snap: Snapshot
    constraints: list[Constraint] = field(default_factory=list)
    extraction: ExtractRecord | None = None
    fresh: bool = False  # extracted by an API call in this run


@dataclass
class BuildResult:
    out_dir: Path
    manifest: dict
    skills: list[Built]
    groups: dict[str, list[str]]
    model: str

    @property
    def api_cost_usd(self) -> float:
        seen, total = set(), 0.0
        for b in self.skills:
            if b.fresh and b.extraction and b.record.content_hash not in seen:
                seen.add(b.record.content_hash)
                total += b.extraction.cost_usd or 0.0
        return total

    def cached_cost(self) -> tuple[float, int, int]:
        """(cost, extractions, of which estimated) of the extractions reused from the cache:
        what earlier runs paid for them, including runs that were interrupted and never
        printed a total. Provider-reported where the record has it, else the mean of the
        reported ones."""
        seen, known, unknown = set(), [], 0
        for b in self.skills:
            e = b.extraction
            if b.fresh or e is None or not e.attempts or b.record.content_hash in seen:
                continue
            seen.add(b.record.content_hash)
            if e.cost_usd is None:
                unknown += 1
            else:
                known.append(e.cost_usd)
        mean = sum(known) / len(known) if known else 0.0
        return sum(known) + unknown * mean, len(seen), unknown


# --- sampling and records ---------------------------------------------------------------------


def sample_dirs(dirs: list[Path], size: int | None, seed: int) -> list[Path]:
    """`size` skill folders chosen with a seeded RNG from the path-sorted population;
    the result is path-sorted. None or a size >= the population returns all of them."""
    population = sorted(dirs)
    if size is None or size >= len(population):
        return population
    return sorted(random.Random(seed).sample(population, size))


def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-") or "skill"


def _source_url(snap: Snapshot, rel: str) -> str:
    url = snap.source.url.removesuffix(".git").rstrip("/")
    if url.startswith("https://github.com/"):
        return f"{url}/blob/{snap.commit}/{rel}/{SKILL_FILE}"
    return f"{url}/{rel}/{SKILL_FILE}"


def _fetch_base(snap: Snapshot, skill_dir: Path, rel: str) -> str:
    """Where load_skills fetches the files: raw GitHub at the pinned commit, else the
    local snapshot (dir sources, other git hosts)."""
    url = snap.source.url.removesuffix(".git").rstrip("/")
    if url.startswith("https://github.com/"):
        repo = url.removeprefix("https://github.com/")
        return f"https://raw.githubusercontent.com/{repo}/{snap.commit}/{rel}"
    return skill_dir.resolve().as_uri()


def file_manifest(skill_dir: Path) -> dict[str, str]:
    paths = [skill_dir / SKILL_FILE, *skill_files(skill_dir)]
    return {
        p.relative_to(skill_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }


def _record(snap: Snapshot, skill_dir: Path) -> Built:
    source = snap.source
    rel = skill_dir.relative_to(snap.path).as_posix()
    lint = lint_skill(skill_dir)
    scan = scan_skill(skill_dir)
    fm = read_skill(skill_dir).frontmatter if lint.ok else None
    fm = fm or {}
    name = fm.get("name") if isinstance(fm.get("name"), str) else skill_dir.name
    digest = content_hash(skill_dir)
    status: Status = "lint_failed" if not lint.ok else "scan_failed" if not scan.ok else "ok"
    lic = skill_license(skill_dir, fm, source.license)
    up = openskills_upstream(skill_dir)
    text = read_text(skill_dir / SKILL_FILE)
    sid = f"{source.id}/{_safe(name)}@{digest[:12]}"
    record = SkillRecord(
        id=sid,
        canonical_id=sid,
        name=name,
        title=str(fm.get("title") or name),
        description=str(fm.get("description") or ""),
        source_id=source.id,
        publisher=source.publisher,
        publisher_trust=source.publisher_trust,
        commit=snap.commit,
        path=rel,
        source_url=_source_url(snap, rel),
        files=file_manifest(skill_dir),
        fetch_base=_fetch_base(snap, skill_dir, rel),
        content_hash=digest,
        status=status,
        has_scripts=scan.has_scripts,
        scripts=scan.scripts,
        token_estimate=len(text) // 4,
        lint=lint.model_dump(),
        scan=scan.model_dump(),
        license=lic.license,
        redistributable=lic.redistributable,
        license_origin=lic.origin,
        upstream=up.__dict__ if up else None,
    )
    return Built(record, skill_dir, snap)


def _apply_upstream_licenses(
    skills: list[Built], github: GitHubClient | None, cache_dir: Path
) -> None:
    """§1.8: license_source for every record; with a GitHub client, a skill without a
    license of its own takes its upstream's (the nearest license file on its upstream path)."""
    repos = {}
    if github is not None:
        for url in sorted({b.record.upstream["repo"] for b in skills if b.record.upstream}):
            repos[url] = read_repo(github, url, cache_dir)
    for b in skills:
        r = b.record
        own = r.license_origin
        found = license_finding(r.license, own, r.upstream, repos)
        r.license_source = found.license_source
        if own == "none" and found.license_source == "explicit":
            r.license, r.license_origin = found.license, found.origin
            r.redistributable = found.redistributable


def _apply_extraction(b: Built, extraction: ExtractRecord | None) -> None:
    r = b.record
    b.extraction = extraction
    if extraction is None:
        r.status, r.not_extracted_reason = "not_extracted", "no cache entry"
        return
    if extraction.status == "too_large":
        # over the extraction cost guard: searchable and loadable, no constraints to check
        r.status, r.not_extracted_reason = "not_extracted", "too_large"
        r.extract_error = extraction.error
        return
    if extraction.status != "ok" or extraction.result is None:
        r.status = extraction.status  # extract_failed | too_large
        r.extract_error = extraction.error
        return
    res = extraction.result
    b.constraints = [
        c.model_copy(update={"id": f"{r.id}#c{i}"}) for i, c in enumerate(res.constraints, 1)
    ]
    r.summary = res.summary
    r.tags = res.tags.model_dump()
    r.keywords = res.keywords
    r.synthetic_queries = res.synthetic_queries
    r.consumes, r.produces, r.requires_tools = res.consumes, res.produces, res.requires_tools
    r.constraint_count = len(b.constraints)
    r.adjusted = extraction.adjusted
    r.dropped = [d.reason for d in extraction.dropped]


# --- dedup and tiers ---------------------------------------------------------------------------


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = {k.lower() for k in a}, {k.lower() for k in b}
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def _same_constraints(a: list[Constraint], b: list[Constraint]) -> bool:
    return bool(a) and sorted(map(repr, map(constraint_identity, a))) == sorted(
        map(repr, map(constraint_identity, b))
    )


def dedup(skills: list[Built]) -> dict[str, list[str]]:
    """Duplicate groups (§1.6) as {canonical_id: [member ids]}; sets canonical_id on
    every record. Identical content, or keyword Jaccard >= 0.8 with equal constraints.
    Canonical: verified publisher first, then the newest commit, then the smallest id."""
    parent = {b.record.id: b.record.id for b in skills}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in combinations(skills, 2):
        ra, rb = a.record, b.record
        same = ra.content_hash == rb.content_hash or (
            _jaccard(ra.keywords, rb.keywords) >= KEYWORD_JACCARD
            and _same_constraints(a.constraints, b.constraints)
        )
        if same:
            parent[find(ra.id)] = find(rb.id)

    members: dict[str, list[Built]] = {}
    for b in skills:
        members.setdefault(find(b.record.id), []).append(b)
    groups = {}
    for group in members.values():
        group.sort(key=lambda b: b.record.id)
        newest_first = sorted(group, key=lambda b: b.snap.commit_date or "", reverse=True)
        canon = min(
            group,
            key=lambda b: (
                _TRUST_RANK[b.record.publisher_trust],
                newest_first.index(b),
                b.record.id,
            ),
        )
        for b in group:
            b.record.canonical_id = canon.record.id
        if len(group) > 1:
            groups[canon.record.id] = [b.record.id for b in group]
    return groups


# Warnings that do not demote an unknown publisher's skill to tier C. Skills for web APIs are
# full of documentation URLs; in the first public build `network.bare-url` alone put 129 of
# 185 UASL skills in tier C.
TIER_NEUTRAL_WARNINGS = frozenset({"network.bare-url"})


def tier_warnings(scan: dict) -> list[dict]:
    """Scan warnings that count against an unknown publisher (§1.7)."""
    return [w for w in scan.get("warnings", []) if w["rule_id"] not in TIER_NEUTRAL_WARNINGS]


def assign_tiers(skills: list[Built]) -> None:
    """§1.7. A: verified and passed lint + scan + extract. B: passed, no scripts, not a
    duplicate of an A skill, and not an unknown publisher with scan warnings (bare URLs do not
    count). C: the rest that did not fail lint or the scan."""
    by_id = {b.record.id: b.record for b in skills}
    for b in skills:
        r = b.record
        if r.status in ("lint_failed", "scan_failed"):
            r.tier = None
        elif r.status != "ok" and r.not_extracted_reason != "too_large":
            r.tier = "C"
        elif r.publisher_trust == "verified":
            r.tier = "A"
        else:
            copy_of_a = (
                r.canonical_id != r.id and by_id[r.canonical_id].publisher_trust == "verified"
            )
            warned = r.publisher_trust == "unknown" and bool(tier_warnings(r.scan))
            r.tier = "C" if copy_of_a or r.has_scripts or warned else "B"


def _mark_fan_out(skills: list[Built]) -> None:
    """constraints.md §3 row 14: flag constraints that conflict with three or more distinct
    indexed skills; the flag is stored in constraints.jsonl for resolve_set."""
    indexed = [b for b in skills if b.record.tier and b.constraints]
    marked = mark_fan_out([Skill(id=b.record.id, constraints=b.constraints) for b in indexed])
    for b, s in zip(indexed, marked, strict=True):
        b.constraints = s.constraints


# --- writing ------------------------------------------------------------------------------------


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


PAIRS_FILE = "pairs.jsonl"


def carry_pairs(previous: Path, indexed_ids: set[str]) -> list[dict]:
    """Judge verdicts of the previous index (constraints.md §8) whose two skills are still
    indexed. Skill ids pin the content (`<name>@<hash12>`), so a verdict stays valid while
    neither skill changes."""
    path = previous / PAIRS_FILE
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if r["a"] in indexed_ids and r["b"] in indexed_ids]


def write_manifest_files(root: Path, manifest: dict) -> None:
    """Hash every file of the index into the manifest and write it."""
    manifest["files"] = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def write_pairs(root: Path, rows: list[dict]) -> Path:
    """Write an index's pairs.jsonl (sorted by pair) and refresh the manifest hashes."""
    rows = sorted(rows, key=lambda r: (r["a"], r["b"]))
    _write_jsonl(root / PAIRS_FILE, rows)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["judged_pairs"] = len(rows)
    write_manifest_files(root, manifest)
    return root / PAIRS_FILE


def _write_index(
    tmp: Path,
    result_skills: list[Built],
    groups: dict,
    manifest: dict,
    previous: Path | None = None,
) -> None:
    indexed = sorted((b for b in result_skills if b.record.tier), key=lambda b: b.record.id)
    rejected = sorted((b for b in result_skills if not b.record.tier), key=lambda b: b.record.id)
    _write_jsonl(tmp / "skills.jsonl", [b.record.model_dump(mode="json") for b in indexed])
    _write_jsonl(tmp / "rejected.jsonl", [b.record.model_dump(mode="json") for b in rejected])
    _write_jsonl(
        tmp / "constraints.jsonl",
        [
            {"skill_id": b.record.id, **c.model_dump(mode="json")}
            for b in indexed
            for c in b.constraints
        ],
    )
    (tmp / "dupgroups.json").write_text(json.dumps(groups, indent=2, sort_keys=True) + "\n")
    if previous is not None and (kept := carry_pairs(previous, {b.record.id for b in indexed})):
        _write_jsonl(tmp / PAIRS_FILE, sorted(kept, key=lambda r: (r["a"], r["b"])))
        manifest["judged_pairs"] = len(kept)
    write_manifest_files(tmp, manifest)


def build_index(
    sources: list[Source],
    *,
    out_dir: Path,
    work_dir: Path = DEFAULT_WORK_DIR,
    cache: ExtractCache,
    extractor: Extractor | None,
    model: str | None = None,
    samples: dict[str, int] | None = None,
    seed: int = 42,
    jobs: int = 4,
    github: GitHubClient | None = None,
    license_cache: Path = DEFAULT_LICENSE_CACHE,
) -> BuildResult:
    model = extractor.model if extractor else (model or DEFAULT_MODEL)
    samples = samples or {}
    skills: list[Built] = []
    source_meta = []
    for source in sources:
        snap = snapshot(source, work_dir)
        found = discover_skills(snap.skills_root) if snap.skills_root.is_dir() else []
        chosen = sample_dirs(found, samples.get(source.id), seed)
        seen_ids: set[str] = set()
        for skill_dir in chosen:
            built = _record(snap, skill_dir)
            if built.record.id in seen_ids:  # same name and content twice in one source
                continue
            seen_ids.add(built.record.id)
            skills.append(built)
        doc = snap.path / source.third_party_doc if source.third_party_doc else None
        source_meta.append(
            {
                "id": source.id,
                "kind": source.kind,
                "url": source.url,
                "ref": source.ref,
                "commit": snap.commit,
                "commit_date": snap.commit_date,
                "publisher_trust": source.publisher_trust,
                "discovered": len(found),
                "sampled": len(chosen),
                "sample_seed": seed if source.id in samples else None,
                "third_party_upstreams": parse_third_party_doc(read_text(doc))
                if doc and doc.is_file()
                else [],
            }
        )

    _apply_upstream_licenses(skills, github, license_cache)

    ok = [b for b in skills if b.record.status == "ok"]
    cached = {b.record.content_hash: cache.get(b.record.content_hash, model) for b in ok}
    for b in ok:  # failures the current validation accepts are recovered without the API
        hit = cached[b.record.content_hash]
        if hit is not None and (fixed := revalidate(hit, b.skill_dir)) is not None:
            cache.put(fixed)
            cached[b.record.content_hash] = fixed
    todo = [
        (b.skill_dir, b.record.id, b.record.content_hash)
        for b in ok
        if cached[b.record.content_hash] is None
    ]
    api_errors: dict[str, str] = {}
    fresh = (
        run_extractions(todo, cache, extractor, jobs, errors=api_errors)
        if extractor and todo
        else {}
    )
    for b in ok:
        digest = b.record.content_hash
        b.fresh = digest in fresh
        if digest in api_errors:
            # not cached: a rerun retries it; tier C until then
            reason = (
                "pending_answer" if api_errors[digest].startswith("PendingAnswer") else "api_error"
            )
            b.record.status, b.record.not_extracted_reason = "not_extracted", reason
            b.record.extract_error = api_errors[digest]
            continue
        _apply_extraction(b, fresh.get(digest) or cached[digest])

    candidates = [b for b in skills if b.record.status not in ("lint_failed", "scan_failed")]
    groups = dedup(candidates)
    assign_tiers(skills)
    _mark_fan_out(skills)

    counts = Counter(b.record.tier for b in skills if b.record.tier)
    statuses = Counter(b.record.status for b in skills)
    reasons = Counter(b.record.not_extracted_reason for b in skills)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extract_version": EXTRACT_VERSION,
        "extract_model": model,
        "scan_rules_version": load_rules().version,
        "conflict_cap": relation_mod.OBJECTLESS_CAP,
        "sources": [
            {**m, "skills": sum(1 for b in skills if b.record.source_id == m["id"])}
            for m in source_meta
        ],
        "counts": {
            **{t: counts.get(t, 0) for t in ("A", "B", "C")},
            **{s: statuses.get(s, 0) for s in ("lint_failed", "scan_failed", "extract_failed")},
            # too_large keeps its tier; "no cache entry" (a run without --with-api) is tier C
            "too_large": reasons.get("too_large", 0),
            "not_extracted": reasons.get("no cache entry", 0),
            "api_errors": reasons.get("api_error", 0),
            "pending_answers": reasons.get("pending_answer", 0),
        },
        "licenses": dict(sorted(Counter(b.record.license for b in skills).items())),
        "license_sources": dict(sorted(Counter(b.record.license_source for b in skills).items())),
        "redistributable": sum(b.record.redistributable for b in skills if b.record.tier),
        "signature": None,
    }

    tmp = out_dir.with_name(out_dir.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    _write_index(tmp, skills, groups, manifest, previous=out_dir if out_dir.is_dir() else None)
    old = out_dir.with_name(out_dir.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if out_dir.exists():
        out_dir.rename(old)
    tmp.rename(out_dir)
    shutil.rmtree(old, ignore_errors=True)
    return BuildResult(out_dir, manifest, skills, groups, model)


def render_summary(result: BuildResult) -> str:
    m = result.manifest
    c = m["counts"]
    extracted = {b.record.content_hash for b in result.skills if b.fresh}
    cached = {
        b.record.content_hash for b in result.skills if b.extraction is not None and not b.fresh
    }
    lines = [f"index: {result.out_dir}"]
    for s in m["sources"]:
        sample = f" (seed {s['sample_seed']})" if s["sample_seed"] is not None else ""
        lines.append(
            f"  {s['id']} @ {s['commit'][:12]}: {s['discovered']} discovered, "
            f"{s['sampled']} sampled{sample}"
        )
    lines.append(f"tiers: A={c['A']} B={c['B']} C={c['C']}")
    lines.append(
        "not indexed: "
        + ", ".join(f"{k}={c[k]}" for k in ("lint_failed", "scan_failed"))
        + f" · tier C: extract_failed={c['extract_failed']}, "
        f"not in cache={c['not_extracted']}, API errors={c.get('api_errors', 0)} · too large "
        f"to extract (tier kept): {c['too_large']}"
    )
    lines.append(
        f"redistributable: {m['redistributable']} of {c['A'] + c['B'] + c['C']} indexed · "
        f"duplicate groups: {len(result.groups)}"
    )
    lines.append(
        f"API cost this run: ${result.api_cost_usd:.4f} ({len(extracted)} extracted, "
        f"{len(cached)} from cache)"
    )
    return "\n".join(lines)
