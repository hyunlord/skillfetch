#!/usr/bin/env python3
"""Stage 13 per-task numbers for A (off), P, R (on), m1–m3 (stage13/DESIGN.md §3): check pass (the task's own check),
added test functions (added diff lines matching a test definition: Python `def test_`, Rust `#[test]`/`#[tokio::test]`,
Go `func Test`, Java `@Test`, Swift `func test`, JS/TS `it(`/`test(`; one rule for all conditions), median turns, mean
API-price equivalent, median input tokens (input + cache read + cache creation). -> stage13-private/metrics-13.json
usage: metrics_13.py"""
import json
import re
import statistics as st
import sys
from pathlib import Path

S13 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S13 / "scripts"))
from build_blind_13 import TASKS, source  # noqa: E402

TEST = re.compile(r"^\+\s*(?:async\s+)?(?:def test_\w+|#\[(?:tokio::)?test\]|func Test\w+|@Test\b|func test\w+|(?:it|test)\(\s*['\"`])")


def result(jsonl):
    ev = None
    for line in Path(jsonl).open(errors="replace"):
        if '"type":"result"' in line.replace(" ", ""):
            try:
                ev = json.loads(line)
            except ValueError:
                pass
    return ev or {}


out = {}
for t in TASKS:
    for c in ("A", "P", "R"):
        rows = []
        for k in (1, 2, 3):
            b = source(t, c, f"m{k}")
            m = json.loads(Path(str(b) + ".meta.json").read_text())
            ev = result(str(b) + ".jsonl")
            u = ev.get("usage") or {}
            diff = Path(str(b) + ".diff").read_text(errors="replace") if Path(str(b) + ".diff").exists() else ""
            rows.append({"check": (m.get("check") or {}).get("pass"), "turns": ev.get("num_turns"),
                         "cost": ev.get("total_cost_usd") or m.get("cost_usd") or 0,
                         "tokens": sum(u.get(x) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                         "tests": sum(bool(TEST.match(l)) for l in diff.splitlines())})
        out[f"{t} {c}"] = {"check": f"{sum(r['check'] is True for r in rows)}/3", "turns_median": st.median(r["turns"] or 0 for r in rows),
                           "cost_mean": round(st.mean(r["cost"] for r in rows), 3), "tokens_median": int(st.median(r["tokens"] for r in rows)),
                           "tests_mean": round(st.mean(r["tests"] for r in rows), 1)}
(S13.parent / "stage13-private" / "metrics-13.json").write_text(json.dumps(out, indent=1))
for t in TASKS:
    print(t.ljust(13), " | ".join(f"{c}: chk {out[f'{t} {c}']['check']} t{out[f'{t} {c}']['turns_median']} ${out[f'{t} {c}']['cost_mean']} tests {out[f'{t} {c}']['tests_mean']}" for c in "APR"))
for c in "APR":
    v = [out[f"{t} {c}"] for t in TASKS]
    print(c, "checks", sum(int(x["check"][0]) for x in v), "/54", "cost mean", round(st.mean(x["cost_mean"] for x in v), 3))
