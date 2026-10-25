#!/usr/bin/env python3
"""Stage 10 metrics and gate (DESIGN §3, §4). Main-run sessions only (tags m1-m3). Inputs: sessions-m1-m2-m3.jsonl,
grades-s10.jsonl, judge/scores-p1.jsonl, scores-p2.jsonl (and scores-gpt.jsonl when present), redacted/stats.json,
runs/*/*.meta.json (t115 check_original). Writes stage10-private/metrics-s10.json and prints markdown tables.
usage: metrics_s10.py"""
import json
import statistics
import sys
from pathlib import Path

S10 = Path(__file__).resolve().parents[1]
E2E = S10.parent
PRIV = E2E / "stage10-private"
sys.path.insert(0, str(E2E / "stage4" / "scripts"))
from eval_stage4 import SF, parse  # noqa: E402

rows = [json.loads(l) for l in (PRIV / "sessions-m1-m2-m3.jsonl").open()]
grade = {(g["task"], g["skill"]): g["grade"] for g in map(json.loads, (PRIV / "grades-s10.jsonl").open())}
passes = {}
for p in ("p1", "p2", "gpt"):
    f = PRIV / "judge" / f"scores-{p}.jsonl"
    if f.exists():
        passes[p] = {(s["task"], s["env"], s["cond"], s["tag"]): s for s in map(json.loads, f.open())}
CELLS = [("E1", "A"), ("E1", "R0"), ("E1", "R1"), ("E1", "R1s"), ("E2", "A"), ("E2", "R1")]
BUNDLES = (1, 2, 3, 4)
med = lambda xs: statistics.median(xs) if xs else None  # noqa: E731
mean = lambda xs: round(statistics.mean(xs), 3) if xs else None  # noqa: E731

for r in rows:  # skillfetch call turns (first .. last) from the raw stream
    f = PRIV / "runs" / r["env"] / r["cond"] / f"{r['task']}-{r['tag']}.jsonl"
    _, _, _, calls, _, _ = parse(f)
    t = [c["turn"] for c in calls if c["name"].startswith(SF)]
    r["sf_span"] = (max(t) - min(t) + 1) if t else 0
    r["relevant_load"] = any(grade.get((r["task"], s), 0) >= 2 for s in r["loaded"])
    r["loaded_grades"] = [grade.get((r["task"], s)) for s in r["loaded"]]
    m = json.loads(Path(str(f)[:-6] + ".meta.json").read_text())
    r["check_pass"] = m["check"].get("pass")
    r["check_pass_original"] = m.get("check_original", m["check"]).get("pass")


def cell(env, cond, b):
    return [r for r in rows if r["env"] == env and r["cond"] == cond and r["bundle"] == b]


def score(p, env, cond, b, key="score"):
    return mean([passes[p][(r["task"], r["env"], r["cond"], r["tag"])][key] for r in cell(env, cond, b)
                 if (r["task"], r["env"], r["cond"], r["tag"]) in passes.get(p, {})])


M = {"cells": {}, "D": {}, "gate": {}, "r1_vs_a": {}, "r1s_vs_r1": {}}
for b in BUNDLES:
    for env, cond in CELLS:
        g = cell(env, cond, b)
        sc = {p: score(p, env, cond, b) for p in passes}
        M["cells"][f"b{b} {env} {cond}"] = {
            "n": len(g), "fired": sum(r["fired"] for r in g), "loaded_any": sum(bool(r["loaded"]) for r in g),
            "relevant_load": sum(r["relevant_load"] for r in g), "check_pass": sum(bool(r["check_pass"]) for r in g),
            "check_pass_original": sum(bool(r["check_pass_original"]) for r in g),
            "turns_med": med([r["turns"] for r in g]), "input_tokens_med": med([r["input_tokens"] for r in g]),
            "cost_med": round(med([r["cost_usd"] for r in g]), 3), "cost_sum": round(sum(r["cost_usd"] for r in g), 2),
            "first_search_turn_med": med([r["first_search_turn"] for r in g if r["first_search_turn"]]),
            "sf_span_med": med([r["sf_span"] for r in g if r["sf_span"]]),
            "score": sc, "score_claude": round((sc["p1"] + sc["p2"]) / 2, 3) if sc.get("p1") is not None and sc.get("p2") is not None else None,
            "ai_look": {p: score(p, env, cond, b, "ai_look") for p in passes} if b == 1 else None}
    gc = ("A", "R0", "R1")
    dcl = max(abs(score("p1", "E1", c, b) - score("p2", "E1", c, b)) for c in gc) if "p2" in passes else None
    dg = None
    if "gpt" in passes:
        pairs = [("p1", "p2"), ("p1", "gpt"), ("p2", "gpt")]
        dg = max(abs(score(x, "E1", c, b) - score(y, "E1", c, b)) for x, y in pairs for c in gc)
    M["D"][f"b{b}"] = {"claude": round(dcl, 3) if dcl is not None else None, "gpt": round(dg, 3) if dg is not None else None}

