## s14-rust

| code | 동시성 정확성 1-5 | 범위·유지보수 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| bdd3a784 | 5 | 5 | 5 | spawn_blocking with an owned permit moved into the job, JoinError→500; bounded wait (configurable queue timeout) then 503 + Retry-After is a deliberate overflow policy that also caps memory; 5 tests incl. a single-thread responsiveness test that waits for the permit to be taken |
| 5a177318 | 5 | 5 | 5 | correct offload + owned permit + panic→500; unbounded wait is documented and raised with the user; 5 focused tests (responsiveness, waiting, release after failure, validation before queueing, 0→1), confirmed to fail on the old code |
| 18767764 | 5 | 5 | 5 | same correct design, CPU-count default with reason, 0 filtered; 3 tests cover responsiveness, waiting/validation-first and permit release, confirmed to catch the regression; flags the body-limit bug without touching it |
| 1c8b9028 | 5 | 4 | 4 | correct offload, permit and panic handling; real before/after load measurement; only one new test (waiting for a slot), nothing tests that other routes stay responsive |
| c181931d | 5 | 4 | 4 | correct implementation, measured before/after; 2 tests, but the limit test only checks that permits hit 0, not that requests actually wait; reports a stash mishap during the work (recovered) |
| 4fb2c43d | 5 | 4 | 4 | correct implementation with a convincing 2-worker load measurement; tests are weak: /healthz is checked while the resize waits on the semaphore (not while it runs), and the 8-request test does not check the limit |

1. bdd3a784, 5a177318, 18767764
4. 1c8b9028, c181931d, 4fb2c43d
