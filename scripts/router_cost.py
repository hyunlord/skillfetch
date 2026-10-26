"""Where the router's extra turns and tokens go (issue #26), and what the cheaper variants
would cost offline. No model calls.

  uv run python scripts/router_cost.py sessions RUNS_DIR [--out rows.jsonl] [--grades G]
      RUNS_DIR: a Stage 10 runs folder (runs/<env>/<cond>/<task>-<tag>.jsonl transcripts
      with a .meta.json beside each). Read only. Prints per-condition phase tables.
  uv run python scripts/router_cost.py offline --index DIR [--index DIR ...]
      hit@k / recall@k for k = 10, 20, 30, 50 on the shipped router's queries (R-c) against
      oracle v3, and the size of the search_skills results (k, summary length).

Token counts in the session part are the API's own usage numbers. Sizes of tool results
and of search results are characters / 4 (the convention of token_estimate).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLFETCH = "mcp__skillfetch__"
PHASES = (
    "pre",
    "router_skill",
    "tool_schema",
    "profile",
    "search",
    "resolve",
    "load",
    "resolve_and_load",
    "between",
    "work",
)


def _tool_phase(name: str, inp: dict) -> str | None:
    """The router phase a tool call belongs to, or None for an ordinary work tool."""
    if name == "Skill" and "skillfetch" in json.dumps(inp).lower():
        return "router_skill"
    if name == "ToolSearch" and "skillfetch" in json.dumps(inp).lower():
        return "tool_schema"
    if name.startswith(SKILLFETCH):
        short = name.removeprefix(SKILLFETCH)
        return {
            "profile_repo": "profile",
            "search_skills": "search",
            "resolve_set": "resolve",
            "load_skills": "load",
            "resolve_and_load": "resolve_and_load",
        }.get(short, short)
    return None


def calls(path: Path) -> tuple[list[dict], dict[str, int], dict]:
    """API calls in order: {usage, tools: [(name, phase)]}; the size (chars) of each
    skillfetch tool result by phase; and the session's result event. Input-side usage per
    call (input, cache creation, cache read) sums to the result's totals; output tokens per
    call are partial in the stream, so only the result's total is used."""
    by_id: dict[str, dict] = {}
    result: dict = {}
    order: list[str] = []
    tool_phase: dict[str, str] = {}
    result_chars: Counter = Counter()
    for line in path.open():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            msg = ev["message"]
            mid = msg.get("id") or f"anon{len(order)}"
            if mid not in by_id:
                by_id[mid] = {"usage": msg.get("usage") or {}, "tools": []}
                order.append(mid)
            else:
                by_id[mid]["usage"] = msg.get("usage") or by_id[mid]["usage"]
            for c in msg.get("content") or []:
                if c.get("type") == "tool_use":
                    phase = _tool_phase(c.get("name", ""), c.get("input") or {})
                    by_id[mid]["tools"].append((c.get("name", ""), phase))
                    if phase:
                        tool_phase[c.get("id")] = phase
        elif ev.get("type") == "result":
            result = ev
        elif ev.get("type") == "user":
            content = ev.get("message", {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in tool_phase:
                        result_chars[tool_phase[c["tool_use_id"]]] += _text_len(c.get("content"))
    return [by_id[m] for m in order], dict(result_chars), result


def _text_len(content) -> int:
    """Characters of a tool result as the model sees it (text, not JSON-escaped)."""
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(c.get("text", "")) for c in content if isinstance(c, dict))
    return 0


def picked_ranks(path: Path) -> list[list]:
    """[1-based rank, skill id] in the session's last search_skills result, for each skill id
    the session then passed to resolve_set / resolve_and_load (auto_ids and pinned_ids)."""
    ranking: list[str] = []
    search_ids: set[str] = set()
    ranks: list[list] = []
    for line in path.open():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for c in ev["message"].get("content") or []:
                if c.get("type") != "tool_use":
                    continue
                name = c.get("name", "")
                if name == SKILLFETCH + "search_skills":
                    search_ids.add(c.get("id"))
                elif name in (SKILLFETCH + "resolve_set", SKILLFETCH + "resolve_and_load"):
                    inp = c.get("input") or {}
                    for sid in (inp.get("auto_ids") or []) + (inp.get("pinned_ids") or []):
                        if sid in ranking:
                            ranks.append([ranking.index(sid) + 1, sid])
        elif ev.get("type") == "user":
            content = ev.get("message", {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_result" and c.get("tool_use_id") in search_ids:
                        text = c.get("content")
                        if isinstance(text, list):
                            text = "".join(x.get("text", "") for x in text if isinstance(x, dict))
                        with contextlib.suppress(TypeError, ValueError, KeyError):
                            ranking = [r["id"] for r in json.loads(text)["results"]]
    return ranks


def _uncached(u: dict) -> int:
    return (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)


def _read(u: dict) -> int:
    return u.get("cache_read_input_tokens") or 0


def session_row(path: Path) -> dict | None:
    meta_path = path.with_suffix(".meta.json")
    if not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text())
    if not str(meta.get("tag", "")).startswith("m"):  # main run only (no pilots, no b3new)
        return None
    seq, result_chars, result = calls(path)
    if not seq or not result:
        return None
    router_idx = [i for i, c in enumerate(seq) if any(p for _, p in c["tools"])]
    first, last = (router_idx[0], router_idx[-1]) if router_idx else (None, None)
    phase_calls: Counter = Counter()
    phase_uncached: Counter = Counter()
    phase_read: Counter = Counter()
    for i, c in enumerate(seq):
        phases = [p for _, p in c["tools"] if p]
        if phases:
            phase = phases[0]
        elif first is None or i < first:
            phase = "pre"
        elif i > last:
            phase = "work"
        else:
            phase = "between"
        phase_calls[phase] += 1
        phase_uncached[phase] += _uncached(c["usage"])
        phase_read[phase] += _read(c["usage"])
    # context carried: a skillfetch result stays in the context of every later call
    carried: Counter = Counter()
    pos: dict[str, int] = {}
    for i, c in enumerate(seq):
        for _, p in c["tools"]:
            if p and p not in pos:
                pos[p] = i
    for p, i in pos.items():
        if p in result_chars:
            carried[p] = result_chars[p] // 4 * (len(seq) - 1 - i)
    return {
        "session": f"{meta['env']}/{meta['cond']}/{meta['task']}-{meta['tag']}",
        "env": meta["env"],
        "cond": meta["cond"],
        "task": meta["task"],
        "bundle": meta.get("bundle"),
        "calls": len(seq),
        "num_turns": result.get("num_turns"),
        "cost": result.get("total_cost_usd"),
        "uncached": _uncached(result.get("usage") or {}),
        "read": _read(result.get("usage") or {}),
        "out": (result.get("usage") or {}).get("output_tokens") or 0,
        "phase_calls": dict(phase_calls),
        "phase_uncached": dict(phase_uncached),
        "phase_read": dict(phase_read),
        "result_tokens": {k: v // 4 for k, v in result_chars.items()},
        "carried_tokens": dict(carried),
        "fired": first is not None,
        "picked_ranks": picked_ranks(path),
    }


def _med(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def sessions(runs: Path, out: Path | None, grades_path: Path | None = None) -> None:
    rows = [r for p in sorted(runs.glob("E1/*/*.jsonl")) if (r := session_row(p))]
    if out:
        out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r["cond"]].append(r)
    a_task = defaultdict(list)
    for r in by_cond.get("A", []):
        a_task[r["task"]].append(r)

    def a_med(r: dict, key: str) -> float:
        return _med([x[key] for x in a_task[r["task"]]])

    print(f"E1 main-run sessions: {len(rows)}\n")
    print(
        "| cond | sessions | fired | turns | API calls | cost $ | uncached input | cache read "
        "| output |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for cond in ("A", "R0", "R1", "R1s"):
        rs = by_cond.get(cond, [])
        if rs:
            print(
                f"| {cond} | {len(rs)} | {sum(r['fired'] for r in rs)} | "
                f"{_med([r['num_turns'] for r in rs])} | {_med([r['calls'] for r in rs])} | "
                f"{_med([r['cost'] for r in rs]):.3f} | {_med([r['uncached'] for r in rs]):,.0f} | "
                f"{_med([r['read'] for r in rs]):,.0f} | {_med([r['out'] for r in rs]):,.0f} |"
            )
    print("\n(medians over sessions)\n")
    print("Router minus A on the same task (mean over sessions of R − median A of its task):\n")
    print(
        "| cond | turns | API calls | cost $ | uncached input | cache read | output |\n"
        "|---|---:|---:|---:|---:|---:|---:|"
    )
    for cond in ("R0", "R1", "R1s"):
        rs = by_cond.get(cond, [])
        if rs:
            d = {
                k: statistics.mean(r[k] - a_med(r, k) for r in rs)
                for k in ("num_turns", "calls", "cost", "uncached", "read", "out")
            }
            print(
                f"| {cond} | {d['num_turns']:+.2f} | {d['calls']:+.2f} | {d['cost']:+.3f} | "
                f"{d['uncached']:+,.0f} | {d['read']:+,.0f} | {d['out']:+,.0f} |"
            )
    print("\nPer phase, sessions that fired (mean per session):\n")
    print(
        "| cond | phase | API calls | uncached input | cache read | result tokens | carried "
        "(result × later calls) |\n|---|---|---:|---:|---:|---:|---:|"
    )
    for cond in ("R0", "R1", "R1s"):
        rs = [r for r in by_cond.get(cond, []) if r["fired"]]
        if not rs:
            continue
        n = len(rs)
        for ph in PHASES:
            c = sum(r["phase_calls"].get(ph, 0) for r in rs) / n
            if c:
                print(
                    f"| {cond} | {ph} | {c:.2f} | "
                    f"{sum(r['phase_uncached'].get(ph, 0) for r in rs) / n:,.0f} | "
                    f"{sum(r['phase_read'].get(ph, 0) for r in rs) / n:,.0f} | "
                    f"{sum(r['result_tokens'].get(ph, 0) for r in rs) / n:,.0f} | "
                    f"{sum(r['carried_tokens'].get(ph, 0) for r in rs) / n:,.0f} |"
                )
    grades = {}
    if grades_path:
        for g in (json.loads(x) for x in grades_path.read_text().splitlines() if x.strip()):
            grades[(g["task"], g["skill"])] = g["grade"]
    print("\nRank of the picked skills in the session's own search result (k = 50):\n")
    print(
        "| cond | picks | rank ≤ 10 | ≤ 20 | ≤ 30 | > 30 | > 30 and graded ≥ 2 | > 30 ungraded |"
        "\n|---|---:|---:|---:|---:|---:|---:|---:|"
    )
    for cond in ("R0", "R1", "R1s"):
        picks = [(x[0], r["task"], x[1]) for r in by_cond.get(cond, []) for x in r["picked_ranks"]]
        if picks:
            low = [(t, sid) for rank, t, sid in picks if rank > 30]
            print(
                f"| {cond} | {len(picks)} | {sum(p[0] <= 10 for p in picks)} | "
                f"{sum(p[0] <= 20 for p in picks)} | {sum(p[0] <= 30 for p in picks)} | "
                f"{len(low)} | {sum((grades.get(k) or 0) >= 2 for k in low)} | "
                f"{sum(k not in grades for k in low)} |"
            )
    print("\nFired sessions that loaded nothing (the router chain ran, no skill came in):\n")
    print(
        "| cond | fired | loaded nothing | by bundle | router calls (mean) | router-phase cache "
        "read + carried (mean) |\n|---|---:|---:|---|---:|---:|"
    )
    router_phases = [ph for ph in PHASES if ph not in ("pre", "work")]
    for cond in ("R0", "R1", "R1s"):
        rs = [r for r in by_cond.get(cond, []) if r["fired"]]
        none = [
            r for r in rs if not any(r["phase_calls"].get(p) for p in ("load", "resolve_and_load"))
        ]
        if rs and none:
            per_b = Counter(r["bundle"] for r in none)
            calls_ = statistics.mean(
                sum(r["phase_calls"].get(p, 0) for p in router_phases) for r in none
            )
            read = statistics.mean(
                sum(r["phase_read"].get(p, 0) for p in router_phases)
                + sum(r["carried_tokens"].values())
                for r in none
            )
            print(
                f"| {cond} | {len(rs)} | {len(none)} | "
                f"{', '.join(f'({b}) {n}' for b, n in sorted(per_b.items()))} | "
                f"{calls_:.2f} | {read:,.0f} |"
            )
    print("\nAPI calls outside the router phases vs A's calls on the same task (fired):\n")
    print("| cond | bundle | sessions | pre + work calls | A calls (median of task) | difference |")
    print("|---|---|---:|---:|---:|---:|")
    for cond in ("R0", "R1", "R1s"):
        for b in sorted({r["bundle"] for r in rows}):
            rs = [r for r in by_cond.get(cond, []) if r["fired"] and r["bundle"] == b]
            if rs:
                work = statistics.mean(
                    r["phase_calls"].get("pre", 0) + r["phase_calls"].get("work", 0) for r in rs
                )
                a = statistics.mean(a_med(r, "calls") for r in rs)
                print(f"| {cond} | {b} | {len(rs)} | {work:.2f} | {a:.2f} | {work - a:+.2f} |")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sessions")
    s.add_argument("runs", type=Path)
    s.add_argument("--out", type=Path)
    s.add_argument("--grades", type=Path, help="grades-s10.jsonl: (task, skill) -> grade")
    o = sub.add_parser("offline")
    o.add_argument("--index", type=Path, action="append", required=True)
    args = p.parse_args(argv)
    if args.cmd == "sessions":
        sessions(args.runs, args.out, args.grades)
    else:
        offline(args.index)
    return 0


K_VALUES = (10, 20, 30, 50)
SUMMARY_LIMITS = (160, 120, 80)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _wire_tokens(results: list[dict]) -> int:
    """search_skills' result as the server sends it (compact JSON), characters / 4."""
    return len(json.dumps({"results": results}, separators=(",", ":"), ensure_ascii=False)) // 4


def offline(indexes: list[Path]) -> None:
    from skillfetch.index.loader import Index
    from skillfetch.index.search import one_line
    from skillfetch.mcp.session import Session

    ev = ROOT / "evals" / "retrieval"
    tasks = {t["id"]: t for t in _jsonl(ev / "tasks.jsonl")}
    oracle = {o["id"]: o for o in _jsonl(ev / "oracle-v3.jsonl")}
    queries = _jsonl(ev / "queries-R-c.jsonl")
    sets = {"all": "relevant", "2a": "relevant_2a"}
    for index_dir in indexes:
        session = Session(Index.load(index_dir))
        full = {rid: r.get("summary", "") for rid, r in session.index.records.items()}
        print(f"\nIndex {index_dir.name}: R-c queries, oracle v3, {len(queries)} tasks\n")
        print(
            "| k | hit@k all | recall@k all | hit@k 2a | recall@k 2a | result tokens (summary "
            + " / ".join(f"{n}" for n in SUMMARY_LIMITS)
            + " chars), median |\n|---:|---:|---:|---:|---:|---|"
        )
        for k in K_VALUES:
            stats = {name: ([], []) for name in sets}
            sizes = {n: [] for n in SUMMARY_LIMITS}
            for q in queries:
                res = session.search_skills(queries=q["queries"], k=k)["results"]
                ids = [r["id"] for r in res]
                for n in SUMMARY_LIMITS:
                    cut = [{**r, "summary": one_line(full.get(r["id"], ""), n)} for r in res]
                    sizes[n].append(_wire_tokens(cut))
                t, o = tasks[q["id"]], oracle[q["id"]]
                for name, field in sets.items():
                    rel = o.get(field) or []
                    if t["expect_none"] or not rel:
                        continue
                    found = sum(1 for s in rel if s in ids)
                    stats[name][0].append(found > 0)
                    stats[name][1].append(found / len(rel))
            cells = []
            for name in sets:
                hits, recalls = stats[name]
                cells += [f"{sum(hits) / len(hits):.3f}", f"{sum(recalls) / len(recalls):.3f}"]
            size = " / ".join(f"{statistics.median(sizes[n]):,.0f}" for n in SUMMARY_LIMITS)
            print(f"| {k} | {' | '.join(cells)} | {size} |")
        n_all = sum(
            1 for q in queries if not tasks[q["id"]]["expect_none"] and oracle[q["id"]]["relevant"]
        )
        n_2a = sum(
            1
            for q in queries
            if not tasks[q["id"]]["expect_none"] and oracle[q["id"]]["relevant_2a"]
        )
        print(
            f"\n(tasks scored: all {n_all}, 2a {n_2a}; result tokens over all {len(queries)} tasks)"
        )


if __name__ == "__main__":
    sys.exit(main())
