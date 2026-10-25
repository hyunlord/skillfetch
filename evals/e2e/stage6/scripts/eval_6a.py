#!/usr/bin/env python3
"""Metrics for the selection candidates (select-<C>.jsonl) against oracle v4 (oracle-v4.jsonl; v3 shown too).
Coverage tasks = relevant set non-empty and not expect_none. precision (tasks with picks), recall, hit; none accuracy on
tasks with no relevant skill (oracle base) and on the 40 expect_none tasks; over-load = picks on a no-relevant task;
wrong loads = picks graded < 2; pairs: 'moved with the direction' as in stage3/scripts/eval_selection.py; process picks
(kind.jsonl) on directive tasks and on the rest. Writes eval-6a.json and eval-6a-rows.jsonl."""
import json
from collections import Counter
from pathlib import Path

S6 = Path(__file__).resolve().parents[1]
CANDS = ["S-0", "S-a", "S-b", "S-c"]
tasks = {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "tasks.jsonl").open()}
kind = {json.loads(l)["id"]: json.loads(l)["kind"] for l in (S6 / "kind.jsonl").open()}
ORC = {"v4": {json.loads(l)["id"]: json.loads(l) for l in (S6 / "oracle-v4.jsonl").open()},
       "v3": {json.loads(l)["id"]: json.loads(l) for l in (S6.parent / "stage3" / "followup" / "oracle-v3.jsonl").open()}}
mean = lambda v: round(sum(v) / len(v), 3) if v else None  # noqa: E731


def evaluate(sel, orc):
    rows = []
    for tid, t in tasks.items():
        S, R = set(sel[tid]), set(orc[tid]["relevant"])
        grade = {x["skill"]: x["grade"] for x in orc[tid]["pool"]}
        rows.append({"id": tid, "S": sorted(S), "R": sorted(R), "expect_none": t["expect_none"], "phrasing": t["phrasing"],
                     "direction": t.get("direction"), "pair_id": t["pair_id"], "pair_side": t.get("pair_side"),
                     "wrong": sorted(s for s in S if grade.get(s, 0) < 2), "proc_pick": [s for s in S if kind.get(s) == "process"]})
    cov = [r for r in rows if r["R"] and not r["expect_none"]]
    nor = [r for r in rows if not r["R"]]
    en = [r for r in rows if r["expect_none"]]
    pairs = {}
    for r in rows:
        if r["pair_id"]:
            pairs.setdefault(r["pair_id"], {})[r["pair_side"]] = r
    changed = moved = 0
    for p in pairs.values():
        a, b = p["a"], p["b"]
        Sa, Sb, Ra, Rb = set(a["S"]), set(b["S"]), set(a["R"]), set(b["R"])
        if Sa != Sb:
            changed += 1
            ea, eb = Sa - Sb, Sb - Sa
            moved += bool((ea | eb) and all(s in Ra for s in ea) and all(s in Rb for s in eb)
                          and not any(s in Rb and s not in Ra for s in ea) and not any(s in Ra and s not in Rb for s in eb))
    dirt = [r for r in rows if r["phrasing"] == "directive" and not r["expect_none"]]
    rest = [r for r in rows if r["phrasing"] != "directive" and not r["expect_none"]]
    return rows, {
        "coverage_tasks": len(cov), "precision": mean([len(set(r["S"]) & set(r["R"])) / len(r["S"]) for r in cov if r["S"]]),
        "recall": mean([len(set(r["S"]) & set(r["R"])) / len(r["R"]) for r in cov]),
        "hit": mean([1.0 if set(r["S"]) & set(r["R"]) else 0.0 for r in cov]),
        "none_cov": sum(not r["S"] for r in cov),
        "none_acc_oracle": mean([1.0 if not r["S"] else 0.0 for r in nor]), "no_relevant_tasks": len(nor),
        "none_acc_expect_none": mean([1.0 if not r["S"] else 0.0 for r in en]), "expect_none_tasks": len(en),
        "over_load_tasks": sum(1 for r in nor if r["S"]), "wrong_loads": sum(len(r["wrong"]) for r in rows),
        "mean_loaded": mean([len(r["S"]) for r in rows]), "none_total": sum(not r["S"] for r in rows),
        "pairs_changed": changed, "pairs_moved": moved, "pairs": len(pairs),
        "directive_tasks": len(dirt), "directive_with_process_pick": sum(bool(r["proc_pick"]) for r in dirt),
        "directive_process_pick_relevant": sum(any(s in r["R"] for s in r["proc_pick"]) for r in dirt),
        "nondirective_tasks": len(rest), "nondirective_with_process_pick": sum(bool(r["proc_pick"]) for r in rest),
        "picked_kinds": dict(Counter(kind.get(s, "?") for r in rows for s in r["S"]))}


sels = {c: {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S6 / f"select-{c}.jsonl").open()} for c in CANDS}
out, allrows = {}, []
for v, orc in ORC.items():
    out[v] = {}
    for c in CANDS:
        rows, m = evaluate(sels[c], orc)
        out[v][c] = m
        if v == "v4":
            allrows += [dict(r, cand=c) for r in rows]
base = out["v4"]["S-0"]["hit"]
out["verdict"] = {c: {"none_acc_oracle>=0.85": out["v4"][c]["none_acc_oracle"] >= 0.85,
                      "none_acc_expect_none>=0.85": out["v4"][c]["none_acc_expect_none"] >= 0.85,
                      "hit_drop<=0.05": round(base - out["v4"][c]["hit"], 3) <= 0.05, "hit_drop": round(base - out["v4"][c]["hit"], 3),
                      "pairs>=15": out["v4"][c]["pairs_moved"] >= 15} for c in CANDS}
(S6 / "eval-6a.json").write_text(json.dumps(out, indent=1))
(S6 / "eval-6a-rows.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in allrows))
for c in CANDS:
    print(c, {k: out["v4"][c][k] for k in ("precision", "recall", "hit", "none_acc_oracle", "none_acc_expect_none", "over_load_tasks", "pairs_moved", "mean_loaded", "directive_with_process_pick")}, out["verdict"][c])
