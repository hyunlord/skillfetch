#!/usr/bin/env python3
"""(a) Current BM25 (search-fix worktree = main@53b81df code, ~/.skillfetch/index): rank of the best gold id in
the full ranking for each eval query, with the query's own profile and default tiers. Also writes the top-50 for
each query (retrieval/top50/<qid>.json) and top-1 scores for gold and no-gold queries."""
import json
import sys
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.index.search import Searcher

R = Path(__file__).resolve().parents[1]


def load(name):
    return [json.loads(l) for l in (R / name).read_text().splitlines() if l.strip()]


def main():
    index = Index.load(DEFAULT_INDEX_DIR)
    s = Searcher(index)
    # score is not part of the public result; recompute it with the same ranking by asking for everything
    out, scores = [], []
    (R / "top50").mkdir(exist_ok=True)
    for name, has_gold in (("retrieval-eval.jsonl", True), ("retrieval-nogold.jsonl", False)):
        for q in load(name):
            full = s.search(q["query"], q["profile"], k=10_000)
            ids = [x["id"] for x in full]
            sc = s.scored(q["query"], q["profile"]) if hasattr(s, "scored") else None
            ranks = {g: (ids.index(g) + 1 if g in ids else None) for g in q["gold"]}
            best = min([r for r in ranks.values() if r], default=None)
            repro = q["recorded_ids"] == ids[: len(q["recorded_ids"] or [])] if q["recorded_ids"] else None
            row = {"qid": q["qid"], "task_id": q["task_id"], "has_gold": has_gold, "gold_ranks": ranks,
                   "best_rank": best, "n_hits": len(ids), "reproduces_recorded": repro}
            out.append(row)
            (R / "top50" / f"{q['qid'].replace('#', '_')}.json").write_text(json.dumps(
                [{"id": x["id"], "title": x["title"], "summary": x["summary"]} for x in full[:50]],
                ensure_ascii=False, indent=1))
    (R / "bm25-ranks.jsonl").write_text("".join(json.dumps(x) + "\n" for x in out))
    g = [x for x in out if x["has_gold"]]
    n = len(g)
    for k in (1, 3, 10, 50):
        hit = sum(1 for x in g if x["best_rank"] and x["best_rank"] <= k)
        print(f"top-{k}: {hit}/{n} = {hit / n:.2f}")
    print("not ranked at all:", sum(1 for x in g if not x["best_rank"]))
    print("reproduces recorded top-k:", sum(1 for x in out if x["reproduces_recorded"]), "/", len(out))


if __name__ == "__main__":
    sys.exit(main())
