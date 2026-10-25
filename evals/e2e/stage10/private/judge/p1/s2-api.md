## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 22d74cc4 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; separate errors module with one envelope for 404/405/409/422 plus a logged 500 catch-all; repository class; HttpUrl normalises URLs; tests assert error code and field; 51 pass |
| bf0adad2 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; uniform error envelope incl. a 500 handler; checks for the url UNIQUE violation specifically; repository class; precise tests that assert the error field; 57 pass |
| 38e67b8b | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; consistent {code, detail} for every error incl. routing errors; rejects null in PATCH; atomic PATCH rollback tested; 53 pass |
| 445c78ec | 5 | 5 | 5 | 4 | 5 | 5 | 27/27; error envelope with field details; repository; schema created both at lifespan and on every request (redundant); 47 pass |
| 5287ada6 | 5 | 4 | 5 | 5 | 5 | 5 | 27/27; consistent error envelope; PATCH schema relies on a `Url = None` type-ignore trick to reject null; thorough tests, 55 pass |
| c4e5a4ce | 5 | 4 | 5 | 5 | 5 | 5 | 27/27; errors module with envelope incl. 405; X-Total-Count pagination; same type-ignore None trick in PATCH; tests check error field paths; 51 pass |
| 565be0df | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; HttpUrl normalisation, domain exceptions, maps only the url UNIQUE violation to 409; default FastAPI 422 shape; tests organised by class, 58 pass |
| 39296517 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; repository with domain exceptions, maps only the UNIQUE violation; list with X-Total-Count; default 422 shape; 56 pass |
| 5c4d2bb3 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; JSON tag column filtered with json_each; maps only the UNIQUE violation; X-Total-Count; broad tests (62 pass) |
| 011b1ed6 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; clean db/schemas/main split, HttpUrl, rejects null in PATCH; every IntegrityError becomes 409; default error shapes; 52 pass |
| 5fc5d902 | 5 | 5 | 4 | 5 | 4 | 5 | 27/27; solid repository, maps only the UNIQUE violation; default error shapes; several tests only check `"detail" in` body; 59 pass |
| c55e2378 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; compact and correct with str_strip_whitespace and null rejection; every IntegrityError becomes 409; tests narrower (no tag or malformed-body 422 cases); 48 pass |
| 40390328 | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; JSON tag column; DB path fixed at startup in app.state; no 409/404 body checks beyond status; created_at assertion weak; 46 pass |
| 8967efd2 | 5 | 4 | 5 | 3 | 5 | 4 | 27/27; good error envelope; sqlite connection opened without check_same_thread=False while dependency and endpoint can run on different threads; type-ignore None trick; 52 pass |
| 6ce2ae5c | 5 | 5 | 4 | 3 | 5 | 4 | 27/27; clean repository and validation; connection lacks check_same_thread=False (threadpool hazard); default error shapes; 60 pass |
| 91ef7be0 | 5 | 4 | 4 | 4 | 4 | 4 | 27/27; hand-written validators; generic 404/409 messages; schema created at lifespan and per request; thinner tests in one file, 43 pass |
| bb916f00 | 5 | 5 | 3 | 3 | 4 | 4 | 27/27; all SQL inline in main.py with no storage layer; any IntegrityError becomes 409; connection without check_same_thread=False; 48 pass |
| 0d352bf9 | 5 | 5 | 4 | 4 | 2 | 3 | 27/27 and well-designed code, but the session's tests do not run in the check (no pytest pythonpath config), so the requested tests are not delivered in working form |

1. 22d74cc4, bf0adad2, 38e67b8b
4. 445c78ec, 5287ada6, c4e5a4ce, 565be0df, 39296517, 5c4d2bb3, 011b1ed6
11. 5fc5d902
12. c55e2378
13. 40390328, 8967efd2, 6ce2ae5c
16. 91ef7be0
17. bb916f00
18. 0d352bf9
