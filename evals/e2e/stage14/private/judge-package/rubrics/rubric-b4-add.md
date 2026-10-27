# Judging rubric — stage 11 bundle (4) addition (fixed 2026-10-25, before the repo was built and before any session ran)

Same instructions, scale, 총점 meaning, ranking and output format as `stage10/rubric-b4.md` (the bundle (4) rubric of
Stage 10, used unchanged for s10-t016, s10-t263, s10-t115, s10-t198). This file only adds the row for the new set.

| set | criterion 1 | criterion 2 |
|---|---|---|
| s11-t266 | 동시성 정확성 1-5 — the `image` resize in `routes/media.rs` no longer runs on the async runtime (moved into `tokio::task::spawn_blocking`, decode and encode included); a `tokio::sync::Semaphore` bounds how many resizes run at once, the permit is held for the whole blocking job, and what happens to requests over the limit (wait or a clear 503/429) is deliberate; panics/cancellation in the blocking task are mapped to an error response; other CMS endpoints stay responsive under a resize burst | 범위·유지보수 1-5 — change stays in the media path and app state/config (limit configurable or a named constant with a reason); no new dependencies beyond what the fix needs; existing behaviour and tests unchanged; a test for the limit or the offloading; readable for the next person |
