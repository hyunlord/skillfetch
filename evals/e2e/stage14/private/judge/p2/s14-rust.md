## s14-rust

| code | 동시성 정확성 1-5 | 범위·유지보수 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| 0d380d40 | 5 | 5 | 5 | Validation before acquire_owned, permit moved into spawn_blocking, JoinError→500, limit configurable (CPU cores, min 1); 5 tests incl. current_thread offload proof, slot release, validation not queued, zero-limit; unbounded wait flagged to user |
| 0ef18159 | 5 | 5 | 5 | Same correct design (permit held for whole blocking job, panic→500, env filter n>0 plus max(1)); 3 focused tests incl. offload proof on single-thread runtime and slot release; unbounded queue and body-limit bug reported, not touched |
| af477346 | 5 | 5 | 5 | Most deliberate overflow handling: bounded wait (CMS_RESIZE_QUEUE_TIMEOUT_MS) then 503 + Retry-After, reasoned half-core default; 5 tests cover 503, queued completion, slot release, no-slot for bad params, offload; only nit: Semaphore::new without max(1) for directly built Config |
| 1ea542e5 | 5 | 4 | 4 | Correct offload + semaphore with panic→500 and a real offload test plus load measurement; but AppState builds Semaphore from raw config (0 from a hand-built Config deadlocks), limit test only yields once, and a git stash mishap during the work |
| 4d5f152a | 5 | 4 | 4 | Correct change, zero guarded, docs updated, good before/after measurement with 2 workers; but no test proves offloading (the healthz test runs while the resize is still queued), second test only checks completion |
| 78c56057 | 5 | 4 | 4 | Correct offload + bounded semaphore, panic→500 with message, docs in both READMEs, honest load test; only one test (limit), nothing guards against regressing to in-handler resize |

1. 0d380d40, 0ef18159, af477346
4. 1ea542e5, 4d5f152a, 78c56057
