#!/usr/bin/env python3
"""Stage 14 numbers (DESIGN §5, §9): joins stage14-private/judge/scores-p1.jsonl, scores-p2.jsonl with usage-14.json.
Score per output = (p1 + p2) / 2.
  (i)   six-task mean R − P       (ii) six-task mean R − A
  (iii) R − P over requests right after a domain change (F: positions 2 4 5 6; B: 2 3 4 6)
  (iv)  session mean API-price equivalent per condition; (R − P) / (cost R − cost P) and (R − A) / (cost R − cost A)
  D = max(per condition mean |p1 − p2|, 0.25); a difference with |diff| <= D is labelled "판정 노이즈 안" (not a gate).
Also: per order, per task, per judge, checks, turns, context at the start, 40-turn limit hits, skills, traces (a)(b),
mutants caught. Writes stage14-private/metrics-14.json and prints a summary.
usage: metrics_14.py"""
import json
import statistics as st
from pathlib import Path

S14 = Path(__file__).resolve().parents[1]
PRIV = S14.parent / "stage14-private"
TASKS = ["landing", "api", "apitests", "rust", "docs", "data"]
C = ("A", "P", "R")


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 3) if xs else None


def main():
    sc = {}
    for pas in ("p1", "p2"):
        for line in (PRIV / "judge" / f"scores-{pas}.jsonl").open():
            r = json.loads(line)
            sc.setdefault((r["cond"], r["order"], r["tag"], r["task"]), {})[pas] = r
    rows = json.loads((PRIV / "usage-14.json").read_text())
    for r in rows:
        s = sc[(r["cond"], r["order"], r["tag"], r["task"])]
        r["p1"], r["p2"] = s["p1"]["score"], s["p2"]["score"]
        r["score"] = (r["p1"] + r["p2"]) / 2
        r["ai_look"] = [s["p1"].get("ai_look"), s["p2"].get("ai_look")]
        r["reason_p1"], r["reason_p2"] = s["p1"].get("reason", ""), s["p2"].get("reason", "")
    by = lambda c, f=lambda r: True: [r for r in rows if r["cond"] == c and f(r)]  # noqa: E731
    gap = {c: mean([abs(r["p1"] - r["p2"]) for r in by(c)]) for c in C}
    D = max(max(gap.values()), 0.25)

    def diff(a, b, f=lambda r: True, key="score"):
        x, y = mean([r[key] for r in by(a, f)]), mean([r[key] for r in by(b, f)])
        d = round(x - y, 3)
        return {"a": x, "b": y, "diff": d, "noise": abs(d) <= D}
    dc = lambda r: r["after_domain_change"]  # noqa: E731
    sess = {}
    for r in rows:
        sess.setdefault((r["cond"], r["order"]), []).append(r)
    cost = {c: mean([sum(x["cost"] for x in v) for (cc, o), v in sess.items() if cc == c]) for c in C}
    crit = {"i_R_minus_P": diff("R", "P"), "ii_R_minus_A": diff("R", "A"), "iii_R_minus_P_after_domain_change": diff("R", "P", dc),
            "iii_ref_R_minus_A_after_domain_change": diff("R", "A", dc)}
    eff = {}
    for b in ("P", "A"):
        dcost = round(cost["R"] - cost[b], 3)
        d = crit["i_R_minus_P" if b == "P" else "ii_R_minus_A"]["diff"]
        eff[f"R_vs_{b}"] = {"score_diff": d, "cost_diff_per_session": dcost,
                             "score_per_dollar": round(d / dcost, 4) if dcost > 0 else "R이 같거나 더 적은 비용"}
    out = {
        "D": D, "judge_gap": gap, "criteria": crit, "cost_session_mean": cost, "efficiency": eff,
        "per_order": {o: {"R_minus_P": diff("R", "P", lambda r, o=o: r["order"] == o), "R_minus_A": diff("R", "A", lambda r, o=o: r["order"] == o)} for o in "FB"},
        "per_judge": {p: {"R_minus_P": diff("R", "P", key=p), "R_minus_A": diff("R", "A", key=p)} for p in ("p1", "p2")},
        "per_task": {t: {c: {"score": mean([r["score"] for r in by(c, lambda r, t=t: r["task"] == t)]),
                             "check": sum(r["check"] is True for r in by(c, lambda r, t=t: r["task"] == t)),
                             "turns": [r["turns"] for r in by(c, lambda r, t=t: r["task"] == t)],
                             "cost": [round(r["cost"], 2) for r in by(c, lambda r, t=t: r["task"] == t)],
                             "skills": [r["skills"] for r in by(c, lambda r, t=t: r["task"] == t)]} for c in C} for t in TASKS},
        "per_condition": {c: {"score": mean([r["score"] for r in by(c)]), "checks": f"{sum(r['check'] is True for r in by(c))}/{len(by(c))}",
                              "max_turns_hits": sum(r["result"] == "error_max_turns" for r in by(c)),
                              "turns_session": [sum(x["turns"] or 0 for x in v) for (cc, o), v in sorted(sess.items()) if cc == c],
                              "cost_session": [round(sum(x["cost"] for x in v), 2) for (cc, o), v in sorted(sess.items()) if cc == c],
                              "context_start_by_position": {k: [r["context_start"] for r in by(c, lambda r, k=k: r["k"] == k)] for k in range(1, 7)},
                              "requests_with_skill": sum(bool(r["skills"]) for r in by(c)),
                              "trace_a_names": sum(bool(r["trace_names"]) for r in by(c)),
                              "trace_a_not_reloaded": sum(bool(r["trace_names_not_reloaded"]) for r in by(c)),
                              "trace_b_out_of_area": sum(bool(r["out_of_area"]) for r in by(c)),
                              "mutants_killed": [r["mutants_killed"] for r in by(c, lambda r: r["task"] == "apitests")]} for c in C},
        "rows": rows,
    }
    (PRIV / "metrics-14.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("D", D, "gap", gap)
    for k, v in crit.items():
        print(k, v)
    print("cost", cost, "eff", eff)
    for c in C:
        x = out["per_condition"][c]
        print(c, {k: x[k] for k in ("score", "checks", "max_turns_hits", "cost_session", "requests_with_skill", "trace_a_names", "trace_a_not_reloaded", "trace_b_out_of_area", "mutants_killed")})
    for t in TASKS:
        print(t, {c: out["per_task"][t][c]["score"] for c in C})


if __name__ == "__main__":
    main()
