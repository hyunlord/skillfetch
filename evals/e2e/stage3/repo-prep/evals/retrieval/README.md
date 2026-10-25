# Retrieval evaluation set

All files here are synthetic, written for this evaluation (no third-party text), so they carry no license restrictions beyond this repository's own.

- `tasks.jsonl` — 380 developer requests: 300 stratified over 12 task types × 6 stacks × 5 phrasings, 40 trivial requests that should load nothing (`expect_none`), and 20 pairs that differ only in a direction (`pair_id`).
- `oracle.jsonl` — per task, the graded candidate pool (0–3 per skill id of index-2026-10-22, with the pool source and a process flag) and the relevant set (grade ≥ 2).
- `queries.jsonl` — the frozen queries: `q1` the request as typed, `q2` the router's one-sentence restatement, `q3` that restatement split into domain / method / stack.

Run `uv run python scripts/eval_retrieval.py` (add `--minilm` for the embedding comparison; needs `sentence-transformers`).
