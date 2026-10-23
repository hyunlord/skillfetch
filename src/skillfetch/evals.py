"""`skillfetch eval retrieval`: the offline retrieval benchmark over evals/retrieval/.

No model calls. For each of the 380 synthetic tasks, search_skills (k=50, compact, default
tiers, no profile) runs on three frozen queries: q1 (the request as typed), q2 (the router's
one-sentence restatement) and q3 (that restatement split into domain / method / stack,
passed as `queries`, so each is searched and the rankings are merged by `search.rrf`).
recall@10 and @50 are measured against the oracle's relevant set (grade >= 2), the subset
the catalogue-only oracle picked (`relevant_2a`, independent of any ranking) and the process
subset; tasks without relevant skills and expect_none tasks are skipped (recall undefined).
With `minilm=True`: all-MiniLM-L6-v2 over title + description + summary + keywords +
synthetic_queries, alone and RRF-fused with the full BM25 ranking, for q1 and q2 (needs
sentence-transformers; not a skillfetch dependency).
"""

from __future__ import annotations

import json
from pathlib import Path

from skillfetch.index.search import rrf
from skillfetch.mcp.session import Session

DEFAULT_EVALS = Path(__file__).resolve().parents[2] / "evals" / "retrieval"
SETS = {"all": "relevant", "2a": "relevant_2a", "process": "relevant_process"}
LABELS = {
    "bm25_q1": ("q1 as typed", "BM25"),
    "bm25_q2": ("q2 restatement", "BM25"),
    "bm25_q3": ("q3 three queries, RRF", "BM25"),
    "emb_q1": ("q1 as typed", "MiniLM"),
    "rrf_q1": ("q1 as typed", "BM25 + MiniLM RRF"),
    "emb_q2": ("q2 restatement", "MiniLM"),
    "rrf_q2": ("q2 restatement", "BM25 + MiniLM RRF"),
}


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rankings(session: Session, queries: list[dict], minilm: bool = False) -> dict[str, dict]:
    """Per task id, the top-50 ids of each method."""

    def top(**kw) -> list[str]:
        return [r["id"] for r in session.search_skills(**kw)["results"]]

    out = {
        q["id"]: {
            "bm25_q1": top(query=q["q1"]),
            "bm25_q2": top(query=q["q2"]),
            "bm25_q3": top(queries=[q["q3"][k] for k in ("domain", "method", "stack")]),
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
            fields = ("title", "description", "summary", "keywords", "synthetic_queries")
            return "\n".join(
                " ".join(map(str, v)) if isinstance(v, list) else str(v or "")
                for v in (r.get(f) for f in fields)
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


def recall_table(tasks: dict, oracle: dict, rk: dict) -> tuple[dict, dict]:
    """{method: {(set, cut): mean recall}} and {set: number of tasks}."""
    scored = {
        name: [tid for tid, t in tasks.items() if not t["expect_none"] and oracle[tid][field]]
        for name, field in SETS.items()
    }
    methods = list(next(iter(rk.values())))
    table = {}
    for m in methods:
        row = {}
        for name, field in SETS.items():
            for cut in (10, 50):
                v = [
                    sum(1 for s in oracle[tid][field] if s in rk[tid][m][:cut])
                    / len(oracle[tid][field])
                    for tid in scored[name]
                ]
                row[(name, cut)] = sum(v) / len(v)
        table[m] = row
    return table, {name: len(ids) for name, ids in scored.items()}


def render(table: dict, counts: dict) -> str:
    head = (
        "| query | method | (i) all @10 | (i) all @50 | (ii) 2a @10 | (ii) 2a @50 "
        "| process @10 | process @50 |"
    )
    lines = [
        f"Tasks scored: all {counts['all']}, 2a {counts['2a']}, process {counts['process']}.",
        "",
        head,
        "|---|---|---|---|---|---|---|---|",
    ]
    for m, row in table.items():
        query, method = LABELS.get(m, (m, ""))
        cells = " | ".join(f"{row[(s, c)]:.3f}" for s in SETS for c in (10, 50))
        lines.append(f"| {query} | {method} | {cells} |")
    return "\n".join(lines) + "\n"


def retrieval(session: Session, evals: Path = DEFAULT_EVALS, minilm: bool = False) -> str:
    tasks = {t["id"]: t for t in jsonl(evals / "tasks.jsonl")}
    oracle = {o["id"]: o for o in jsonl(evals / "oracle.jsonl")}
    rk = rankings(session, jsonl(evals / "queries.jsonl"), minilm)
    return render(*recall_table(tasks, oracle, rk))
