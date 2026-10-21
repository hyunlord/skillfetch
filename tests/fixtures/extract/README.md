# Recorded extraction responses

`responses/*.json` replay Messages API responses (`stop_reason`, `content`, `usage`,
optional `stop_details`) for `tests/ingest/test_extract.py`, so extraction tests run with no
network and no `anthropic` package.

They are synthetic: hand-built to exercise each path of the extractor (valid output, a
miscounted line number, a fabricated quote, an invalid `order` constraint, non-JSON output,
truncation at `max_tokens`, a refusal). They say nothing about model quality; that is what
`skillfetch ingest tests/fixtures --with-api --calibrate` measures.

To turn a real run into a regression fixture, copy an `attempts[]` entry from a cache file in
`~/.skillfetch/extract-cache/` (its `text` becomes `content[0].text`).
