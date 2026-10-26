## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0ed0772d | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27, 49 tests pass. Separate create/update/read schemas with explicit null rejection and URL/title/tag validation; db/repository/routes split; schema init in lifespan with check_same_thread handled; tests cover conflict-leaves-record-unchanged. |
| 077579ea | 5 | 4 | 5 | 5 | 5 | 5 | Contract 27/27, 50 tests pass. Clean db/schemas/routes, normalised tag table, ErrorResponse documented, existence checked before PATCH. HttpUrl rewrites the stored url (adds a trailing slash), a small surprise for clients. |
| d006891c | 5 | 5 | 4 | 5 | 5 | 5 | Contract 27/27, 49 tests pass. Repository split, JSON tags with json_each filter, model_validator rejects explicit nulls. PATCH of a missing id with a taken url returns 409 instead of 404 (no existence check first). |
| 460a1d87 | 5 | 5 | 4 | 3 | 5 | 4 | Contract 27/27, 50 tests pass, validation good. But the sqlite connection is opened without check_same_thread=False while the sync generator dependency and the endpoint may run on different threadpool threads, a latent ProgrammingError/500 under load that the others guard against. Same 409-before-404 PATCH ordering. |

1. 0ed0772d
2. 077579ea, d006891c
4. 460a1d87
