#!/usr/bin/env python3
"""Stage 12/12b input tokens and turns per condition (stage12b/DESIGN.md §4): from each session's result event,
input = input_tokens + cache_read_input_tokens + cache_creation_input_tokens; median and mean, median num_turns, mean
total_cost_usd. usage: tokens_12.py <tag-prefix> <cond> [...]"""
import json
import statistics as st
import sys
from pathlib import Path

PRIV = Path(__file__).resolve().parents[2] / "stage12-private"


def result(jsonl):
    ev = None
    for line in Path(jsonl).open(errors="replace"):
        if '"type":"result"' in line.replace(" ", ""):
            try:
                ev = json.loads(line)
            except ValueError:
                pass
    return ev


out = {}
prefix = sys.argv[1]
for cond in sys.argv[2:]:
    evs = [result(f) for f in sorted((PRIV / "runs" / cond).glob(f"*-{prefix}*.jsonl"))
           if not f.name.endswith((".p1.jsonl", ".p2.jsonl"))]
    evs = [e for e in evs if e]
    tok = [sum((e.get("usage") or {}).get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens",
                                                             "cache_creation_input_tokens")) for e in evs]
    out[cond] = {"sessions": len(evs), "input_median": int(st.median(tok)), "input_mean": int(st.mean(tok)),
                 "turns_median": st.median(e.get("num_turns") or 0 for e in evs),
                 "cost_mean": round(st.mean(e.get("total_cost_usd") or 0 for e in evs), 3)}
print(json.dumps(out, indent=1))