c = lambda b, cond, env="E1": M["cells"][f"b{b} {env} {cond}"]  # noqa: E731
gi = c(4, "R1")["relevant_load"] > c(4, "R0")["relevant_load"]
gii_claude = {f"b{b}": c(b, "R1")["score_claude"] >= c(b, "R0")["score_claude"] - M["D"][f"b{b}"]["claude"] for b in BUNDLES}
gii_gpt = {f"b{b}": (c(b, "R1")["score"]["gpt"] >= c(b, "R0")["score"]["gpt"] - M["D"][f"b{b}"]["gpt"]) if "gpt" in passes else None
           for b in BUNDLES}
giii = c(3, "R1")["loaded_any"] <= c(3, "R0")["loaded_any"] + 1
giv = {f"b{b}": c(b, "R1")["turns_med"] <= c(b, "R0")["turns_med"] + 2 for b in BUNDLES}
M["gate"] = {"i": {"R1": c(4, "R1")["relevant_load"], "R0": c(4, "R0")["relevant_load"], "pass": gi},
             "ii_claude": gii_claude, "ii_gpt": gii_gpt,
             "iii": {"R1": c(3, "R1")["loaded_any"], "R0": c(3, "R0")["loaded_any"], "pass": giii}, "iv": giv}
for b in BUNDLES:
    d = round(c(b, "R1")["score_claude"] - c(b, "A")["score_claude"], 3)
    M["r1_vs_a"][f"b{b}"] = {"claude_diff": d, "within_D": abs(d) <= M["D"][f"b{b}"]["claude"]}
    d2 = round(c(b, "R1s")["score_claude"] - c(b, "R1")["score_claude"], 3)
    M["r1s_vs_r1"][f"b{b}"] = {"claude_diff": d2, "within_D": abs(d2) <= M["D"][f"b{b}"]["claude"]}
M["redaction"] = json.loads((PRIV / "redacted" / "stats.json").read_text())["by_condition"]
(PRIV / "metrics-s10.json").write_text(json.dumps(M, indent=1, ensure_ascii=False))

hdr = "| 묶음 | 환경 | 조건 | n | 발화 | 로드≥1 | 관련 로드 | 체크 통과 | 중앙 턴 | 중앙 입력 토큰 | 중앙 비용 | p1 | p2 | (p1+p2)/2 |"
print(hdr)
print("|" + "---|" * (hdr.count("|") - 1))
for k, v in M["cells"].items():
    b, env, cond = k.split()
    print(f"| {b[1]} | {env} | {cond} | {v['n']} | {v['fired']} | {v['loaded_any']} | {v['relevant_load']} | {v['check_pass']} | "
          f"{v['turns_med']} | {v['input_tokens_med']:,.0f} | ${v['cost_med']} | {v['score'].get('p1')} | {v['score'].get('p2')} | {v['score_claude']} |")
print(json.dumps({"D": M["D"], "gate": M["gate"], "r1_vs_a": M["r1_vs_a"], "r1s_vs_r1": M["r1s_vs_r1"]}, indent=1))
