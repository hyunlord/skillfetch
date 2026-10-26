## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 43cf8020 | 5 | 5 | 4 | 4 | 5 | 4 | 27/27 contract, 50 tests pass, clean create/update/read schemas with null rejected and tags deduped; but the sqlite connection from a sync yield dependency is opened without check_same_thread=False, so dependency and endpoint on different threadpool threads can raise (latent 500s); schema DDL run on every request |
| 6325e879 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27, 49 tests pass; normalised bookmark_tags table with FK cascade, schema created once in lifespan, repository class, explicit-null rejection, 409 via UNIQUE constraint inside a transaction, test that a conflicting PATCH applies nothing |
| a38515ab | 5 | 5 | 5 | 4 | 5 | 5 | 27/27, 49 tests pass; clear db/repository/schemas/routes split, check_same_thread handled, null rejection via model validator, tags normalised; small nits: DDL executed per connection, tags as a JSON column |
| d362742a | 5 | 4 | 5 | 5 | 5 | 5 | 27/27, 50 tests pass; normalised tag table, ErrorResponse model, conflict test checks the record is unchanged; HttpUrl normalises the stored url (e.g. adds a trailing slash) so the returned url can differ from the one sent, and the PATCH existence check runs outside the transaction |

1. 6325e879
2. a38515ab, d362742a
4. 43cf8020
