#!/usr/bin/env python3
"""Stage 11 gate (DESIGN §4, fixed before the run) from stage11-private/sessions-<tags>.jsonl (main run m1–m6),
grades-s11.jsonl and judge/scores-{p1,p2,gpt}.jsonl. Writes stage11-private/metrics-s11.json.

  (i)   bundle (4) relevant-load rate: R1 > R0 (sessions loading >= 1 skill of grade >= 2 / sessions, 30 each)
  (ii)  every bundle: R1 >= R0 - D, per judge.
        Claude: condition score = mean over sessions of (p1 + p2) / 2;
                D_claude(b) = max(max over c in {R0, R1} |mean_p1(c, b) - mean_p2(c, b)|, 0.25)
        GPT:    condition score = mean GPT score;
                D_gpt(b) = max(max over pairs x, y in {p1, p2, gpt}, c in {R0, R1} |mean_x(c, b) - mean_y(c, b)|, 0.25)
        A is not used for D. Reference line (not the verdict, DESIGN §4): the same with the 0.25 floor removed.
  (iii) bundle (3) unneeded loads: R1 <= R0 + 2 (sessions loading >= 1 skill, any grade, of 18)
  (iv)  every bundle: median turns R1 <= R0 + 2
  Release only if all four hold. Report only: bundle (4) A vs R0 / R1 (score, turns, cost), bundle (3) grades of the
  loaded skills, judge agreement (same score, difference <= 1), checks incl. undecidable (s11-t266).
usage: metrics_s11.py <sessions.jsonl>"""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

PRIV = Path(__file__).resolve().parents[2] / "stage11-private"
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
rows = [r for r in rows if r["tag"].startswith("m") and not r.get("harness_fail")]
grade = {(g["task"], g["skill"]): g["grade"] for g in map(json.loads, (PRIV / "grades-s11.jsonl").open())}
passes = {}
for p in ("p1", "p2", "gpt"):
    f = PRIV / "judge" / f"scores-{p}.jsonl"
    if f.exists():
        passes[p] = {(s["task"], s["cond"], s["tag"]): s["score"] for s in map(json.loads, f.open())}
FLOOR = 0.25


def cell(b, c):
    return [r for r in rows if r["bundle"] == b and r["cond"] == c]


def mean_pass(p, b, c):
    v = [passes[p][(r["task"], r["cond"], r["tag"])] for r in cell(b, c) if (r["task"], r["cond"], r["tag"]) in passes.get(p, {})]
    return statistics.mean(v) if v else None


def relevant(r):
    return any(grade.get((r["task"], s), 0) >= 2 for s in r["loaded"])


cells = {}
for b in (1, 2, 3, 4):
    for c in ("A", "R0", "R1"):
        x = cell(b, c)
        if not x:
            continue
        sc = {p: mean_pass(p, b, c) for p in passes}
        cells[f"b{b} {c}"] = {
            "n": len(x), "fired": sum(r["fired"] for r in x), "loaded_any": sum(bool(r["loaded"]) for r in x),
            "relevant_load": sum(relevant(r) for r in x), "check_pass": sum(r["check_pass"] is True for r in x),
            "check_fail": sum(r["check_pass"] is False for r in x), "check_undecidable": sum(r["check_pass"] is None for r in x),
            "turns_med": statistics.median(r["turns"] for r in x), "input_tokens_med": statistics.median(r["input_tokens"] for r in x),
            "cost_med": round(statistics.median(r["cost_usd"] for r in x), 3), "cost_sum": round(sum(r["cost_usd"] for r in x), 2),
            "wall_med": statistics.median(r["wall_s"] for r in x),
            "score": {p: (round(v, 3) if v is not None else None) for p, v in sc.items()},
            "score_claude": round((sc["p1"] + sc["p2"]) / 2, 3) if sc.get("p1") is not None and sc.get("p2") is not None else None}


def d_raw(b):
    out = {}
    if "p1" in passes and "p2" in passes:
        out["claude"] = max(abs(mean_pass("p1", b, c) - mean_pass("p2", b, c)) for c in ("R0", "R1"))
    if all(p in passes for p in ("p1", "p2", "gpt")):
        out["gpt"] = max(abs(mean_pass(x, b, c) - mean_pass(y, b, c)) for x, y in (("p1", "p2"), ("p1", "gpt"), ("p2", "gpt"))
                         for c in ("R0", "R1"))
    return out


gate, ref = {"ii_claude": {}, "ii_gpt": {}, "iv": {}}, {"ii_claude": {}, "ii_gpt": {}}
D = {}
for b in (1, 2, 3, 4):
    r0, r1 = cells[f"b{b} R0"], cells[f"b{b} R1"]
    raw = d_raw(b)
    D[f"b{b}"] = {k: {"raw": round(v, 3), "floored": round(max(v, FLOOR), 3)} for k, v in raw.items()}
    if "claude" in raw:
        gate["ii_claude"][f"b{b}"] = r1["score_claude"] >= r0["score_claude"] - max(raw["claude"], FLOOR)
        ref["ii_claude"][f"b{b}"] = r1["score_claude"] >= r0["score_claude"] - raw["claude"]
    if "gpt" in raw:
        gate["ii_gpt"][f"b{b}"] = r1["score"]["gpt"] >= r0["score"]["gpt"] - max(raw["gpt"], FLOOR)
        ref["ii_gpt"][f"b{b}"] = r1["score"]["gpt"] >= r0["score"]["gpt"] - raw["gpt"]
    gate["iv"][f"b{b}"] = r1["turns_med"] <= r0["turns_med"] + 2
gate["i"] = cells["b4 R1"]["relevant_load"] > cells["b4 R0"]["relevant_load"]
gate["iii"] = cells["b3 R1"]["loaded_any"] <= cells["b3 R0"]["loaded_any"] + 2
complete = "gpt" in passes and "p1" in passes and "p2" in passes


def verdict(g):
    items = [g["i"], all(g["ii_claude"].values()), all(g["ii_gpt"].values()) if complete else None, g["iii"], all(g["iv"].values())]
    return None if None in items else all(items)


agree = {}
if "p1" in passes and "p2" in passes:
    ks = [k for k in passes["p1"] if k in passes["p2"]]
    agree["p1_p2"] = {"same": sum(passes["p1"][k] == passes["p2"][k] for k in ks), "within1": sum(abs(passes["p1"][k] - passes["p2"][k]) <= 1 for k in ks), "n": len(ks)}
if "gpt" in passes:
    for p in ("p1", "p2"):
        ks = [k for k in passes[p] if k in passes["gpt"]]
        agree[f"{p}_gpt"] = {"same": sum(passes[p][k] == passes["gpt"][k] for k in ks), "within1": sum(abs(passes[p][k] - passes["gpt"][k]) <= 1 for k in ks), "n": len(ks)}
b3_grades = Counter(grade.get((r["task"], s)) for r in rows if r["bundle"] == 3 for s in r["loaded"])
out = {"sessions": len(rows), "cells": cells, "D": D,
       "gate": {**gate, "pass": verdict(gate), "complete": complete},
       "reference_no_floor": {"ii_claude": ref["ii_claude"], "ii_gpt": ref["ii_gpt"],
                              "pass": verdict({**gate, "ii_claude": ref["ii_claude"], "ii_gpt": ref["ii_gpt"]})},
       "report_only": {"b3_loaded_grade_distribution": {str(k): v for k, v in b3_grades.items()}, "judge_agreement": agree}}
(PRIV / "metrics-s11.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({"gate": out["gate"], "reference_no_floor": out["reference_no_floor"], "D": D}, indent=1))
