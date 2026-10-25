#!/usr/bin/env python3
"""Step 4 metrics: selection.jsonl vs oracle (v2). Writes selection-eval.jsonl (per task) and selection-summary.json.

Per task (S = selected set, R = oracle relevant set, grade >= 2):
  precision |S∩R|/|S| (tasks with S non-empty and R non-empty), recall |S∩R|/|R| (tasks with R non-empty, not expect_none)
  wrong_loads = skills in S with grade < 2 or not in the pool
Failure class (one per task):
  R empty     -> over_load if S non-empty, else ok
  S∩R ≠ ∅     -> ok
  some r∈R in Q2 top-50                       -> select_fail
  else some r∈R in Q1 or Q3 top-50            -> restate_fail
  else                                        -> search_fail
None accuracy, two bases: oracle (R empty, incl. tasks without coverage) and expect_none (the 40 trivial tasks).
Pairs: set changed between the two directions; 'moved with the direction' = changed, and each side's extra skills are
relevant to that side and none of them is relevant only to the other side."""
import json
from collections import Counter, defaultdict
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]


def main():
    tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
    orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
    sel = {json.loads(l)["id"]: json.loads(l)["skills"] for l in (S3 / "selection.jsonl").open()}
    rk = json.loads((S3 / "rankings.json").read_text())
    rows = []
    for tid, t in tasks.items():
        S, R = set(sel[tid]), set(orc[tid]["relevant"])
        grade = {x["skill"]: x["grade"] for x in orc[tid]["pool"]}
        inq = {q: bool(R & set(rk[tid][m])) for q, m in (("q1", "bm25_q1"), ("q2", "bm25_q2"), ("q3", "bm25_q3"))}
        if not R:
            cls = "over_load" if S else "ok"
        elif S & R:
            cls = "ok"
        elif inq["q2"]:
            cls = "select_fail"
        elif inq["q1"] or inq["q3"]:
            cls = "restate_fail"
        else:
            cls = "search_fail"
        rows.append({"id": tid, "task_type": t["task_type"], "stack": t["stack"], "phrasing": t["phrasing"],
                     "expect_none": t["expect_none"], "pair_id": t["pair_id"], "selected": sorted(S), "relevant": sorted(R),
                     "precision": len(S & R) / len(S) if S and R else None,
                     "recall": len(S & R) / len(R) if R and not t["expect_none"] else None,
                     "wrong_loads": sorted(s for s in S if grade.get(s, 0) < 2), "relevant_in": inq, "class": cls,
                     "q2_ranks_of_relevant": {r: (rk[tid]["bm25_q2"].index(r) + 1 if r in rk[tid]["bm25_q2"] else None) for r in sorted(R)}})
    (S3 / "selection-eval.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))

    def mean(v):
        v = [x for x in v if x is not None]
        return round(sum(v) / len(v), 3) if v else None

    def block(sel_rows):
        cov = [r for r in sel_rows if r["relevant"] and not r["expect_none"]]
        nocov = [r for r in sel_rows if not r["relevant"]]
        en = [r for r in sel_rows if r["expect_none"]]
        return {"tasks": len(sel_rows), "precision": mean(r["precision"] for r in cov), "precision_n": sum(1 for r in cov if r["precision"] is not None),
                "recall": mean(r["recall"] for r in cov), "recall_n": len(cov),
                "hit_rate": mean(1.0 if set(r["selected"]) & set(r["relevant"]) else 0.0 for r in cov),
                "mean_loaded": mean(len(r["selected"]) for r in sel_rows),
                "wrong_loads_total": sum(len(r["wrong_loads"]) for r in sel_rows),
                "tasks_with_wrong_load": sum(1 for r in sel_rows if r["wrong_loads"]),
                "none_acc_oracle": mean(1.0 if not r["selected"] else 0.0 for r in nocov), "none_acc_oracle_n": len(nocov),
                "none_acc_expect_none": mean(1.0 if not r["selected"] else 0.0 for r in en), "none_acc_expect_none_n": len(en),
                "over_load_tasks": sum(1 for r in sel_rows if r["class"] == "over_load"),
                "classes": dict(Counter(r["class"] for r in sel_rows))}

    summary = {"overall": block(rows), "by": {}}
    for axis in ("task_type", "stack", "phrasing"):
        g = defaultdict(list)
        for r in rows:
            g[r[axis]].append(r)
        summary["by"][axis] = {k: block(v) for k, v in sorted(g.items())}
    pairs = defaultdict(dict)
    for r in rows:
        if r["pair_id"]:
            pairs[r["pair_id"]][tasks[r["id"]]["pair_side"]] = r
    changed = moved = oracle_differs = 0
    for p in pairs.values():
        a, b = p["a"], p["b"]
        Sa, Sb, Ra, Rb = set(a["selected"]), set(b["selected"]), set(a["relevant"]), set(b["relevant"])
        oracle_differs += Ra != Rb
        if Sa != Sb:
            changed += 1
            ea, eb = Sa - Sb, Sb - Sa
            good = all(s in Ra for s in ea) and all(s in Rb for s in eb) and not any(s in Rb and s not in Ra for s in ea) \
                and not any(s in Ra and s not in Rb for s in eb) and (ea | eb)
            moved += bool(good)
    summary["pairs"] = {"pairs": len(pairs), "selection_changed": changed, "moved_with_direction": moved, "oracle_sets_differ": oracle_differs}
    (S3 / "selection-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "by"}, indent=1))


if __name__ == "__main__":
    main()
