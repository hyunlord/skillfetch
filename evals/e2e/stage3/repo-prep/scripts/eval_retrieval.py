"""Offline retrieval evaluation over evals/retrieval/ (no model calls).

recall@10 / @50 of search_skills (k=50, compact, default tiers, no profile) for three queries
per task: q1 (the request as typed), q2 (the router's restatement) and q3 (three sentences,
each searched, RRF-merged). Measured against the oracle relevant set (grade >= 2), the subset
the catalogue-only oracle picked (`relevant_2a`, independent of any ranking) and the process
subset. Tasks with no relevant skill and expect_none tasks are skipped (recall is undefined).
With --minilm: all-MiniLM-L6-v2 over title + description + summary + keywords +
synthetic_queries, alone and RRF-fused with BM25, for q1 and q2.

    uv run python scripts/eval_retrieval.py [--minilm] [--index DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

EVAL = Path(__file__).resolve().parents[1] / "evals" / "retrieval"
RRF_K = 60
SETS = {"all": "relevant", "2a": "relevant_2a", "process": "relevant_process"}


def jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (EVAL / name).read_text().splitlines() if line.strip()]


def rrf(*rankings: list[str]) -> list[str]:
    score: dict[str, float] = {}
    for ranking in rankings:
        for n, sid in enumerate(ranking, 1):
            score[sid] = score.get(sid, 0) + 1 / (RRF_K + n)
    return sorted(score, key=lambda s: (-score[s], s))


def rankings(
    session: Session, queries: list[dict], minilm: bool
) -> dict[str, dict[str, list[str]]]:
    def top(text: str) -> list[str]:
        return [r["id"] for r in session.search_skills(text)["results"]]

    out = {
        q["id"]: {
            "bm25_q1": top(q["q1"]),
            "bm25_q2": top(q["q2"]),
            "bm25_q3": rrf(*(top(q["q3"][k]) for k in ("domain", "method", "stack")))[:50],
        }
        for q in queries
    }
    if minilm:
        import numpy as np
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        docs = [r for r in session.index.canonical() if r.get("tier") in ("A", "B")]
        ids = [r["id"] for r in docs]

        def text(r: dict) -> str:
            return "\n".join(
                " ".join(map(str, v)) if isinstance(v, list) else str(v or "")
                for v in (
                    r.get(f)
                    for f in ("title", "description", "summary", "keywords", "synthetic_queries")
                )
            )

        emb = model.encode([text(r) for r in docs], batch_size=64, normalize_embeddings=True)
        for q in queries:
            for name in ("q1", "q2"):
                v = model.encode([q[name]], normalize_embeddings=True)[0]
                ranked = [ids[i] for i in np.argsort(-(emb @ v), kind="stable")]
                out[q["id"]][f"emb_{name}"] = ranked[:50]
                full = [r["id"] for r in session.searcher.search(q[name], None, k=10_000)]
                out[q["id"]][f"rrf_{name}"] = rrf(full, ranked)[:50]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minilm", action="store_true")
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_DIR)
    args = ap.parse_args()
    tasks = {t["id"]: t for t in jsonl("tasks.jsonl")}
    oracle = {o["id"]: o for o in jsonl("oracle.jsonl")}
    rk = rankings(Session(Index.load(args.index)), jsonl("queries.jsonl"), args.minilm)
    methods = list(next(iter(rk.values())))
    print(
        f"{'method':10} "
        + " ".join(f"{k}@{c:<3}" for k in SETS for c in (10, 50))
        + "  (tasks: "
        + ", ".join(
            f"{k} {sum(1 for t in tasks.values() if not t['expect_none'] and oracle[t['id']][f])}"
            for k, f in SETS.items()
        )
        + ")"
    )
    for m in methods:
        cells = []
        for f in SETS.values():
            for cut in (10, 50):
                v = [
                    sum(1 for s in oracle[tid][f] if s in rk[tid][m][:cut]) / len(oracle[tid][f])
                    for tid, t in tasks.items()
                    if not t["expect_none"] and oracle[tid][f]
                ]
                cells.append(f"{sum(v) / len(v):.3f}  ")
        print(f"{m:10} " + " ".join(cells))


if __name__ == "__main__":
    main()
