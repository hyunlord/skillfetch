## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 286287e7 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; create/update/read schemas, null rejected in PATCH, HttpUrl normalisation for duplicate detection; one error envelope covering 404/405/422/500; repository layer; 51 passing tests that check error codes and fields |
| 8abd4274 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; IntegrityError checked for the url constraint specifically, other errors re-raised; error envelope everywhere, including a catch-all 500 handler; clean repository and dependency; 57 thorough tests including rollback and field-level error checks |
| 35afcc12 | 5 | 4 | 5 | 5 | 5 | 5 | 27/27; uniform error envelope with field paths; atomic PATCH with rollback tested; PATCH null rejection uses a `= None  # type: ignore` trick that works but is fragile |
| 53760f13 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; schema built in lifespan, check_same_thread handled, url-specific IntegrityError check; well-organised class-based tests (58); errors use the default `detail` shape and have no code field |
| d02be21c | 5 | 5 | 5 | 4 | 5 | 5 | 27/27; consistent `{code, detail}` errors including routing errors; atomic update; storage and domain errors share db.py, and the 405 handler drops the Allow header |
| 960a9922 | 5 | 5 | 5 | 4 | 5 | 5 | 27/27; error envelope plus documented error models; repository class; schema runs both in lifespan and on every request (redundant); any IntegrityError is treated as a duplicate |
| 354dd4c5 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; simple JSON-column tags with json_each filter suit the size; url-specific conflict check; X-Total-Count header; 62 tests incl. invalid-url matrix and default limit |
| b5513af6 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; repository with domain exceptions mapped by handlers; null rejection via fields_set; storage verified by reading the sqlite file; error responses not documented in OpenAPI |
| 4680671d | 5 | 4 | 5 | 4 | 5 | 5 | 27/27; uniform error envelope with field paths; existence check runs outside the update transaction; errors.py imports from the storage module; PATCH uses the type-ignore None trick |
| 2ae44e25 | 5 | 5 | 5 | 4 | 5 | 4 | 27/27, 60 tests, url-specific IntegrityError handling; but sqlite connection created without check_same_thread=False while the dependency and endpoint can run on different threadpool threads (latent intermittent 500) |
| 656f982a | 5 | 4 | 5 | 4 | 5 | 4 | 27/27; error envelope for all errors; connection lacks check_same_thread=False (threadpool hazard); storage mixed with domain errors in db.py; type-ignore None trick in PATCH schema |
| 17bc0ae0 | 5 | 5 | 4 | 4 | 5 | 4 | 27/27; custom validators and tag normalisation are good; SCHEMA executed on every request despite lifespan init; any IntegrityError mapped to 409; tests have no shared conftest |
| c4c145c1 | 5 | 5 | 4 | 4 | 5 | 4 | 27/27; correct repository with url-specific conflict check; OpenAPI error responses declared as empty dicts; default detail errors; tests solid (59) |
| 967d47bf | 5 | 5 | 4 | 4 | 5 | 4 | 27/27; HttpUrl normalisation and null rejection fine; storage and errors share db.py; existence pre-check outside transaction; any IntegrityError mapped to duplicate |
| c2d64eeb | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; custom tag validator; `os.environ.get("BOOKMARKS_DB", "bookmarks.db")` lets an empty BOOKMARKS_DB fall through to an anonymous DB; 422 tests assert status only, no rollback checks |
| c850332d | 5 | 5 | 4 | 3 | 4 | 4 | 27/27; SQL lives directly in route handlers (no storage layer); no check_same_thread=False; every IntegrityError becomes 409; tests adequate but assert mostly status codes |
| d33b78d7 | 5 | 4 | 4 | 4 | 4 | 4 | 27/27; JSON-column tags kept minimal; PATCH null check also fires on unknown keys before extra=forbid; thinner tests (46), rollback on 409 only partly checked |
| 8e80493a | 5 | 5 | 4 | 5 | 2 | 3 | app passes 27/27 and code is clean, but the test suite fails to run in the check (no pytest pythonpath config or tests/__init__.py, so `app` is not importable), and tests were a stated requirement |

1. 286287e7, 8abd4274
3. 35afcc12, 53760f13, d02be21c, 960a9922, 354dd4c5, b5513af6
9. 4680671d
10. 2ae44e25
11. 656f982a, 17bc0ae0, c4c145c1, 967d47bf
15. c2d64eeb
16. c850332d, d33b78d7
18. 8e80493a
