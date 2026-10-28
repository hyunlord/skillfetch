"""The semantic review over the released index (numbers.md §32), in two stages.

    uv run python evals/index-review/run.py stage1 [--jobs 6] [--budget 95]
    uv run python evals/index-review/run.py targets
    uv run python evals/index-review/run.py stage2 [--jobs 6] [--budget 95]
    uv run python evals/index-review/run.py export

- **stage1**: every canonical skill of the index (`~/.skillfetch/index`), SKILL.md alone
  ("SKILL.md only"), with scan --review's reviewer (ClaudeReviewer: isolated `claude -p`, the
  frozen checklist). Long SKILL.md files are read in parts as in scan --review.
- **stage2**: the skills stage 1 flagged, plus the skills whose rule-based scan warns about
  remote instructions or risky scripts, reviewed in full (all text files).
- Each stage appends one row per skill to <work>/stage<N>.jsonl as it goes, so a stopped run
  resumes. A skill whose review failed (cut off, refused, no findings JSON) is asked once more
  at the end of the stage. The stage stops scheduling new skills once the spend of both stages
  reaches --budget (API-price equivalent, as `claude -p` reports it).
- **export**: derived rows here (results-stage<N>.jsonl: skill id, flagged, categories,
  file:line, incomplete, partly reviewed, requests, cost; no quoted text) and, in <work>, the
  list for human judgement with the quoted lines (to-judge.md, to-judge.jsonl). Quoted lines
  are not committed until they are judged.
- "partly reviewed" is counted apart; this research run computes no install advice.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR
from skillfetch.ingest.injection import scan_skill
from skillfetch.ingest.review import CHECKLIST_SHA
from skillfetch.ingest.review_claude import ClaudeReviewer
from skillfetch.ingest.snapshot import DEFAULT_WORK_DIR

HERE = Path(__file__).resolve().parent
WORK = Path("~/skillfetch-work/index-review").expanduser()


def canonical() -> list[tuple[str, Path]]:
    out = []
    for line in (DEFAULT_INDEX_DIR / "skills.jsonl").open():
        r = json.loads(line)
        if r.get("canonical_id", r["id"]) == r["id"]:
            out.append((r["id"], DEFAULT_WORK_DIR / r["source_id"] / r["commit"] / r["path"]))
    return sorted(out)


def _rows(stage: int) -> dict[str, dict]:
    path = WORK / f"stage{stage}.jsonl"
    rows: dict[str, dict] = {}
    if path.is_file():
        for line in path.open():
            x = json.loads(line)
            rows[x["skill"]] = x  # a retry's row replaces the first
    return rows


def spent() -> float:
    return sum(x["review"]["cost_usd"] or 0 for s in (1, 2) for x in _all_rows(s))


def _all_rows(stage: int) -> list[dict]:
    path = WORK / f"stage{stage}.jsonl"
    return [json.loads(x) for x in path.open()] if path.is_file() else []


def targets() -> list[str]:
    """Stage 2: flagged in stage 1, or the rules warn about remote instructions or scripts."""
    flagged = {s for s, x in _rows(1).items() if x["review"]["findings"]}
    picked = []
    for skill, folder in canonical():
        res = scan_skill(folder)
        remote = any(h.rule_id == "network.remote-instructions" for h in res.warnings)
        if skill in flagged or remote or res.risky_scripts:
            picked.append(skill)
    return picked


def run_stage(stage: int, jobs: int, budget: float) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    reviewer = ClaudeReviewer(cache=WORK / "cache", skill_md_only=stage == 1)
    folders = dict(canonical())
    names = list(folders) if stage == 1 else targets()
    lock = threading.Lock()
    total = [spent()]
    out = (WORK / f"stage{stage}.jsonl").open("a")

    def one(skill: str) -> None:
        with lock:
            if total[0] >= budget:
                return
        review = reviewer(folders[skill])
        with lock:
            total[0] += review.cost_usd or 0
            row = {"skill": skill, "stage": stage, "review": review.model_dump(mode="json")}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()

    for attempt in ("first", "retry"):
        done = _rows(stage)
        if attempt == "first":
            todo = [s for s in names if s not in done]
        else:  # failed replies are not cached, so this asks again
            todo = [s for s in names if s in done and done[s]["review"]["error"]]
        with ThreadPoolExecutor(jobs) as pool:
            for f in as_completed([pool.submit(one, s) for s in todo]):
                f.result()
        print(
            json.dumps(
                {
                    "stage": stage,
                    "pass": attempt,
                    "asked": len(todo),
                    "spent_usd": round(total[0], 2),
                }
            ),
            flush=True,
        )
        if total[0] >= budget:
            print(f"stopped: spend reached the budget (${budget})", flush=True)
            break
    out.close()


def _derived(x: dict) -> dict:
    r = x["review"]
    return {
        "skill": x["skill"],
        "stage": x["stage"],
        "read": "SKILL.md only" if x["stage"] == 1 else "all text files",
        "flagged": bool(r["findings"]),
        "categories": sorted({f["category"] for f in r["findings"]}),
        "locations": [f"{f['file']}:{f['line']}" for f in r["findings"]],
        "incomplete": r["error"] is not None,
        "partly_reviewed": bool(r["not_reviewed"]),
        "requests": r["requests"],
        "unverified": r["unverified"],
        "cost_usd": r["cost_usd"],
    }


def export() -> dict:
    summary: dict = {"checklist": CHECKLIST_SHA[:12]}
    judge = []
    for stage in (1, 2):
        rows = _rows(stage)
        if not rows:
            continue
        derived = [_derived(x) for x in rows.values()]
        (HERE / f"results-stage{stage}.jsonl").write_text(
            "".join(json.dumps(d) + "\n" for d in sorted(derived, key=lambda d: d["skill"]))
        )
        cats: dict[str, int] = {}
        for d in derived:
            for c in d["categories"]:
                cats[c] = cats.get(c, 0) + 1
        summary[f"stage{stage}"] = {
            "skills": len(derived),
            "flagged": sum(d["flagged"] for d in derived),
            "by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
            "incomplete": sum(d["incomplete"] for d in derived),
            "partly_reviewed": sum(d["partly_reviewed"] for d in derived),
            "requests": sum(d["requests"] for d in derived),
            # every row, a failed first try included (a retry's row replaces it above)
            "cost_usd": round(sum(x["review"]["cost_usd"] or 0 for x in _all_rows(stage)), 2),
        }
        for x in rows.values():
            for f in x["review"]["findings"]:
                judge.append({"skill": x["skill"], "stage": stage, **f})
    (WORK / "to-judge.jsonl").write_text(
        "".join(json.dumps(j, ensure_ascii=False) + "\n" for j in judge)
    )
    lines = ["# Index review: findings to judge (not committed)", ""]
    for cat in sorted({j["category"] for j in judge}):
        group = [j for j in judge if j["category"] == cat]
        lines += [
            f"## {cat} ({len(group)} findings, {len({j['skill'] for j in group})} skills)",
            "",
        ]
        for j in sorted(group, key=lambda j: (j["skill"], j["stage"], j["file"], j["line"])):
            lines.append(f"- [ ] `{j['skill']}` (stage {j['stage']}) `{j['file']}:{j['line']}`")
            lines.append(f"  > {j['quote']}")
            lines.append(f"  {j['why']}")
        lines.append("")
    (WORK / "to-judge.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=1))
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("stage1", "stage2"):
        s = sub.add_parser(name)
        s.add_argument("--jobs", type=int, default=6)
        s.add_argument("--budget", type=float, default=95.0)
    sub.add_parser("targets")
    sub.add_parser("export")
    args = p.parse_args(argv)
    if args.cmd == "targets":
        names = targets()
        print(json.dumps({"stage2_targets": len(names)}))
    elif args.cmd == "export":
        export()
    else:
        run_stage(int(args.cmd[-1]), args.jobs, args.budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
