#!/usr/bin/env python3
"""Step 3 metrics (Python only): recall@10 / @50 of every ranking in rankings.json against the oracle relevant set.
Relevant sets per task (oracle.jsonl, v2 after the 3-0 pool expansion):
  all       grade >= 2 (any pool source)
  2a        grade >= 2 and picked by the catalog-only oracle 2a (independent of any search ranking)
  process   grade >= 2 and marked process
Evaluated tasks: not expect_none and the set is non-empty (recall is undefined without relevant skills).
Recall per task = |relevant ∩ top-k| / |relevant|, averaged over tasks (macro). Writes retrieval.jsonl (per task)
and retrieval-summary.json (overall and per stratum)."""
import json
from collections import defaultdict
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
METHODS = ["bm25_q1", "bm25_q2", "bm25_q3", "emb_q1", "emb_q2", "rrf_q1", "rrf_q2"]
SETS = {"all": "relevant", "2a": "relevant_2a", "process": "relevant_process"}


def main():
    tasks = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "tasks.jsonl").open()}
    orc = {json.loads(l)["id"]: json.loads(l) for l in (S3 / "oracle.jsonl").open()}
    rk = json.loads((S3 / "rankings.json").read_text())
    rows = []
    for tid, t in tasks.items():
        o = orc[tid]
        row = {"id": tid, "task_type": t["task_type"], "stack": t["stack"], "phrasing": t["phrasing"],
               "expect_none": t["expect_none"], "n_relevant": {k: len(o[f]) for k, f in SETS.items()}, "recall": {}, "ranks": {}}
        for m in METHODS:
            r = rk[tid][m]
            pos = {s: i + 1 for i, s in enumerate(r)}
            row["ranks"][m] = {s: pos.get(s) for s in o["relevant"]}
            for k, f in SETS.items():
                rel = o[f]
                if t["expect_none"] or not rel:
                    continue
                for cut in (10, 50):
                    row["recall"][f"{m}|{k}|{cut}"] = sum(1 for s in rel if pos.get(s, 999) <= cut) / len(rel)
        rows.append(row)
    (S3 / "retrieval.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))

    def agg(sel):
        out = {}
        for m in METHODS:
            for k in SETS:
                for cut in (10, 50):
                    v = [r["recall"][f"{m}|{k}|{cut}"] for r in sel if f"{m}|{k}|{cut}" in r["recall"]]
                    out[f"{m}|{k}|{cut}"] = {"mean": round(sum(v) / len(v), 3) if v else None, "n": len(v)}
        return out

    summary = {"overall": agg(rows), "by": {}}
    for axis in ("task_type", "stack", "phrasing"):
        groups = defaultdict(list)
        for r in rows:
            groups[r[axis]].append(r)
        summary["by"][axis] = {g: agg(v) for g, v in sorted(groups.items())}
    (S3 / "retrieval-summary.json").write_text(json.dumps(summary, indent=1))
    o = summary["overall"]
    print("method      | all@10 all@50 (n) | 2a@10 2a@50 (n) | proc@10 proc@50 (n)")
    for m in METHODS:
        c = lambda k, cut: o[f"{m}|{k}|{cut}"]  # noqa: E731
        print(f"{m:11} | {c('all', 10)['mean']} {c('all', 50)['mean']} ({c('all', 50)['n']}) | {c('2a', 10)['mean']} {c('2a', 50)['mean']} ({c('2a', 50)['n']}) | "
              f"{c('process', 10)['mean']} {c('process', 50)['mean']} ({c('process', 50)['n']})")


if __name__ == "__main__":
    main()
