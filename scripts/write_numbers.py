"""Write docs/writeup/numbers.md: every number for the write-up, with where it comes from.

Reads the built indexes and reports under data/ (gitignored) and the caches under
~/.skillfetch/. Run from the repo root:  uv run python scripts/write_numbers.py
Nothing here calls a model.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from skillfetch.ingest.build_report import LICENSE_CLASSES, LICENSE_SOURCES, license_class
from skillfetch.ingest.extract import ExtractRecord

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HOME = Path.home() / ".skillfetch"
OUT = ROOT / "docs" / "writeup" / "numbers.md"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def review_counts(path: Path) -> dict[str, int]:
    """The kind/pairs table at the top of a review.md."""
    counts = {}
    for kind, n in re.findall(
        r"^\| (conflict|redundant|tension|needs_review) \| (\d+) \|$", path.read_text(), re.M
    ):
        counts[kind] = int(n)
    return counts


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "-"


def table(header, rows) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def corpus(out: list[str]) -> None:
    idx = DATA / "index"
    manifest = json.loads((idx / "manifest.json").read_text())
    indexed, rejected = jsonl(idx / "skills.jsonl"), jsonl(idx / "rejected.jsonl")
    allrecs = indexed + rejected
    c = manifest["counts"]
    out += [
        "## 1. Corpus (full build)",
        "",
        "Source: `data/index/manifest.json`, `skills.jsonl`, `rejected.jsonl` — built by "
        "`skillfetch ingest --sources sources.yaml --upstream-licenses` "
        f"(extraction `{manifest['extract_model']}` v{manifest['extract_version']}, "
        f"scan rules v{manifest['scan_rules_version']}, conflict cap "
        f"`{manifest.get('conflict_cap', 'all')}`).",
        "",
    ]
    out += table(
        ("source", "commit", "discovered", "records"),
        [(s["id"], s["commit"][:12], s["discovered"], s["skills"]) for s in manifest["sources"]],
    )
    out += [
        "",
        f"- Skills discovered: **{len(allrecs)}**; indexed: **{len(indexed)}**; not indexed: "
        f"{len(rejected)} (lint {c['lint_failed']}, injection scan {c['scan_failed']}).",
        f"- Tiers: A {c['A']}, B {c['B']}, C {c['C']}. Too large to extract (tier kept): "
        f"{c.get('too_large', 0)}.",
        "",
    ]
    lint = Counter(i["rule"] for r in rejected for i in r["lint"].get("errors", []))
    scan = Counter(h["rule_id"] for r in rejected for h in r["scan"].get("failures", []))
    out += ["Rejections by rule (`data/index-reports/report.md` §Not indexed):", ""]
    out += table(("rule", "hits"), [(f"`{k}`", n) for k, n in (lint + scan).most_common()])
    tier_c = [r for r in indexed if r["tier"] == "C"]
    out += [
        "",
        f"Tier C ({len(tier_c)}): scripts {sum(r['has_scripts'] for r in tier_c)}; the "
        "rest are unknown-publisher skills with non-URL scan warnings, or copies of a tier A "
        "skill (`report.md` §Why tier C).",
        "",
    ]

    out += [
        "## 2. Licenses",
        "",
        "Source: `license_source` in `skills.jsonl` + `rejected.jsonl`; upstream repos read "
        "via the GitHub git trees API, cached in `~/.skillfetch/upstream-licenses/` "
        '(index-format.md §1.8). "No license stated" and "not redistributable" are '
        "different columns: only `permissive` is redistributable.",
        "",
    ]
    cells = Counter((r["license_source"], license_class(r["license"])) for r in allrecs)
    rows = []
    for src in LICENSE_SOURCES:
        counts = [cells.get((src, cls), 0) for cls in LICENSE_CLASSES]
        rows.append((src, *counts, sum(counts), pct(sum(counts), len(allrecs))))
    out += table(("license_source", *LICENSE_CLASSES, "skills", "share"), rows)
    composio = sum(
        1
        for r in allrecs
        if r["license_source"] == "upstream_no_license"
        and "ComposioHQ/awesome-claude-skills" in ((r.get("upstream") or {}).get("repo", ""))
    )
    upstreams = Counter((r.get("upstream") or {}).get("repo") for r in allrecs if r.get("upstream"))
    out += [
        "",
        f"- Of the `upstream_no_license` skills, **{composio}** come from "
        "`ComposioHQ/awesome-claude-skills`, which has no LICENSE file.",
        f"- Skills naming an upstream (`.openskills.json`): {sum(upstreams.values())}, in "
        f"{len(upstreams)} repos.",
        f"- Redistributable (permissive) among indexed skills: "
        f"{sum(r['redistributable'] for r in indexed)} of {len(indexed)}.",
        "",
    ]


def constraints_and_pairs(out: list[str]) -> None:
    idx = DATA / "index"
    cons = jsonl(idx / "constraints.jsonl")
    indexed = jsonl(idx / "skills.jsonl")
    extracted = [r for r in indexed if r["status"] == "ok"]
    dropped = Counter(d.split(":")[0] for r in indexed for d in r.get("dropped", []))
    out += [
        "## 3. Constraints and pairs",
        "",
        "Source: `data/index/constraints.jsonl`, `data/index-reports/review.md` (every "
        "non-independent pair among canonical, extracted skills).",
        "",
        f"- Constraints: **{len(cons)}** from {len(extracted)} skills "
        f"({len(cons) / len(extracted):.1f} per skill). Dropped at extraction: "
        + ", ".join(f"{k} {n}" for k, n in dropped.most_common())
        + ".",
        f"- Constraints flagged as fan-out hubs: {sum(c.get('fan_out', False) for c in cons)}.",
        "",
    ]
    history = [
        ("first build: anthropics 19 + UASL 200 (seed 42), extraction v4", "index-v0-reports"),
        ("UASL seed 43, extraction v5, every object-less pair capped", "index-v1-reports"),
        ("UASL seed 43, extraction v6, only narrowed object-less pairs capped", "index-v2-reports"),
        ("UASL seed 43, v6 + caps (default cap)", "index-v4-all-reports"),
        ("UASL seed 43, v6 + caps (--conflict-cap vocabulary)", "index-v4-vocabulary-reports"),
        ("full build: anthropics 19 + UASL 1812", "index-reports"),
    ]
    rows = []
    for label, d in history:
        path = DATA / d / "review.md"
        if path.is_file():
            k = review_counts(path)
            rows.append(
                (
                    label,
                    f"`data/{d}/review.md`",
                    k.get("conflict", 0),
                    k.get("redundant", 0),
                    k.get("tension", 0),
                    k.get("needs_review", 0),
                )
            )
    out += table(("build", "source", "conflict", "redundant", "tension", "needs_review"), rows)
    out += [
        "",
        "- Every `conflict` was read by hand. First build: 24 conflicts, all false. Full "
        'build with extraction v6 and the caps: 2 conflicts, both false (README, "Cases we '
        'get wrong"). Before the fan-out fix the full build had 18, all false.',
        "",
    ]


def calibration(out: list[str]) -> None:
    out += [
        "## 4. Calibration and holdout",
        "",
        "Source: `skillfetch ingest tests/fixtures --calibrate [--conflict-cap MODE]` and "
        "`skillfetch ingest --sources sources.yaml --holdout "
        "tests/fixtures/holdout/public-v0.yaml` "
        "(both from the extract cache, no API).",
        "",
        "- Fixtures: 41 hand-written skills, 55 labelled constraints, 820 pairs, 34 "
        "labelled non-independent.",
        "- Default cap: 11 of 11 flagged conflicts true (8 real blanket-rule conflicts are "
        "reported as needs_review by design); `--conflict-cap vocabulary`: 19 of 19. "
        "Informative-pair accuracy 0.912 (31/34), extraction v6.",
        "- Holdout (26 public skills, 325 pairs, hand labels): 0 conflicts flagged in both "
        "cap modes; v4 had flagged 24, all false.",
    ]
    labels = sorted((ROOT / "tests" / "fixtures" / "skills").glob("*/constraints.json"))
    cap = [f for f in labels if '"note"' in f.read_text()]
    v6 = HOME / "extract-cache" / "v6"
    v6_fixtures = sum(
        1 for f in v6.rglob("*.json") if "/" not in json.loads(f.read_text()).get("skill_id", "/")
    )
    out += [
        f"- Fixture directory today (`tests/fixtures/skills`): {len(labels)} skills, "
        f"{len(labels) - len(cap)} hand-written and {len(cap)} cap fixtures (constraints kept as "
        "the extractor read real public lines, each with a `note`; `tests/fixtures/README.md`). "
        f"The calibration figures above are from the {v6_fixtures}-skill set extraction v6 ran "
        "on (fixture entries in the v6 extract cache).",
        "",
    ]


def judge(out: list[str]) -> None:
    rows = jsonl(DATA / "index-reports" / "judgments.jsonl")
    verdicts = Counter(r["verdict"] or "error" for r in rows)
    amb = [r for r in rows if r["ambiguous_together"]]
    both = [r for r in amb if r["verdict"] == "conflict"]
    out += [
        "## 5. LLM judge over the open pairs",
        "",
        "Source: `data/index-reports/judgments.jsonl`, `judge.md`; stored in the index as "
        "`data/index/pairs.jsonl`. Judge `openrouter/anthropic/claude-sonnet-5.5` (not the "
        "extractor), original lines only. Calibration `skillfetch judge --calibrate "
        "tests/fixtures`: 0.824 (28/34); it called 6 of 7 hand-labelled carve-outs "
        "`conflict`, so its conflict count leans high.",
        "",
        f"- Pairs judged: {len(rows)} (needs_review "
        f"{sum(r['rules'] == 'needs_review' for r in rows)}, "
        f"tension {sum(r['rules'] == 'tension' for r in rows)}).",
        "",
    ]
    out += table(
        ("verdict", "pairs", "share"),
        [(v, n, pct(n, len(rows))) for v, n in verdicts.most_common()],
    )
    out += ["", f"- `ambiguous_together`: {len(amb)}; also `conflict`: {len(both)}.", ""]
    cells = defaultdict(Counter)
    for r in rows:
        cells[r["row"]][r["verdict"] or "error"] += 1
    cols = ("conflict", "carve_out", "situational", "independent", "unclear", "error")
    out += ["Rules' §3 row × verdict:", ""]
    out += table(
        ("§3 row", *cols, "total"),
        [(row, *(c.get(k, 0) for k in cols), sum(c.values())) for row, c in sorted(cells.items())],
    )
    out.append("")


def obedience(out: list[str]) -> None:
    trials_path = DATA / "obedience" / "trials.jsonl"
    out += ["## 6. Obedience split test", ""]
    if not trials_path.is_file():
        out += ["Not run yet.", ""]
        return
    trials = jsonl(trials_path)
    tasks = json.loads((DATA / "obedience" / "tasks.json").read_text())
    by_pair = defaultdict(list)
    for t in trials:
        by_pair[t["pair"]].append(t)
    mixed = sum(1 for ts in by_pair.values() if {"a", "b"} <= {t["followed"] for t in ts})
    unanimous = sum(1 for ts in by_pair.values() if len({t["followed"] for t in ts}) == 1)
    one_side = sum(1 for ts in by_pair.values() if {t["followed"] for t in ts} in ({"a"}, {"b"}))
    total = Counter(t["followed"] for t in trials)
    first = Counter(
        "first" if t["followed"] == t["order"][0] else "second"
        for t in trials
        if t["followed"] in ("a", "b")
    )
    sel = json.loads((DATA / "obedience" / "selection.json").read_text())
    out += [
        "Source: `data/obedience/` (`selection.json`, `tasks.json`, `trials.jsonl`, "
        "`results.md`); `skillfetch obedience --index data/index --run "
        "data/obedience/tasks.json`. Pairs: judge `conflict` ∧ `ambiguous_together`, "
        "no config-file or install tasks, at most two pairs per skill. Each run is an "
        "isolated Claude Code session (`claude -p --safe-mode`, sonnet, no tools) with both "
        "skill bodies in its system prompt and no precedence rule; A first on runs 1, 3, 5, "
        "B first on 2, 4. Outputs classified by Claude Code (opus-5.5) against the task's "
        "'follows A' / 'follows B' descriptions. Two earlier batches were discarded: "
        "without a no-tools note 51 of 90 runs wrote a tool call as text and stopped; a first "
        'note ("do the task in this one reply") discouraged stopping to ask. Two tasks that '
        "needed tools (run CodeQL, deploy to Vercel) ask for the commands instead.",
        "",
        f"- Candidates {len(sel['chosen']) + len(sel['excluded']) + len(sel['capped'])}; "
        f"excluded (config / install) {len(sel['excluded'])}; over the 2-per-skill cap "
        f"{len(sel['capped'])}; tested **{len(tasks)}** pairs × "
        f"{len(trials) // max(1, len(tasks))} runs = {len(trials)} runs.",
        f"- Followed: A {total.get('a', 0)}, B {total.get('b', 0)}, both {total.get('both', 0)}, "
        f"neither {total.get('neither', 0)}"
        + (f", unclassified {total.get(None, 0)}" if total.get(None) else "")
        + ".",
        f"- **Non-deterministic pairs** (A in some runs, B in others): **{mixed} of "
        f"{len(by_pair)}**. Same outcome in all runs: {unanimous} (always the same one "
        f"skill: {one_side}).",
        f"- When exactly one skill was followed: the one loaded first {first['first']}, "
        f"second {first['second']}.",
        "",
    ]
    rows = Counter(t["row"] for t in tasks)
    out += ["Pairs by §3 row: " + ", ".join(f"{k} {n}" for k, n in rows.most_common()), ""]
    table = (DATA / "obedience" / "results.md").read_text().split("## Per pair\n", 1)[1]
    out += ["Per pair (`results.md`):", "", table.strip(), ""]
    out += [
        "Caveats:",
        "",
        '- The harness wording moves the result: under the discarded "do it in this one '
        'reply" note the code-review pair went B in 5 of 5 runs; under the neutral note it '
        'is mixed. Pairs whose rule is "stop and ask" are the most sensitive.',
        "- The Tic-Tac-Toe task (artifacts-builder ⟷ develop-web-game) needs a bundling "
        "step neither skill can do without tools; all its runs are `neither`.",
        "- Sessions still carry Claude Code's environment block (working directory, "
        "platform); no project files or instructions.",
        "- One classifier (opus-5.5, in this Claude Code session) labelled every run; no "
        "second rater.",
        "",
    ]


def costs(out: list[str]) -> None:
    out += [
        "## 7. Cost of this analysis",
        "",
        "Source: provider-reported cost (`usage.cost` from OpenRouter) in every cache "
        "record under `~/.skillfetch/extract-cache/`, `judge-cache/` and "
        "`obedience-cache/tasks/`; requests that failed before a response are not "
        "included (none were billed as far as the provider reports show).",
        "",
    ]
    groups: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
    for f in (HOME / "extract-cache").rglob("*.json"):
        version, *model = f.relative_to(HOME / "extract-cache").parts[:-1]
        rec = ExtractRecord.model_validate_json(f.read_text())
        key = f"extraction {version} · {'/'.join(model)}"
        groups[key][0] += 1
        groups[key][1] += rec.cost_usd or 0.0
    for f in (HOME / "judge-cache").rglob("*.json"):
        key = "judge · " + "/".join(f.relative_to(HOME / "judge-cache").parts[1:-1])
        d = json.loads(f.read_text())
        groups[key][0] += 1
        groups[key][1] += d.get("cost_usd") or 0.0
    for f in (HOME / "obedience-cache" / "tasks").rglob("*.json"):
        key = "obedience tasks · " + "/".join(
            f.relative_to(HOME / "obedience-cache" / "tasks").parts[:-1]
        )
        groups[key][0] += 1
        groups[key][1] += json.loads(f.read_text()).get("_cost_usd") or 0.0
    api = {k: v for k, v in groups.items() if "claude-code" not in k}
    v6_ids = [
        json.loads(f.read_text()).get("skill_id", "")
        for f in (HOME / "extract-cache" / "v6").rglob("*.json")
    ]
    v6_public = sum(1 for s in v6_ids if "/" in s)
    total = sum(v[1] for v in api.values())
    out += table(
        ("stage · model", "requests", "USD"),
        [(k, n, f"{c:.4f}") for k, (n, c) in sorted(api.items())],
    )
    out += [
        "",
        f"Extraction v6 requests: {len(v6_ids)} = {v6_public} public skills + "
        f"{len(v6_ids) - v6_public} fixture skills.",
        "",
        f"**Total external API spend: ${total:.2f}** (OpenRouter). Since the "
        '"no external API" rule, model work runs inside Claude Code and is not in this '
        "total.",
        "",
    ]
    runs = list((HOME / "obedience-cache" / "runs").rglob("*.json"))
    discarded = list((HOME / "obedience-archive").rglob("runs/**/*.json"))

    def session_cost(files):
        return sum(json.loads(f.read_text()).get("cost_usd") or 0.0 for f in files)

    plain = len(jsonl(DATA / "obedience" / "trials.jsonl"))
    header_path = DATA / "obedience" / "trials-precedence.jsonl"
    header = len(jsonl(header_path)) if header_path.is_file() else 0
    resolved_path = DATA / "obedience" / "trials-resolved.jsonl"
    named = len(jsonl(resolved_path)) if resolved_path.is_file() else 0
    strip_path = DATA / "obedience" / "trials-strip.jsonl"
    stripped = len(jsonl(strip_path)) if strip_path.is_file() else 0
    out += [
        "Claude Code sessions (API-price equivalent reported by Claude Code, billed to the "
        "Claude Code plan, not OpenRouter): obedience agent runs "
        f"{len(runs)} ({plain} without a precedence header, §6; {header} with one, §8; "
        f"{named} with a resolved-conflict block, §9; {stripped} with stripped lines, §10), "
        f"${session_cost(runs):.2f}; {len(discarded)} runs of two earlier "
        "batches discarded for harness problems (no note that the session has no tools; then "
        f"a note that discouraged asking), ${session_cost(discarded):.2f}; "
        "the end-to-end MCP transcript session $0.82.",
        "",
    ]
    transcript = 0.82
    repo = session_cost(runs) + session_cost(discarded) + transcript
    e2e_path = DATA / "e2e" / "router-e2e.json"
    if not e2e_path.is_file():
        return
    e2e_data = json.loads(e2e_path.read_text())
    e2e = e2e_data["session_costs"]
    prep = e2e_data.get("stage4_prep") or {"calls": 0, "cost_usd": 0.0}
    prep3 = e2e_data.get("stage3_prep") or {}
    prep5 = e2e_data.get("stage5_prep") or {}
    # stage 5 calls with no cache record (e2e/stage5/report-stage5.md, report-check.md): the
    # first oracle relabel pass of the 7 rewritten tasks (discarded; the second pass overwrote its
    # cache files) and the 1-turn, no-tool call that checked V2's CLAUDE.md is loaded
    prep5_uncached = {"first relabel pass (discarded)": 1.24, "V2 CLAUDE.md check call": 0.05}
    prep5_cost = sum(v["cost_usd"] for v in prep5.values()) + sum(prep5_uncached.values())
    prep3_cost = sum(v["cost_usd"] for v in prep3.values())
    prep3_calls = sum(v["calls"] for v in prep3.values())
    gen_label = [prep3[k] for k in ("generation", "labelling") if k in prep3]
    names = {
        "stage0": "stage 0",
        "stage0.5": "stage 0.5",
        "stage1": "stage 1",
        "stage1b": "stage 1b",
        "c2": "C2",
        "stage2": "stage 2",
        "stage3_run1": "stage 3 run 1 (empty repos)",
        "stage3_run2": "stage 3 run 2 (stub repos)",
        "stage4_pilot": "stage 4 pilot",
        "stage4": "stage 4",
        "stage5": "stage 5",
        "stage5_check": "stage 5 check sessions",
        "stage5_trivial": "stage 5 trivial-task check",
        "stage5_discarded": "stage 5 discarded (old t026 text)",
        "smoke": "smoke tests",
    }
    e2e_cost = sum(v["cost_usd"] for v in e2e.values())
    counted = sum(
        v["sessions"] for k, v in e2e.items() if k != "smoke" and not k.endswith("_discarded")
    )
    out += [
        "End-to-end sessions (§11, §14, §15 and the write-up's sections 5-6; `session_costs` in "
        "`data/e2e/router-e2e.json`, Claude Code's `total_cost_usd` per session, same "
        "billing): "
        + "; ".join(f"{names[k]} {v['sessions']}, ${v['cost_usd']:.2f}" for k, v in e2e.items())
        + ".",
        "",
        "Stage 3 batch calls (isolated `claude -p`, no tools; `stage3_prep`, the `cost_usd` of "
        "every cached call in e2e/stage3/gen/raw): generation and labelling "
        f"{sum(v['calls'] for v in gen_label)} calls, ${sum(v['cost_usd'] for v in gen_label):.2f}"
        + "".join(
            f"; {k} {v['calls']} call{'s' if v['calls'] != 1 else ''}, ${v['cost_usd']:.2f}"
            for k, v in prep3.items()
            if k not in ("generation", "labelling")
        )
        + f"; total {prep3_calls} calls, ${prep3_cost:.2f}.",
        "",
        f"Stage 4 batch calls (isolated `claude -p`, no tools: task rewrite, oracle 2a / 2b / "
        f"3-0, queries, offline selection, 4-0 grading; `stage4_prep`): {prep['calls']} calls, "
        f"${prep['cost_usd']:.2f}.",
        "",
        "Stage 5 batch calls (isolated `claude -p`, no tools; `stage5_prep`, cached in "
        "e2e/stage4/gen/raw): "
        + "; ".join(f"{k} {v['calls']} calls, ${v['cost_usd']:.2f}" for k, v in prep5.items())
        + "; not in the cache, from the stage 5 report: "
        + "; ".join(f"{k} ${c:.2f}" for k, c in prep5_uncached.items())
        + f"; total ${prep5_cost:.2f}.",
        "",
        "Not recorded: in these stages' batch calls only successful answers are cached, so the "
        "cost of an attempt that returned an error and was retried, if any, is not in these "
        "sums.",
        "",
        f"**Claude Code plan, API-price equivalent, not money spent, total: "
        f"${repo + e2e_cost + prep3_cost + prep['cost_usd'] + prep5_cost:.2f}**: "
        f"sessions run from this repo ${repo:.2f} ({len(runs)} obedience runs, {len(discarded)} "
        f"discarded, the transcript session), end-to-end sessions ${e2e_cost:.2f}, stage 3 "
        f"batch calls ${prep3_cost:.2f}, stage 4 batch calls ${prep['cost_usd']:.2f}, stage 5 "
        f"batch calls ${prep5_cost:.2f}. "
        "The agent sessions the "
        f"write-up counts: {len(runs) + counted:,} ({len(runs)} obedience runs and {counted} "
        "end-to-end; discarded runs and smoke tests not counted). The interactive Claude Code "
        "sessions that wrote the code and classified the outputs are not included.",
        "",
    ]
    after = DATA / "e2e" / "after-post-costs.md"
    if after.is_file():
        out += [after.read_text().strip(), ""]


def runtime(out: list[str]) -> None:
    """§7, runtime latency: scripts/bench_runtime.py before and after the resolve_set
    bucketing (data/runtime/bench-{before,after}.json)."""
    paths = [DATA / "runtime" / f"bench-{tag}.json" for tag in ("before", "after")]
    if not all(p.is_file() for p in paths):
        return
    before, after = (json.loads(p.read_text()) for p in paths)

    def fmt(seconds: float) -> str:
        return f"{seconds * 1000:.1f} ms" if seconds < 1 else f"{seconds:.2f} s"

    def span(xs: list[float]) -> str:
        lo, mid, hi = min(xs), statistics.median(xs), max(xs)
        return f"{fmt(mid)} ({fmt(lo)}–{fmt(hi)})"

    rows = [
        (
            "server start (fresh process: import, load index, build server)",
            fmt(before["server_start_s"]),
            fmt(after["server_start_s"]),
        ),
        (
            "search_skills, k=50",
            span([x / 1000 for x in before["search_ms"]]),
            span([x / 1000 for x in after["search_ms"]]),
        ),
    ]
    for size in before["resolve_s"]:
        how = (
            "Session"
            if int(size) <= 20
            else "before: Session; after: the resolver, since the session refuses >20"
        )
        rows.append(
            (
                f"resolve_set, {size} skills ({how})",
                span(before["resolve_s"][size]),
                span(after["resolve_s"][size]),
            )
        )
    rows.append(
        (
            "peak RSS of the benchmark process",
            f"{before['max_rss_bytes'] / 1e6:.0f} MB",
            f"{after['max_rss_bytes'] / 1e6:.0f} MB",
        )
    )
    out += [
        "### Runtime latency",
        "",
        "Source: `uv run python scripts/bench_runtime.py` on index-2026-10-22 (Apple M4 Max), "
        f"before ({before['commit']}) and after constraint pairs are bucketed by subject and "
        "`normalize_term` is cached in `resolve/relation.py`; `data/runtime/`. resolve_set sets: "
        "the top N search_skills results for each of 5 task sentences; median (min–max) over "
        "the 5. The fixture scan (`skillfetch scan tests/fixtures/skills --json`, with and "
        "without the index) and the resolutions of 28 real-index sets are byte-identical "
        "before and after.",
        "",
    ]
    out += table(("measure", "before", "after"), rows)
    out += [""]


def precedence(out: list[str]) -> None:
    path = DATA / "obedience" / "results-precedence.md"
    out += ["## 8. Precedence header (experiment A)", ""]
    if not path.is_file():
        out += ["Not run yet.", ""]
        return
    body = path.read_text().split("\n", 2)[2].strip()  # drop the file's own title
    body = body.replace("\n## Per pair", "\n### Per pair")
    out += [
        "Source: `data/obedience/trials-precedence.jsonl`, `results-precedence.md`; "
        "`skillfetch obedience --index data/index --run data/obedience/tasks.json "
        "--precedence ab --precedence ba`. The 26 pairs and tasks of §6, the same harness "
        "(isolated `claude -p --safe-mode` sessions, sonnet, no tools, the neutral no-tools "
        "note) and the same classification (Claude Code, opus-5.5, against each task's "
        "'follows A' / 'follows B'). `ab`: load_skills' precedence header at the top of the "
        "system prompt, then A, then B, in all 5 runs; `ba`: the header, then B, then A. The "
        "no-header winner of a pair is the skill followed in more of its §6 runs (a tie when "
        "equal). A run is controlled when the skill it followed is the one the header ranks "
        "first.",
        "",
        body,
        "",
    ]


def resolved(out: list[str]) -> None:
    path = DATA / "obedience" / "results-resolved.md"
    out += ["## 9. Resolved-conflict block (experiment A2)", ""]
    if not path.is_file():
        out += ["Not run yet.", ""]
        return
    body = path.read_text().split("\n", 2)[2].strip()  # drop the file's own title
    body = body.replace("\n## ", "\n### ")
    out += [
        "Source: `data/obedience/trials-resolved.jsonl`, `results-resolved.md`; "
        "`skillfetch obedience --index data/index --run data/obedience/tasks.json "
        "--precedence resolved-a --precedence resolved-b`. The 26 pairs and tasks of §6, the "
        "harness and classification of §6 and §8. Each run's system prompt starts with a "
        '"Resolved rule conflicts" block: the two skill names, the subject, the winner '
        "(`resolved-a`: A, `resolved-b`: B) and both sides' evidence lines (the lines in "
        "`data/index-reports/judgments.jsonl` for the pair, else the first constraints with a "
        "shared subject in `constraints.jsonl`); the skill bodies follow in the order A, B in "
        "every run, with no precedence header. A run is controlled when the skill it followed "
        "is the named winner.",
        "",
        body,
        "",
    ]


def _winner(rows: list[dict]) -> str | None:
    dist = Counter(r["followed"] for r in rows)
    if dist["a"] == dist["b"]:
        return None
    return "a" if dist["a"] > dist["b"] else "b"


def three_conditions(out: list[str]) -> None:
    """§10: the header (§8), block (§9) and strip runs side by side."""
    out += ["## 10. Header, block and stripped lines (experiments A, A2, A3)", ""]
    files = {
        "header": DATA / "obedience" / "trials-precedence.jsonl",
        "block": DATA / "obedience" / "trials-resolved.jsonl",
        "strip": DATA / "obedience" / "trials-strip.jsonl",
    }
    if not all(f.is_file() for f in files.values()):
        out += ["Not run yet.", ""]
        return
    by: dict[tuple[str, str], list[dict]] = defaultdict(list)
    conds: dict[str, list[str]] = {}
    for name, path in files.items():
        rows = jsonl(path)
        conds[name] = list(dict.fromkeys(r["precedence"] for r in rows))
        for r in rows:
            by[(r["precedence"], r["pair"])].append(r)
    base: dict[str, list[dict]] = defaultdict(list)
    for r in jsonl(DATA / "obedience" / "trials.jsonl"):
        base[r["pair"]].append(r)
    pairs = list(base)

    def first(cond: str) -> str:
        return cond[-1] if cond.startswith(("resolved-", "strip-")) else cond[0]

    out += [
        "Sources: `data/obedience/trials-precedence.jsonl` (§8), `trials-resolved.jsonl` (§9), "
        "`trials-strip.jsonl`; `skillfetch obedience ... --precedence strip-a --precedence "
        "strip-b`. Strip: no header and no block; in the losing skill's body each of the "
        "pair's evidence lines (as in §9) is replaced, not deleted, by `<!-- overridden by "
        '<winner>: "<line>" -->` (strip-a: A wins; strip-b: B wins); the skills load A then '
        "B. Same pairs, tasks, harness and classification as §6, §8 and §9. Controlled: the "
        "followed skill is the one ranked (header) or named (block, strip) first. Turned "
        "around: a pair whose §6 winner was ranked or named second and the other skill won "
        "the majority of that condition's 5 runs.",
        "",
        "| condition | runs | controlled, all runs | controlled, one-skill runs | "
        "§6 winners turned around | §6 winners kept |",
        "|---|---|---|---|---|---|",
    ]
    for name in files:
        for cond in conds[name]:
            rows = [r for p in pairs for r in by[(cond, p)]]
            hit = sum(r["followed"] == first(cond) for r in rows)
            one = sum(r["followed"] in ("a", "b") for r in rows)
            turned = kept = 0
            for p in pairs:
                w = _winner(base[p])
                if w is None or first(cond) == w:
                    continue
                won = _winner(by[(cond, p)])
                turned += won == first(cond)
                kept += won == w
            out.append(
                f"| {name}: `{cond}` | {len(rows)} | {hit}/{len(rows)} ({hit / len(rows):.2f}) "
                f"| {hit}/{one} | {turned} | {kept} |"
            )
    out += [
        "",
        "Per pair (controlled runs out of 5):",
        "",
        "| pair (A ⟷ B) | §6 winner | " + " | ".join(c for n in files for c in conds[n]) + " |",
        "|---|---|" + "---|" * sum(len(c) for c in conds.values()),
    ]
    for p in pairs:
        a, b = (x.split("/")[1].split("@")[0] for x in p.split("|"))
        cells = [
            str(sum(r["followed"] == first(c) for r in by[(c, p)])) for n in files for c in conds[n]
        ]
        out.append(f"| {a} ⟷ {b} | {_winner(base[p]) or 'tie'} | " + " | ".join(cells) + " |")
    out.append("")


def router_e2e(out: list[str]) -> None:
    """§11: the router in real Claude Code sessions (stage 1 and 1b of the end-to-end test)."""
    out += ["## 11. Router in real sessions (end-to-end stages 1, 1b and 2)", ""]
    path = DATA / "e2e" / "router-e2e.json"
    if not path.is_file():
        out += ["Not run yet.", ""]
        return
    d = json.loads(path.read_text())
    s1, s1b = d["stage1"], d["stage1b"]
    sources = ", ".join(d["sources"])
    out += [
        f"Source: `data/e2e/router-e2e.json` (exported from the e2e workspace: {sources}). "
        "`claude -p` headless sessions, Claude Code plan, default model, one run per task "
        "and condition repeated twice. A: the upstream repo. B: A plus the expert-chosen "
        "skills for the task, loaded through `load_skills` and appended to the system "
        "prompt. C: A plus the router skill and the MCP server; the session decides on its "
        "own whether to search and what to load. Repos: fastapi full-stack template, "
        "Next.js with-typescript. Checks were written and frozen before the runs. Blind "
        "judging: one judge (the Claude session that ran the test), condition hidden "
        "behind random codes.",
        "",
        "| stage | tasks | condition | sessions | checks pass | median turns | "
        "median input tokens | searched | loaded |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, st in (("1", s1), ("1b", s1b)):
        for cond, a in st["by_condition"]["expert_tasks"].items():
            out.append(
                f"| {name} | {st['expert_tasks']} with an expert skill | {cond} | "
                f"{a['sessions']} | {a['check_pass']}/{a['sessions']} | {a['median_turns']:g} | "
                f"{a['median_input_tokens']:,} | {a['searched']} | {a['loaded']} |"
            )
    m = d["stage1_selection_match"]
    b1, b1b, r = d["stage1_blind"], d["stage1b_blind"], d["retrieval_bm25"]

    def conds(x: dict) -> str:
        return (
            ", ".join(f"{k} {v:.2f}" for k, v in x.items() if k != "n")
            + f" (n={x['n']} per condition)"
        )

    out += [
        "",
        f"- Stage 1, C on the {s1['expert_tasks']} expert tasks "
        f"({s1['c_runs_on_expert_tasks']} runs), what it loaded against the expert's pick: "
        f"same set {m['same']}, a different set covering the same ground {m['equivalent']}, "
        f"a set that does not cover it {m['different']}, nothing loaded {m['not_loaded']} "
        "(hand-judged). Runs whose loaded set contains an expert id: "
        f"{s1['c_loaded_an_expert_id']}.",
        f"- Stage 1b, C ({s1b['c_runs_on_expert_tasks']} runs): loaded an expert id in "
        f"{s1b['c_loaded_an_expert_id']}; none of the five expert skills was in C's search "
        "top 10.",
        "- Stage 1 blind: screenshots usefulness 1-5 "
        f"{conds(b1['screens_abc_usefulness'])}; A vs C only "
        f'{conds(b1["screens_ac_usefulness"])}; docs "would merge as is" 1-5 '
        f"{conds(b1['docs_merge'])}.",
        "- Stage 1b blind: landing pages usefulness 1-5 "
        f"{conds(b1b['screens_usefulness'])}; generic-AI-look checklist hits "
        f"{conds(b1b['screens_ai_look'])}; plans normalised rank (0 = best) "
        f"{conds(b1b['plans_norm_rank'])}; implementation followed the plan 1-5 "
        f"{conds(b1b['plan_followed'])}.",
        f"- Retrieval, the {r['queries']} queries C sent on tasks with an expert skill, "
        "re-ranked by the current BM25: the expert skill in the top 3 for "
        f"{r['top3']}, top 10 for {r['top10']}, top 50 for {r['top50']}.",
        "",
    ]
    all1 = s1["by_condition"].get("all_tasks")
    if all1:
        a, c = all1["A"], all1["C"]
        ex = s1["by_condition"]["expert_tasks"]
        out[-1:-1] = [
            f"- All {s1['tasks']} stage 1 tasks (A and C on all {s1['tasks']}, B on the "
            f"{s1['expert_tasks']} with an expert skill): checks pass "
            + ", ".join(f"{k} {v['check_pass']}/{v['sessions']}" for k, v in all1.items())
            + "; median turns "
            + ", ".join(f"{k} {v['median_turns']:g}" for k, v in all1.items())
            + "; median input tokens "
            + ", ".join(f"{k} {v['median_input_tokens']:,}" for k, v in all1.items())
            + f". C against A: {c['median_turns'] - a['median_turns']:+g} turns, "
            f"{c['median_input_tokens'] / a['median_input_tokens'] - 1:+.0%} input tokens over all "
            f"tasks; {ex['C']['median_turns'] - ex['A']['median_turns']:+g} turns, "
            f"{ex['C']['median_input_tokens'] / ex['A']['median_input_tokens'] - 1:+.0%} on the "
            "expert tasks.",
        ]
    if "stage1b_rejudge" in d:
        rejudge(out, d["stage1b_rejudge"], d["landing_expert_ranks"])
    if "stage2" in d:
        stage2(out, d["stage2"], d["stage2_landing_from_1b"], d.get("stage2_setup"), d)


def rejudge(out: list[str], rj: dict, ranks: dict) -> None:
    """§11, stage 1b rejudge: A / B / C (first version) / C2 judged together by fresh judges."""
    conds = ("A", "B", "C", "C2")
    names = {"A": "A", "B": "B", "C": "C, first version (k=10)", "C2": "C2, search k=50"}
    out += [
        "### Stage 1b rejudge",
        "",
        "Source: e2e/stage1b/report-1b-c2.md §1 and §4 (`rejudge/`). A, B and C are the 1b "
        "sessions; C2 is the same 5 tasks × 2 runs with skillfetch e2a1b65 (search_skills k=50, "
        "compact results). All four conditions judged together under fresh random codes by "
        "sub-agent judges (same model) that saw only the rubric and the outputs. Landing pages: "
        "2 tasks × 2 runs (n=4); plan: 1 task × 2 runs (n=2); median turns over all 5 tasks "
        "(n=10).",
        "",
        "| condition | landing usable 1-5 | landing AI-template tells | plan normalised rank "
        "(0 = best) | median turns |",
        "|---|---|---|---|---|",
    ]
    for c in conds:
        out.append(
            f"| {names[c]} | {rj['usable'][c]:.2f} | {rj['ai_tells'][c]:.2f} | "
            f"{rj['plan_norm_rank'][c]:.2f} | {rj['median_turns'][c]:g} |"
        )
    c_ranks, c2_ranks = ranks["c_bm25"], ranks["c2_session"]
    out += [
        "",
        f"- `anthropics-skills/frontend-design` in the landing queries: C (k={ranks['c_k']}), "
        f"re-ranked by the current BM25: {', '.join(map(str, c_ranks))} (never in the "
        f"{ranks['c_k']} results returned); C2 (k={ranks['c2_k']}), in the results each session "
        f"received: {', '.join(map(str, c2_ranks))}, mean {sum(c2_ranks) / len(c2_ranks):.1f}.",
        "",
    ]


STAGE2_NAMES = {
    "s2-tests": "test writing",
    "s2-api": "backend API",
    "s2-docs": "documentation",
    "s2-data": "data script",
}


def stage2(out: list[str], s2: dict, land: dict, setup: dict | None, d: dict) -> None:
    """§11, stage 2 (domain generalisation): one task per domain, A / B / C2, 5 runs each."""
    out += [
        "### Stage 2: domain generalisation",
        "",
        "Same harness and conditions as 1b (A no skill; B the expert's skill appended to the "
        "system prompt; C2 router + search k=50, skillfetch e2a1b65), one large generative "
        "task per domain, 5 runs per condition. Score: overall 1-5 from two blind judging "
        "passes (fresh codes, fresh judge), mean. Landing pages: 1b rejudge, one pass, n=4.",
        "",
    ]
    if setup:
        out += [
            "Repos (e2e/stage2/report-stage2.md §0): test writing, a package with a "
            f"{setup['tests_module_lines']}-line rules module and no tests; backend API, an empty "
            f"FastAPI project, checked by {setup['api_contract_calls']} contract calls; "
            "documentation, the stage 1 Next.js repo with its README removed; data script, a "
            f"{setup['orders_csv_rows']}-row orders CSV with {setup['orders_planted_problems']} "
            "planted problems.",
            "",
        ]
    out += [
        "| domain | condition | sessions | score (pass 1 / pass 2) | checks pass | median turns "
        "| median input tokens | C2: expert skill in top 50 / picked / loaded (mean rank) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in ("A", "B", "C2"):
        hit = (
            f"{land['c2_in_top50']}/4 / {land['c2_picked']}/4 / {land['c2_loaded_expert']}/4 "
            f"({sum(d['landing_expert_ranks']['c2_session']) / 4:.1f}) |"
            if c == "C2"
            else "|"
        )
        out.append(f"| landing page (1b) | {c} | 4 | {land['usefulness'][c]:.2f} | | | | " + hit)
    for t, name in STAGE2_NAMES.items():
        for c in ("A", "B", "C2"):
            a = s2["tasks"][t][c]
            n = a["sessions"]
            hit = (
                f"{a['b_in_top50']}/5 / {a['b_picked']}/5 / {a['b_loaded']}/5 "
                f"({sum(a['b_ranks']) / len(a['b_ranks']):.1f})"
                if c == "C2"
                else ""
            )
            out.append(
                f"| {name} | {c} | {n} | {a['score']:.2f} ({a['score_p1']:.2f} / "
                f"{a['score_p2']:.2f}) | {a['check_pass']}/{n} | {a['median_turns']:g} | "
                f"{a['median_input_tokens']:,} | {hit} |"
            )
    repro = [
        t for t in STAGE2_NAMES if s2["tasks"][t]["C2"]["score"] >= s2["tasks"][t]["B"]["score"]
    ]
    with_landing = len(repro) + (land["usefulness"]["C2"] >= land["usefulness"]["B"])
    consistency = "; ".join(
        f"{STAGE2_NAMES[t]} {c['total_exact_agree']}/{c['n']} identical, "
        f"mean |diff| {c['total_mean_abs_diff']}"
        for t, c in s2["consistency"].items()
    )
    ABC2 = ("A", "B", "C2")

    def ratio(t: str) -> str:
        a, c2 = s2["tasks"][t]["A"], s2["tasks"][t]["C2"]
        return (
            f"{STAGE2_NAMES[t]} {c2['median_input_tokens'] / a['median_input_tokens']:.2f}x, "
            f"{c2['median_turns'] - a['median_turns']:+g} turns"
        )

    ratios = "; ".join(ratio(t) for t in STAGE2_NAMES)
    out += [
        "",
        f"- C2 scored at least B in {len(repro)} of 4 domains "
        f"({', '.join(STAGE2_NAMES[t] for t in repro) or 'none'}); with landing pages "
        f"{with_landing} of 5.",
        f"- Judging consistency (pass 1 vs pass 2, overall score): {consistency}.",
        "- C2 against A, median input tokens and turns: " + ratios + ".",
        "- Objective metrics: test writing branch coverage (mean) "
        + ", ".join(f"{c} {s2['tasks']['s2-tests'][c]['mean_branch_cov']:g}%" for c in ABC2)
        + "; backend API contract calls passed (mean, of 27) "
        + ", ".join(f"{c} {s2['tasks']['s2-api'][c]['mean_contract_pass']:g}" for c in ABC2)
        + ".",
        "- Limitation (documentation): two C2 runs (r4, r5) described the router's install "
        "files (`.mcp.json`, `.claude/`, present only in the C2 repo) in their README, and "
        "pass 1 cited that when marking them down: a trace of the harness, not of the router.",
        "- Limitation (interactive skills): the sessions had no AskUserQuestion or plan-mode "
        "tools, so whether a router-picked skill with interview or approval steps stalls a "
        "real session is not observed. Backend API C2 r1 loaded `uasl/fastapi-endpoint` "
        '("Enter plan mode", "Use AskUserQuestion to clarify requirements") and answered '
        '"Requirements are clear enough to implement directly."',
        "",
    ]


def embedding(out: list[str]) -> None:
    """§12: the embedding retrieval evaluation (not adopted)."""
    out += ["## 12. Embedding retrieval (not adopted)", ""]
    path = DATA / "e2e" / "router-e2e.json"
    e = json.loads(path.read_text()).get("embedding_eval") if path.is_file() else None
    if not e:
        out += ["Not run yet.", ""]
        return
    m, n = e["model"], e["queries"]

    def cell(x: int) -> str:
        return f"{x}/{n} = {x / n:.2f}"

    out += [
        "Source: `embedding_eval` in `data/e2e/router-e2e.json` "
        "(e2e/retrieval/report-embedding.md, `emb-ranks.jsonl`, `emb-timing.json`). "
        "Offline, no sessions, no runtime change. "
        f"{n} queries: the queries C sent on tasks with an expert skill (stages 1 and 1b); gold = "
        f"the expert skill id. Documents: the {m['docs']} tier A/B canonical skills, text = "
        "title + description + summary + synthetic queries. RRF: reciprocal rank fusion of the "
        "BM25 ranking (search_skills with the query's profile) and the embedding ranking, k=60.",
        "",
        "| method | gold in top 3 | top 10 | top 50 |",
        "|---|---|---|---|",
    ]
    for name, key in (
        ("BM25 (current)", "bm25"),
        ("embedding alone", "embedding"),
        ("BM25 + embedding RRF", "rrf"),
    ):
        r = e[key]
        out.append(f"| {name} | {cell(r['top3'])} | {cell(r['top10'])} | {cell(r['top50'])} |")
    picks = e["picks_top3"]
    out += [
        "",
        f"- Picking 1-3 from the top 50 (a sub-agent without the gold labels): BM25 top 50 "
        f"{cell(picks['bm25_top50'])}, RRF top 50 {cell(picks['rrf_top50'])}.",
        f"- Model: `{m['model']}`, {m['params']:,} parameters, {m['dim']} dimensions, max "
        f"{m['max_seq_length']} tokens ({m['docs_truncated']} of {m['docs']} documents truncated); "
        f"{m['model_cache_bytes'] / 1e6:.1f} MB on disk; load {m['model_load_s']} s, indexing "
        f"{m['index_s']} s; query latency median {m['query_latency_ms']['median']} ms. It would "
        "add sentence-transformers and torch as runtime dependencies.",
        "- Reproduce (in the e2e workspace, a venv with sentence-transformers): "
        "`python retrieval/scripts/eval_embed.py && python retrieval/scripts/report_embed.py`; "
        "BM25 ranks: `uv run python retrieval/scripts/eval_bm25.py` against skillfetch 53b81df "
        "and index-2026-10-22.",
        "",
    ]


def retrieval_benchmark(out: list[str]) -> None:
    """§13: the 380-task retrieval benchmark. Table 1's BM25 rows and the router-rule recall
    tables are computed here by `skillfetch eval retrieval` (evals/retrieval/, data/index);
    the rest is the stage 3 report, transcribed in data/e2e/stage3.md."""
    out += ["## 13. Retrieval benchmark (380 synthetic tasks)", ""]
    text_path = DATA / "e2e" / "stage3.md"
    if not text_path.is_file():
        out += ["Not run yet.", ""]
        return
    from skillfetch import evals
    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session

    before, _, after = text_path.read_text().partition("<!-- table 1 -->")
    results = evals.tables(Session(Index.load(DATA / "index")))
    router = ["router_R-a", "router_R-b", "router_R-c", "bm25_q3"]
    for version in ("v3", "v2"):
        after = after.replace(
            f"<!-- router {version} -->", evals.render(*results[version], router).rstrip()
        )
    out += [
        before.rstrip(),
        "",
        "**Table 1, recall@10 / @50 of search_skills** (`skillfetch eval retrieval --index "
        "data/index`), on oracle v2 (the stage 3 labels in evals/retrieval/). Mean per-task "
        "recall against (i) all relevant skills, (ii) the ones the "
        "catalogue pass picked (independent of any ranking) and the process subset. "
        "Tasks with no relevant skill are skipped, and so are expect_none tasks.",
        "",
        evals.render(*results["v2"], ["bm25_q1", "bm25_q2", "bm25_q3"]).rstrip(),
        "",
        after.strip(),
        "",
    ]


def stage4(out: list[str]) -> None:
    """§14: stage 4, the router in real repos, clean vs the author's environment (the stage 4
    report, transcribed in data/e2e/stage4.md)."""
    out += ["## 14. Stage 4: router in real repos, clean vs author's environment", ""]
    path = DATA / "e2e" / "stage4.md"
    out += [path.read_text().strip() if path.is_file() else "Not run yet.", ""]


def stage5(out: list[str]) -> None:
    """§15: stage 5, what makes the router fire (the stage 5 reports, transcribed in
    data/e2e/stage5.md)."""
    out += ["## 15. Stage 5: what makes the router fire", ""]
    path = DATA / "e2e" / "stage5.md"
    out += [path.read_text().strip() if path.is_file() else "Not run yet.", ""]


def codex(out: list[str]) -> None:
    """§16: Codex with the router steps in AGENTS.md (the Codex reports, transcribed in
    data/e2e/codex.md)."""
    out += ["## 16. Codex (after the post freeze)", ""]
    path = DATA / "e2e" / "codex.md"
    out += [path.read_text().strip() if path.is_file() else "Not run yet.", ""]


def stage6(out: list[str]) -> None:
    """§17: stage 6, the selection rule and choosing none (the stage 6 reports, transcribed in
    data/e2e/stage6.md)."""
    out += ["## 17. Stage 6: choosing none (after the post freeze)", ""]
    path = DATA / "e2e" / "stage6.md"
    out += [path.read_text().strip() if path.is_file() else "Not run yet.", ""]


def main() -> None:
    out = [
        "# Numbers for the write-up",
        "",
        "Frozen for the 2026-10-26 post.",
        "",
        "Generated by `uv run python scripts/write_numbers.py` from `data/` and "
        "`~/.skillfetch/`. Each section names its source; rerun the script after a rebuild.",
        "",
    ]
    for section in (
        corpus,
        constraints_and_pairs,
        calibration,
        judge,
        obedience,
        costs,
        runtime,
        precedence,
        resolved,
        three_conditions,
        router_e2e,
        embedding,
        retrieval_benchmark,
        stage4,
        stage5,
        codex,
        stage6,
    ):
        section(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
