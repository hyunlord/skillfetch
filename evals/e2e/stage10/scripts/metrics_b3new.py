#!/usr/bin/env python3
"""DESIGN §11 re-measurement of bundle (3): tasks-b3new.jsonl × {R0, R1, R1s} × E1 × n1-n3.
Gate items for bundle (3) (§11.1: they replace the bundle (3) items of (ii), (iii), (iv); other bundles keep the main
run): (ii) R1 >= R0 - D per judge with D over {R0, R1} (Claude: max |mean_p1 - mean_p2|; GPT: max over pass pairs of
{p1n, p2n, gptn}); (iii) sessions with >=1 loaded skill R1 <= R0 + 1; (iv) median turns R1 <= R0 + 2.
Also §4.5 (b)/(c) for R1s on the new bundle (3), and the recomputed full gate with the main-run bundles (1), (2), (4).
Writes stage10-private/metrics-b3new.json. usage: metrics_b3new.py"""
import json
import statistics
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
PRIV = S10.parent / "stage10-private"
rows = [json.loads(l) for l in (PRIV / "sessions-n1-n2-n3.jsonl").open()]
grade = {(g["task"], g["skill"]): g["grade"] for g in map(json.loads, (PRIV / "grades-b3new.jsonl").open())}
passes = {}
for p in ("p1n", "p2n", "gptn"):
    f = PRIV / "judge" / f"scores-{p}.jsonl"
    if f.exists():
        passes[p] = {(s["task"], s["cond"], s["tag"]): s["score"] for s in map(json.loads, f.open())}
CONDS = ("R0", "R1", "R1s")


def g(cond):
    return [r for r in rows if r["cond"] == cond]


def sc(p, cond):
    v = [passes[p][(r["task"], r["cond"], r["tag"])] for r in g(cond) if (r["task"], r["cond"], r["tag"]) in passes.get(p, {})]
    return round(statistics.mean(v), 3) if v else None


cells = {}
for c in CONDS:
    x = g(c)
    cells[c] = {"n": len(x), "fired": sum(r["fired"] for r in x), "loaded_any": sum(bool(r["loaded"]) for r in x),
                "relevant_load": sum(any(grade.get((r["task"], s), 0) >= 2 for s in r["loaded"]) for r in x),
                "check_pass": sum(bool(r["check_pass"]) for r in x), "turns_med": statistics.median(r["turns"] for r in x),
                "input_tokens_med": statistics.median(r["input_tokens"] for r in x),
                "cost_med": round(statistics.median(r["cost_usd"] for r in x), 3), "cost_sum": round(sum(r["cost_usd"] for r in x), 2),
                "score": {p: sc(p, c) for p in passes}}
    s = cells[c]["score"]
    cells[c]["score_claude"] = round((s["p1n"] + s["p2n"]) / 2, 3) if s.get("p1n") is not None and s.get("p2n") is not None else None
D = {"claude": round(max(abs(sc("p1n", c) - sc("p2n", c)) for c in ("R0", "R1")), 3) if "p2n" in passes else None,
     "gpt": round(max(abs(sc(x, c) - sc(y, c)) for x, y in (("p1n", "p2n"), ("p1n", "gptn"), ("p2n", "gptn")) for c in ("R0", "R1")), 3)
     if "gptn" in passes else None}
b3 = {"ii_claude": (cells["R1"]["score_claude"] >= cells["R0"]["score_claude"] - D["claude"]) if D["claude"] is not None else None,
      "ii_gpt": (cells["R1"]["score"]["gptn"] >= cells["R0"]["score"]["gptn"] - D["gpt"]) if D["gpt"] is not None else None,
      "iii": cells["R1"]["loaded_any"] <= cells["R0"]["loaded_any"] + 1,
      "iv": cells["R1"]["turns_med"] <= cells["R0"]["turns_med"] + 2}
r1s = {"b_claude": (cells["R1s"]["score_claude"] >= cells["R1"]["score_claude"] - D["claude"]) if D["claude"] is not None else None,
       "b_gpt": (cells["R1s"]["score"]["gptn"] >= cells["R1"]["score"]["gptn"] - D["gpt"]) if D["gpt"] is not None else None,
       "c": cells["R1s"]["loaded_any"] <= cells["R1"]["loaded_any"] + 1}
main = json.loads((PRIV / "metrics-s10.json").read_text())["gate"]
full = {"i": main["i"]["pass"],
        "ii_claude": all(v for k, v in main["ii_claude"].items() if k != "b3") and b3["ii_claude"],
        "ii_gpt": (all(v for k, v in main["ii_gpt"].items() if k != "b3") and b3["ii_gpt"]) if b3["ii_gpt"] is not None else None,
        "iii": b3["iii"], "iv": all(v for k, v in main["iv"].items() if k != "b3") and b3["iv"]}
full["pass"] = all(v for v in full.values()) if None not in full.values() else None
out = {"cells": cells, "D": D, "b3_gate_items": b3, "r1s_b3": r1s, "gate_recomputed": full}
(PRIV / "metrics-b3new.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
