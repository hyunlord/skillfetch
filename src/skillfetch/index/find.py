"""`skillfetch find "<what you want>"` and the MCP tool find_skills: the index's top matches
for a request the user made, each with its summary, tier, size, license and an install advice
read from the index record (index-format.md §5.2). No model, no network.

This is search on request, separate from per-task routing: nothing is loaded. The advice is
from the record the index stored at build time, with each stored scan warning graded by the
current rules; checks added since the build (remote instructions, for one) need the files, so
every result carries the pinned GitHub URL to pass to `scan` / `scan_skill` before installing.
"""

from __future__ import annotations

import re

from skillfetch.index.loader import Index
from skillfetch.index.search import Searcher
from skillfetch.ingest.injection import RuleSet, load_rules
from skillfetch.ingest.skill_checks import MAX_FILES, MAX_SKILL_MD_TOKENS

DEFAULT_FIND_K = 10
MAX_FIND_K = 50
MAX_WANT_CHARS = 2000
ADVICE_NOTE = (
    "advice from the index record (lint, scan, size, scripts at build time, scan warnings "
    "graded by the current rules); run scan_skill on scan_url for the full check before "
    "installing"
)
_BLOB = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/blob/")


def scan_url(record: dict) -> str | None:
    """https://github.com/<owner>/<repo>/tree/<commit>/<path>: the skill at its pinned commit."""
    m = _BLOB.match(record.get("source_url") or "")
    if m is None:
        return None
    path = record.get("path") or ""
    return f"https://github.com/{m[1]}/{m[2]}/tree/{record['commit']}" + (
        f"/{path}" if path else ""
    )


def _effect(rules: RuleSet, rule_id: str, stored: str) -> str:
    for rule in rules.rules:
        if rule.id == rule_id:
            return rule.effect or rules.effects.get(rule.family, stored)
    return stored  # a rule the current set no longer has: keep what the build recorded


def record_advice(record: dict, rules: RuleSet | None = None) -> tuple[str, list[str]]:
    """(recommended | caution | not_recommended, reasons) from an index record, by the
    rule of §5.1 (license not included)."""
    rules = rules or load_rules()
    scan = record.get("scan") or {}
    lint = record.get("lint") or {}
    if lint.get("errors"):
        return "not_recommended", ["fails lint"]
    if scan.get("failures"):
        return "not_recommended", ["fails the injection scan"]
    reasons = []
    warned = sorted(
        {
            h["rule_id"]
            for h in scan.get("warnings") or []
            if _effect(rules, h["rule_id"], "warn") != "info"
        }
    )
    if warned:
        reasons.append("injection-scan warnings: " + ", ".join(warned))
    tokens, files = record.get("token_estimate", 0), len(record.get("files") or {})
    if tokens > MAX_SKILL_MD_TOKENS or files > MAX_FILES:
        reasons.append(f"over a size limit (~{tokens:,} tokens, {files} files)")
    if record.get("has_scripts"):
        reasons.append("bundles scripts")
    return ("caution", reasons) if reasons else ("recommended", [])


def find_skills(index: Index, searcher: Searcher, want: str, k: int = DEFAULT_FIND_K) -> dict:
    if not isinstance(want, str) or not want.strip():
        return {"error": "invalid request: describe the skill you want in a sentence"}
    rules = load_rules()
    hits = searcher.search(want.strip()[:MAX_WANT_CHARS], k=max(1, min(k, MAX_FIND_K)))
    results = []
    for hit in hits:
        record = index.records[hit["id"]]
        advice, reasons = record_advice(record, rules)
        results.append(
            {
                **hit,
                "files": len(record.get("files") or {}),
                "has_scripts": bool(record.get("has_scripts")),
                "license": record.get("license", "unknown"),
                # the repository's root license file; whether it covers the skill depends on
                # the repository (an aggregator's does not): scan_skill decides (§5.1)
                "repo_license": record.get("repo_license"),
                "advice": advice,
                "advice_reasons": reasons,
                "scan_url": scan_url(record),
            }
        )
    return {"results": results, "advice_note": ADVICE_NOTE}


ADVICE_TEXT = {
    "recommended": "RECOMMENDED",
    "caution": "CAUTION",
    "not_recommended": "NOT RECOMMENDED",
}


def render_find(want: str, found: dict) -> str:
    if "error" in found:
        return found["error"] + "\n"
    if not found["results"]:
        return f'No indexed skill matches "{want}".\n'
    lines = [f'Skills for "{want}" (top {len(found["results"])} in the index):', ""]
    for i, r in enumerate(found["results"], 1):
        advice = ADVICE_TEXT[r["advice"]] + (
            f" ({'; '.join(r['advice_reasons'])})" if r["advice_reasons"] else ""
        )
        files = f"{r['files']} file" + ("" if r["files"] == 1 else "s")
        license = r["license"]
        if license == "unknown":
            repo = r.get("repo_license")
            license = f"none in the skill (repo: {repo})" if repo not in (None, "none") else "none"
        lines.append(
            f"{i:>2}. {r['title']}  tier {r['tier']} · ~{r['token_estimate']:,} tokens · "
            f"{files} · license {license}"
        )
        lines.append(f"    {r['summary']}")
        lines.append(f"    advice: {advice}")
        if r["scan_url"]:
            lines.append(f"    before installing: skillfetch scan {r['scan_url']}")
        lines.append("")
    lines.append(f"Note: {found['advice_note']}.")
    return "\n".join(lines) + "\n"
