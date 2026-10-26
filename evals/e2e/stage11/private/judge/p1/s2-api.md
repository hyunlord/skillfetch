## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 61e6728b | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; separate create/update/read schemas with null rejected on PATCH, http/https plus host check, tags stripped and deduped; uniform error envelope including 404/405; db/errors/repository/schemas split; 54 tests on isolated DBs. |
| 93b98ffb | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; normalised tag table, a transactional PATCH that rolls back on 409 (tested), consistent error envelope with documented error models; 45 thorough tests on isolated DBs. |
| b6548d5a | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; HttpUrl normalisation so case and trailing-slash variants count as duplicates, a per-request transaction in the dependency (failed PATCH fully rolled back), consistent envelope; 52 tests. |
| c4869158 | 5 | 5 | 4 | 5 | 5 | 5 | Contract 27/27 with solid schemas, a transactional update and good tests (51), but errors keep FastAPI's default `detail` shape (a string for 404/409, a list for 422), not one consistent error body. |
| c897cc9d | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; strict schemas with a null-rejecting model validator, a uniform error envelope covering 404/405/422, tests that check which field failed and that data persists across app restarts. |
| ff2fbd72 | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; cleanest layering (db / repository / schemas / routes) with domain exceptions mapped to one envelope, the existence check and update in one transaction, 56 tests incl. rollback and OpenAPI. |

1. 61e6728b, 93b98ffb, b6548d5a, c897cc9d, ff2fbd72
6. c4869158
