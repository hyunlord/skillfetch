## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0ded5561 | 5 | 5 | 4 | 5 | 5 | 5 | Contract 27/27; separate create/update/read schemas, null rejected on PATCH, URL host/scheme/whitespace checks; UNIQUE constraint mapped to 409 inside a transaction; errors use FastAPI's default `detail` shape rather than one uniform envelope |
| 3e14698a | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; clean db/repository/schemas/routes split, uniform `{"error":{code,message,details}}` envelope for every error incl. 404/405 framework errors, transactional update with rollback test, 56 passing tests |
| 9e77c02c | 5 | 4 | 5 | 5 | 5 | 5 | Contract 27/27; uniform error envelope, per-request transaction in the dependency; HttpUrl normalises (and so alters) the stored URL, and the tag validators are attached with lambdas |
| b9d5aaeb | 5 | 5 | 5 | 3 | 4 | 4 | Contract 27/27 and a good error envelope, but the sqlite connection is opened without `check_same_thread=False` while FastAPI runs the sync dependency and endpoint in threadpool workers (latent 500s under load), and the schema is created only in lifespan; tests are thinner (created_at only checked for truthiness) |
| ef9d83c6 | 5 | 4 | 5 | 5 | 5 | 5 | Contract 27/27; dedicated errors module with a uniform envelope, JSON tags column filtered with json_each; BookmarkUpdate rejects null through `Url = None  # type: ignore`, which works but is a hack |
| ff992312 | 5 | 5 | 5 | 3 | 5 | 4 | Contract 27/27, strong schemas, uniform envelope and good tests (field-level 422 assertions, restart persistence); same connection-threading flaw as b9d5aaeb (no `check_same_thread=False`) and schema created only at startup |

1. 3e14698a
2. 0ded5561, 9e77c02c, ef9d83c6
5. ff992312
6. b9d5aaeb
