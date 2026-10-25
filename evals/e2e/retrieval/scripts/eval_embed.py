#!/usr/bin/env python3
"""Offline embedding evaluation (no runtime change). sentence-transformers/all-MiniLM-L6-v2 over the 1489 tier A/B
canonical skills, document text = title + description + summary + synthetic_queries. For the 34 gold queries:
(i) embedding alone (cosine), (ii) BM25 + embedding reciprocal rank fusion (k=60; BM25 ranking = search_skills'
ranking with the query's profile, from bm25-full.json). Gold rank top-3/10/50. Writes emb-ranks.jsonl,
emb-timing.json and rrf top-50 lists (rrf-top50/<qid>.json) for the pick step.
Run with the scratch venv that has sentence-transformers (not skillfetch's env)."""
import json
import os
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60


def doc_text(d):
    return "\n".join([d["title"], d["description"].strip(), d["summary"].strip(), " ".join(d["synthetic_queries"])])


def dir_size(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())


def main():
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device="cpu")
    load_s = time.perf_counter() - t0
    docs = json.loads((R / "emb-docs.json").read_text())
    ids = [d["id"] for d in docs]
    texts = [doc_text(d) for d in docs]
    t1 = time.perf_counter()
    E = model.encode(texts, batch_size=64, normalize_embeddings=True, convert_to_numpy=True)
    index_s = time.perf_counter() - t1
    tok = model.tokenizer
    truncated = sum(1 for t in texts if len(tok(t)["input_ids"]) > model.max_seq_length)
    bm25 = json.loads((R / "bm25-full.json").read_text())
    qs = [json.loads(l) for l in (R / "retrieval-eval.jsonl").read_text().splitlines()]
    (R / "rrf-top50").mkdir(exist_ok=True)
    byid = {d["id"]: d for d in docs}
    rows, lat = [], []
    for q in qs:
        t2 = time.perf_counter()
        v = model.encode([q["query"]], normalize_embeddings=True, convert_to_numpy=True)[0]
        sims = E @ v
        emb_rank = [ids[i] for i in np.argsort(-sims, kind="stable")]
        lat.append(time.perf_counter() - t2)
        fused = {}
        for rank, i in enumerate(bm25[q["qid"]], 1):
            fused[i] = fused.get(i, 0) + 1 / (RRF_K + rank)
        for rank, i in enumerate(emb_rank, 1):
            fused[i] = fused.get(i, 0) + 1 / (RRF_K + rank)
        rrf_rank = sorted(fused, key=lambda i: (-fused[i], i))

        def best(rank_list):
            pos = {i: n for n, i in enumerate(rank_list, 1)}
            rs = [pos[g] for g in q["gold"] if g in pos]
            return {g: pos.get(g) for g in q["gold"]}, (min(rs) if rs else None)

        eg, eb = best(emb_rank)
        rg, rb = best(rrf_rank)
        bg, bb = best(bm25[q["qid"]])
        rows.append({"qid": q["qid"], "bm25_best": bb, "emb_ranks": eg, "emb_best": eb, "rrf_ranks": rg,
                     "rrf_best": rb, "emb_top3": emb_rank[:3], "rrf_top3": rrf_rank[:3]})
        (R / "rrf-top50" / f"{q['qid'].replace('#', '_')}.json").write_text(json.dumps(
            [{"id": i, "title": byid[i]["title"], "summary": byid[i]["summary"]} for i in rrf_rank[:50]],
            ensure_ascii=False, indent=1))
    (R / "emb-ranks.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    from huggingface_hub import scan_cache_dir
    repo = next(r for r in scan_cache_dir().repos if r.repo_id == MODEL)
    timing = {"model": MODEL, "model_cache_bytes": repo.size_on_disk, "params": sum(p.numel() for p in model.parameters()),
              "dim": int(E.shape[1]), "max_seq_length": model.max_seq_length, "docs": len(docs),
              "docs_truncated": truncated, "model_load_s": round(load_s, 2), "index_s": round(index_s, 2),
              "embeddings_bytes_float32": int(E.astype(np.float32).nbytes),
              "query_latency_ms": {"median": round(1000 * float(np.median(lat)), 1), "max": round(1000 * max(lat), 1)},
              "cpu": os.cpu_count(), "device": "cpu"}
    (R / "emb-timing.json").write_text(json.dumps(timing, indent=1))
    n = len(rows)
    for key in ("bm25_best", "emb_best", "rrf_best"):
        print(key, " ".join(f"top{k}={sum(1 for x in rows if x[key] and x[key] <= k)}/{n}" for k in (3, 10, 50)))
    print(json.dumps(timing))


if __name__ == "__main__":
    main()
