#!/usr/bin/env python3
"""(c) use_case filter + BM25: keep skills whose use-cases.json tags contain the query's use case
(query-use-cases.json), rank the rest exactly as search_skills does (scores.ranked), gold rank."""
import json
from pathlib import Path

from scores import ranked
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.index.search import Searcher

R = Path(__file__).resolve().parents[1]


def main():
    s = Searcher(Index.load(DEFAULT_INDEX_DIR))
    tags = json.loads((R / "use-cases.json").read_text())
    quc = json.loads((R / "query-use-cases.json").read_text())
    rows = []
    for l in (R / "retrieval-eval.jsonl").read_text().splitlines():
        q = json.loads(l)
        uc = quc[q["qid"]]
        rk = [i for _, i in ranked(s, q["query"], q["profile"]) if uc in tags.get(i, [])]
        gr = {g: (rk.index(g) + 1 if g in rk else None) for g in q["gold"]}
        best = min([r for r in gr.values() if r], default=None)
        rows.append({"qid": q["qid"], "use_case": uc, "pool": sum(uc in v for v in tags.values()),
                     "gold_tags": {g: tags.get(g) for g in q["gold"]}, "gold_ranks": gr, "best_rank": best,
                     "top3": rk[:3]})
    (R / "usecase-ranks.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    n = len(rows)
    for k in (1, 3, 10):
        h = sum(1 for x in rows if x["best_rank"] and x["best_rank"] <= k)
        print(f"top-{k}: {h}/{n} = {h / n:.2f}")
    print("gold filtered out:", sum(1 for x in rows if x["best_rank"] is None))
    for x in rows:
        print(x["qid"], x["use_case"], x["pool"], x["gold_ranks"], [i.split("@")[0] for i in x["top3"]])


if __name__ == "__main__":
    main()
