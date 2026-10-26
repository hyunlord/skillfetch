"""How many skills the router picks, and whether load_skills' 8,000-token budget limits it.
No model calls.

  uv run python scripts/skill_count.py extract --e2e E2E_DIR [--out ROWS]
      E2E_DIR: the e2e workspace (stage10-private/, stage11-private/, stageQ-private/ with
      the session transcripts, plus the label files in RUNC and PRECHECK). Read only. Writes one
      derived row per session (Stage 10, 11) or request (Stage Q) that called search_skills:
      skill ids, counts and grades only, no transcript text. Local pinned paths become
      "path:<local>".
  uv run python scripts/skill_count.py report [--rows ROWS]
      The tables of docs/design/skill-count.md from the derived rows.

Token numbers are the search results' token_estimate (characters / 4 of the indexed file)
and, for what was loaded, the loaded content's characters / 4. A budget drop is an
`errors` entry of load_skills or resolve_and_load that says "over max_tokens".
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROWS = ROOT / "evals" / "e2e" / "skill-count" / "rows.jsonl"
BUDGET = 8000
SF = "mcp__skillfetch__"

# Search-result labels per task, only where the label was made for the same request text:
# bundle (4) takes the run-c labels (Stage 9, index-staging-4 pool), the bundle (3) tasks
# their pre-run grading of the union of both indexes' top 50. Other tasks have grades for
# the skills that were loaded only (grades-s10 / grades-s11), so they count as unlabeled.
RUNC = "stage9/run-c/oracle-v5-ss-b-s9g.jsonl"
PRECHECK = {
    "s10-t001": "stage10-private/b3new/precheck-grades.jsonl",
    "s10-t033": "stage10-private/b3new/precheck-grades.jsonl",
    "s10-t114": "stage10-private/b3new/precheck-grades.jsonl",
    "s11-t160": "stage11-private/b3/precheck-grades.jsonl",
    "s11-t162": "stage11-private/b3/precheck-grades.jsonl",
    "s11-t118": "stage11-private/b3/precheck-grades.jsonl",
    "s11-t266": "stage11-private/b4/precheck-grades.jsonl",
}
RUNC_TASKS = {"s10-t016", "s10-t263", "s10-t115", "s10-t198"}


def _jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def labels(e2e: Path) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    runc = {r["id"]: r for r in _jsonl(e2e / RUNC)}
    for task in RUNC_TASKS:
        out[task] = {x["skill"]: x["grade"] for x in runc[task.split("-", 1)[1]]["pool"]}
    for task, rel in PRECHECK.items():
        tid = task.split("-", 1)[1]
        out[task] = {g["skill"]: g["grade"] for g in _jsonl(e2e / rel) if g["task"] == tid}
    return out


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _redact(skill_id: str) -> str:
    return "path:<local>" if skill_id.startswith("path:") else skill_id


def calls(path: Path) -> list[tuple[str, dict, dict | None]]:
    """(tool, input, parsed result) for every skillfetch call, in order."""
    uses, results = [], {}
    with path.open() as f:
        for line in f:
            e = json.loads(line)
            if e.get("type") not in ("assistant", "user"):
                continue
            for b in e["message"].get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b["name"].startswith(SF):
                    uses.append((b["id"], b["name"][len(SF) :], b.get("input") or {}))
                elif b.get("type") == "tool_result":
                    try:
                        results[b["tool_use_id"]] = json.loads(_text(b.get("content")))
                    except (json.JSONDecodeError, KeyError):
                        results[b.get("tool_use_id")] = None
    return [(tool, inp, results.get(uid)) for uid, tool, inp in uses]


def session_row(path: Path, task_labels: dict[str, int] | None) -> dict | None:
    cs = calls(path)
    searches = [c for c in cs if c[0] == "search_skills"]
    if not searches:
        return None
    # The task search is the one with the most queries (the router sends four); a search for
    # a skill the user named (Q5) has one. Labels are counted on the task search's results.
    est, task_results, most = {}, [], -1
    for _, inp, res in searches:
        items = (res or {}).get("results") or []
        for x in items:
            est[x["id"]] = x.get("token_estimate")
        n_queries = len(inp.get("queries") or []) or 1
        if items and n_queries > most:
            task_results, most = [x["id"] for x in items], n_queries
    auto, pinned, max_tokens = [], [], set()
    loaded_tokens, drops, other_errors, loaded_calls = 0, [], 0, 0
    for tool, inp, res in cs:
        if tool in ("resolve_set", "resolve_and_load"):
            auto += [i for i in inp.get("auto_ids") or [] if i not in auto]
            pinned += [i for i in inp.get("pinned_ids") or [] if i not in pinned]
        if tool in ("load_skills", "resolve_and_load"):
            loaded_calls += 1
            max_tokens.add(inp.get("max_tokens", BUDGET))
            res = res or {}
            loaded_tokens += len(res.get("content") or "") // 4
            for err in res.get("errors") or []:
                msg = err.get("error", "") if isinstance(err, dict) else str(err)
                if "over max_tokens" in msg:
                    drops.append(_redact(err.get("id", "?")))
                elif tool == "load_skills" or "fetch" in msg or "hash" in msg:
                    other_errors += 1
    chosen = set(auto) | set(pinned)
    row = {
        "searches": len(searches),
        "picked": auto,
        "n_picked": len(auto),
        "pinned": [_redact(p) for p in pinned],
        "picked_tokens": sum(est.get(i) or 0 for i in auto),
        "picked_tokens_missing": sum(1 for i in auto if est.get(i) is None),
        "pinned_tokens": sum(est.get(i) or 0 for i in pinned if not i.startswith("path:")),
        "load_calls": loaded_calls,
        "max_tokens": sorted(max_tokens),
        "loaded_tokens": loaded_tokens,
        "budget_drops": drops,
        "other_load_errors": other_errors,
        "results": len(task_results),
    }
    if task_labels is not None:
        graded = [i for i in task_results if i in task_labels]
        row["labeled_results"] = len(graded)
        row["picked_grades"] = [task_labels.get(i) for i in auto]
        row["unpicked_g2"] = [
            {"id": i, "grade": task_labels[i], "token_estimate": est.get(i)}
            for i in graded
            if task_labels[i] >= 2 and i not in chosen
        ]
    return row


def _stage_sessions(e2e: Path):
    """(stage, group, task, tag, k, transcript) for every main-run session or request."""
    p10 = e2e / "stage10-private"
    for name in ("sessions-m1-m2-m3.jsonl", "sessions-n1-n2-n3.jsonl"):
        for r in _jsonl(p10 / name):
            if r["cond"] == "A":
                continue
            group = f"{r['env']} {r['cond']}" + (" b3-remeasure" if r["tag"][0] == "n" else "")
            path = p10 / "runs" / r["env"] / r["cond"] / f"{r['task']}-{r['tag']}.jsonl"
            yield "10", group, r["task"], r["tag"], 1, r["bundle"], path
    p11 = e2e / "stage11-private"
    for r in _jsonl(p11 / "sessions-m1-m2-m3-m4-m5-m6.jsonl"):
        if r["cond"] == "A":
            continue
        path = p11 / "runs" / r["cond"] / f"{r['task']}-{r['tag']}.jsonl"
        yield "11", r["cond"], r["task"], r["tag"], 1, r["bundle"], path
    pq = e2e / "stageQ-private"
    for r in _jsonl(pq / "requests-m1-m2-m3-m4-m5.jsonl"):
        if r["job"].endswith(":off"):
            continue
        stem = r["job"].replace(":", "-") + f"-{r['tag']}"
        q2 = r["kind"] == "q2"  # one transcript per request: .p1 ... .p4
        name = f"{stem}.p{r['k']}.jsonl" if q2 or r["k"] > 1 else f"{stem}.jsonl"
        group = {"q1": "Q1 on", "q2": "Q2 " + r["job"][3:], "q5n": "Q5 named", "q5t": "Q5 trivial"}
        yield (
            "Q",
            group.get(r["kind"], r["kind"].upper()),
            r["task"],
            r["tag"],
            r["k"],
            None,
            (pq / "runs" / name),
        )


def extract(e2e: Path, out: Path) -> None:
    labs = labels(e2e)
    rows, seen, skipped = [], 0, Counter()
    for stage, group, task, tag, k, bundle, path in _stage_sessions(e2e):
        seen += 1
        if not path.exists():
            skipped["missing transcript"] += 1
            continue
        row = session_row(path, labs.get(task))
        if row is None:
            skipped["no search"] += 1
            continue
        rows.append(
            {"stage": stage, "group": group, "bundle": bundle, "task": task, "tag": tag, "k": k}
            | row
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"sessions": seen, "rows": len(rows), "skipped": dict(skipped)}))


def _stage_label(r: dict) -> str:
    return {"10": "Stage 10", "11": "Stage 11", "Q": "Stage Q"}[r["stage"]]


def report(rows_path: Path) -> None:
    rows = _jsonl(rows_path)
    by = defaultdict(list)
    for r in rows:
        by[(_stage_label(r), r["group"])].append(r)

    print("## Picks per session\n")
    print(
        "| stage | group | sessions | 0 | 1 | 2 | 3 | pinned ≥ 1 | median picked tokens "
        "| max picked tokens | picked > 8,000 | loaded > 8,000 | budget drops |"
    )
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    tot = Counter()
    for (stage, group), rs in sorted(by.items()):
        n = Counter(min(r["n_picked"], 3) for r in rs)
        toks = [r["picked_tokens"] for r in rs if r["n_picked"]]
        drops = sum(len(r["budget_drops"]) for r in rs)
        over = sum(1 for r in rs if r["picked_tokens"] + r["pinned_tokens"] > BUDGET)
        lover = sum(1 for r in rs if r["loaded_tokens"] > BUDGET)
        pin = sum(1 for r in rs if r["pinned"])
        med = statistics.median(toks) if toks else "–"
        mx = max(toks) if toks else "–"
        print(
            f"| {stage} | {group} | {len(rs)} | {n[0]} | {n[1]} | {n[2]} | {n[3]} | {pin} "
            f"| {med} | {mx} | {over} | {lover} | {drops} |"
        )
        tot.update(
            {
                "sessions": len(rs),
                "0": n[0],
                "1": n[1],
                "2": n[2],
                "3": n[3],
                "pin": pin,
                "over": over,
                "lover": lover,
                "drops": drops,
            }
        )
    alltoks = [r["picked_tokens"] for r in rows if r["n_picked"]]
    print(
        f"| all | | {tot['sessions']} | {tot['0']} | {tot['1']} | {tot['2']} | {tot['3']} "
        f"| {tot['pin']} | {statistics.median(alltoks)} | {max(alltoks)} | {tot['over']} "
        f"| {tot['lover']} | {tot['drops']} |"
    )

    print("\n## Picked-token distribution (sessions with ≥ 1 pick)\n")
    edges = [2000, 4000, 6000, 7000, 8000]
    buckets = Counter()
    for t in alltoks:
        buckets[next((e for e in edges if t <= e), "> 8000")] += 1
    print("| picked tokens | sessions |\n|---|---:|")
    lo = 0
    for e in edges:
        print(f"| {lo}–{e} | {buckets[e]} |")
        lo = e + 1
    print(f"| > 8,000 | {buckets['> 8000']} |")

    print("\n## Grade ≥ 2 skills in the results that were not picked (labeled tasks only)\n")
    print(
        "| stage | group | sessions on labeled tasks | labeled results (median of 50) "
        "| sessions with an unpicked grade ≥ 2 | of those, with < 3 picks "
        "| of those, smallest unpicked would push the set over 8,000 |"
    )
    print("|---|---|---:|---:|---:|---:|---:|")
    for (stage, group), rs in sorted(by.items()):
        lab = [r for r in rs if "labeled_results" in r]
        if not lab:
            continue
        miss = [r for r in lab if r["unpicked_g2"]]
        room = [r for r in miss if r["n_picked"] < 3]
        tight = [
            r
            for r in room
            if r["picked_tokens"]
            + r["pinned_tokens"]
            + min(x["token_estimate"] or 0 for x in r["unpicked_g2"])
            > BUDGET
        ]
        med = statistics.median(r["labeled_results"] for r in lab)
        print(
            f"| {stage} | {group} | {len(lab)} | {med} | {len(miss)} | {len(room)} | {len(tight)} |"
        )

    miss = [r for r in rows if r.get("unpicked_g2")]
    room = [r for r in miss if r["n_picked"] < 3]
    head = [
        BUDGET
        - r["picked_tokens"]
        - r["pinned_tokens"]
        - min(x["token_estimate"] or 0 for x in r["unpicked_g2"])
        for r in room
    ]
    fill = sum(
        1
        for r in room
        if r["picked_tokens"]
        + r["pinned_tokens"]
        + sum(sorted(x["token_estimate"] or 0 for x in r["unpicked_g2"])[: 3 - r["n_picked"]])
        <= BUDGET
    )
    picks = Counter(r["n_picked"] for r in miss)
    print(
        f"\nSessions with an unpicked grade ≥ 2: {len(miss)}; picks there "
        + ", ".join(f"{k}: {v}" for k, v in sorted(picks.items()))
        + f". With < 3 picks: {len(room)}. Budget left after adding the smallest unpicked "
        f"grade ≥ 2: min {min(head)}, median {statistics.median(head)}. Filling the set to 3 "
        f"with the smallest unpicked grade ≥ 2 stays within 8,000 in {fill} of {len(room)}."
    )
    pg = Counter(g for r in rows for g in r.get("picked_grades") or [])
    print(
        "Grades of the picked skills on labeled tasks: "
        + ", ".join(f"{k}: {v}" for k, v in sorted(pg.items(), key=lambda kv: str(kv[0])))
    )

    print("\n## Max_tokens passed\n")
    mt = Counter(tuple(r["max_tokens"]) for r in rows if r["load_calls"])
    print(" ".join(f"{list(k)}: {v}" for k, v in mt.items()))
    print("\nOther load errors (fetch or hash):", sum(r["other_load_errors"] for r in rows))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("--e2e", type=Path, required=True)
    ex.add_argument("--out", type=Path, default=ROWS)
    rp = sub.add_parser("report")
    rp.add_argument("--rows", type=Path, default=ROWS)
    args = p.parse_args(argv)
    if args.cmd == "extract":
        extract(args.e2e, args.out)
    else:
        report(args.rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
