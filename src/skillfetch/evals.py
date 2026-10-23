"""`skillfetch eval retrieval`: the offline retrieval benchmark over evals/retrieval/.

No model calls. For each of the 380 synthetic tasks, search_skills (k=50, compact, default
tiers, no profile) runs on three frozen queries: q1 (the request as typed), q2 (the router's
one-sentence restatement) and q3 (that restatement split into domain / method / stack,
passed as `queries`, so each is searched and the rankings are merged by `search.rrf`).
`queries-R-{a,b,c}.jsonl`, when present, add the `queries` three router step-1 rules wrote:
R-a (the previous rule), R-b and R-c (the shipped rule).
recall@10 and @50 are measured against the oracle's relevant set (grade >= 2), the subset
the catalogue-only oracle picked (`relevant_2a`, independent of any ranking) and the process
subset; tasks without relevant skills and expect_none tasks are skipped (recall undefined).
hit@10 and @50 (all and 2a): the share of those tasks with at least one relevant skill in
the top k.
One table per oracle: v2 (`oracle.jsonl`, the stage 3 labels) and, when present, v3
(`oracle-v3.jsonl`: v2 plus the router rules' top 10 graded).
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
HIT_SETS = ("all", "2a")
LABELS = {
    "bm25_q1": ("q1 as typed", "BM25"),
    "bm25_q2": ("q2 restatement", "BM25"),
    "bm25_q3": ("q3 three queries, RRF", "BM25"),
    "router_R-a": ("R-a router rule (previous)", "BM25, RRF"),
    "router_R-b": ("R-b router rule", "BM25, RRF"),
    "router_R-c": ("R-c router rule (shipped)", "BM25, RRF"),
    "emb_q1": ("q1 as typed", "MiniLM"),
    "rrf_q1": ("q1 as typed", "BM25 + MiniLM RRF"),
    "emb_q2": ("q2 restatement", "MiniLM"),
    "rrf_q2": ("q2 restatement", "BM25 + MiniLM RRF"),
}
ROUTER_RULES = ("R-a", "R-b", "R-c")
ORACLES = {"v2": "oracle.jsonl", "v3": "oracle-v3.jsonl"}


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rankings(
    session: Session,
    queries: list[dict],
    minilm: bool = False,
    router: dict[str, list[dict]] | None = None,
) -> dict[str, dict]:
    """Per task id, the top-50 ids of each method. `router`: rule name -> its queries rows."""

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
    for rule, rows in (router or {}).items():
        for q in rows:
            out[q["id"]][f"router_{rule}"] = top(queries=q["queries"])
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
    """{method: {(set, cut): mean recall, ("hit " + set, cut): hit rate}} and
    {set: number of tasks}."""
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
                row[("hit " + name, cut)] = sum(1 for x in v if x > 0) / len(v)
        table[m] = row
    return table, {name: len(ids) for name, ids in scored.items()}


def render(table: dict, counts: dict, methods: list[str] | None = None) -> str:
    head = (
        "| query | method | (i) all @10 | (i) all @50 | (ii) 2a @10 | (ii) 2a @50 "
        "| process @10 | process @50 | hit (i) @10 | hit (i) @50 | hit (ii) @10 | hit (ii) @50 |"
    )
    columns = [(s, c) for s in SETS for c in (10, 50)]
    columns += [("hit " + s, c) for s in HIT_SETS for c in (10, 50)]
    lines = [
        f"Tasks scored: all {counts['all']}, 2a {counts['2a']}, process {counts['process']}.",
        "",
        head,
        "|---|---|" + "---|" * len(columns),
    ]
    for m in methods or table:
        row = table[m]
        query, method = LABELS.get(m, (m, ""))
        cells = " | ".join(f"{row[col]:.3f}" for col in columns)
        lines.append(f"| {query} | {method} | {cells} |")
    return "\n".join(lines) + "\n"


def tables(
    session: Session, evals: Path = DEFAULT_EVALS, minilm: bool = False
) -> dict[str, tuple[dict, dict]]:
    """{oracle version: recall_table(...)} for every oracle file in `evals`."""
    tasks = {t["id"]: t for t in jsonl(evals / "tasks.jsonl")}
    router = {
        rule: jsonl(evals / f"queries-{rule}.jsonl")
        for rule in ROUTER_RULES
        if (evals / f"queries-{rule}.jsonl").is_file()
    }
    rk = rankings(session, jsonl(evals / "queries.jsonl"), minilm, router)
    return {
        version: recall_table(tasks, {o["id"]: o for o in jsonl(evals / name)}, rk)
        for version, name in ORACLES.items()
        if (evals / name).is_file()
    }


def retrieval(session: Session, evals: Path = DEFAULT_EVALS, minilm: bool = False) -> str:
    return "\n".join(
        f"Oracle {version} ({ORACLES[version]}). " + render(*result)
        for version, result in tables(session, evals, minilm).items()
    )
