#!/usr/bin/env python3
"""Step 3 rankings (offline, no model calls): every method's top-50 per task -> rankings.json, timings -> rank-timing.json.

  bm25_q1, bm25_q2   search_skills(query) as the server returns it (k=50 compact, default tiers, no profile)
  bm25_q3            three search_skills calls (domain / method / stack sentences), RRF-merged (k=60), top 50
  emb_q1, emb_q2     all-MiniLM-L6-v2 cosine over the tier A/B canonical skills, text = title + description +
                     summary + keywords + synthetic_queries
  rrf_q1, rrf_q2     BM25 full ranking + embedding full ranking, RRF (k=60), top 50
Run in a venv with skillfetch (64f4bd8) and sentence-transformers."""
import json
import time
from pathlib import Path

import numpy as np

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S3 = Path(__file__).resolve().parents[1]
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60
K = 50


def rrf(*rankings):
    score = {}
    for ranking in rankings:
        for n, sid in enumerate(ranking, 1):
            score[sid] = score.get(sid, 0) + 1 / (RRF_K + n)
    return sorted(score, key=lambda s: (-score[s], s))


def text(r):
    def j(v):
        return " ".join(map(str, v)) if isinstance(v, list) else str(v or "")
    return "\n".join(j(r.get(f)) for f in ("title", "description", "summary", "keywords", "synthetic_queries"))


def main():
    s = Session(Index.load(DEFAULT_INDEX_DIR))
    docs = [r for r in s.index.canonical() if r.get("tier") in ("A", "B")]
    ids = [r["id"] for r in docs]
    queries = [json.loads(l) for l in (S3 / "queries.jsonl").open()]
    timing = {}
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device="cpu")
    timing["model_load_s"] = round(time.perf_counter() - t0, 2)
    t0 = time.perf_counter()
    E = model.encode([text(r) for r in docs], batch_size=64, normalize_embeddings=True, convert_to_numpy=True)
    timing["index_embed_s"] = round(time.perf_counter() - t0, 2)
    timing["docs"] = len(docs)
    timing["truncated_docs"] = sum(1 for r in docs if len(model.tokenizer(text(r))["input_ids"]) > model.max_seq_length)
    out, lat_bm25, lat_emb = {}, [], []
    for q in queries:
        row = {}
        t0 = time.perf_counter()
        row["bm25_q1"] = [r["id"] for r in s.search_skills(q["q1"])["results"]]
        lat_bm25.append(time.perf_counter() - t0)
        row["bm25_q2"] = [r["id"] for r in s.search_skills(q["q2"])["results"]]
        parts = [[r["id"] for r in s.search_skills(q["q3"][k])["results"]] for k in ("domain", "method", "stack")]
        row["bm25_q3"] = rrf(*parts)[:K]
        for name, qt in (("q1", q["q1"]), ("q2", q["q2"])):
            t0 = time.perf_counter()
            v = model.encode([qt], normalize_embeddings=True, convert_to_numpy=True)[0]
            emb = [ids[i] for i in np.argsort(-(E @ v), kind="stable")]
            lat_emb.append(time.perf_counter() - t0)
            row[f"emb_{name}"] = emb[:K]
            full_bm25 = [r["id"] for r in s.searcher.search(qt, None, k=10_000)]
            row[f"rrf_{name}"] = rrf(full_bm25, emb)[:K]
        out[q["id"]] = row
    timing["bm25_query_ms_median"] = round(1000 * float(np.median(lat_bm25)), 1)
    timing["emb_query_ms_median"] = round(1000 * float(np.median(lat_emb)), 1)
    from huggingface_hub import scan_cache_dir
    repo = next(r for r in scan_cache_dir().repos if r.repo_id == MODEL)
    timing["model_cache_mb"] = round(repo.size_on_disk / 1e6, 1)
    timing["embeddings_mb_float32"] = round(E.astype(np.float32).nbytes / 1e6, 2)
    (S3 / "rankings.json").write_text(json.dumps(out))
    (S3 / "rank-timing.json").write_text(json.dumps(timing, indent=1))
    print(json.dumps(timing))


if __name__ == "__main__":
    main()
