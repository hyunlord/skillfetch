# Retrieval evaluation set

All files here are synthetic, written for this evaluation (no third-party text), so they carry no license restrictions beyond this repository's own.

- `tasks.jsonl` — 380 developer requests: 300 stratified over 12 task types × 6 stacks × 5 phrasings, 40 trivial requests that should load nothing (`expect_none`), and 20 pairs that differ only in a direction (`pair_id`).
- `oracle.jsonl` — per task, the graded candidate pool (0–3 per skill id of index-2026-10-22, with the pool source and a process flag) and the relevant set (grade ≥ 2).
- `queries.jsonl` — the frozen queries: `q1` the request as typed, `q2` the router's one-sentence restatement, `q3` that restatement split into domain / method / stack.

Score it with `uv run skillfetch eval retrieval [--index DIR]`. It runs no model, takes about 8 s and prints recall@10 / @50 for q1, q2 and q3 (q3's three sentences go to `search_skills` as `queries`, merged by RRF). Add `--minilm` for the embedding comparison, which needs `sentence-transformers` (for example `uv run --with sentence-transformers skillfetch eval retrieval --minilm`). Results and the rest of the benchmark (selection, failure classes, coverage, end-to-end sessions) are in `docs/writeup/numbers.md` §13.

The labels were written by a model (Opus 5.5), the same one that runs the router in these tests. Two grading passes agree exactly on 94.2% of 500 pairs; that is consistency, not ground truth.
