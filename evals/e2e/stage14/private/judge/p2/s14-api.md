## s14-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 49b68985 | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; db/repository/routes/schemas split, HttpUrl normalisation, null-rejecting partial update, tag normalisation in ordered tag table, one error envelope incl. 404/405/422, only url-UNIQUE mapped to 409; 51 isolated tests asserting error codes and fields, incl. rollback, default DB path and persistence |
| 63b4915b | 5 | 5 | 5 | 5 | 5 | 5 | Contract 27/27; errors.py with typed ApiError hierarchy, uniform envelope incl. a logged, non-leaking 500 handler, documented OpenAPI error models; store/schemas/db split, transactional update; 44 strong tests (field/location checks, 500 path, persistence); README/USAGE updated accurately |
| 690a6138 | 5 | 4 | 4 | 4 | 5 | 4 | Contract 27/27; create_app(db_path) makes tests clean, WAL, docs updated; but BookmarkUpdate uses `Url = None  # type: ignore` instead of an explicit null check, errors keep FastAPI's default {"detail"} shape, and db.py mixes schema and queries; 50 thorough tests |
| a0aab5ea | 5 | 4 | 4 | 3 | 4 | 4 | Contract 27/27; works, but every IntegrityError becomes 409, URLs not normalised (trailing-slash variants can both be saved), tags not lowercased, all SQL and routes in main.py, `type: ignore` defaults for PATCH; 42 tests mostly status-only on 422, and the default-DB test only calls a helper |
| d3f17cb4 | 5 | 5 | 4 | 5 | 4 | 4 | Contract 27/27; clean BookmarkStore, HttpUrl normalisation, explicit null rejection, ordered tags, new api/README.md and root README links; but create/update map any IntegrityError to 409 and errors use default FastAPI shape; 48 tests, 422 cases assert status only |
| ebb20fa6 | 5 | 4 | 4 | 5 | 4 | 4 | Contract 27/27; crud/db/schemas/main split, separate Read model, only url-UNIQUE mapped to 409, model_validator rejects explicit null; tags are case-sensitive, PATCH's 404 check runs outside the write transaction, no docs; 47 tests, 422s status-only, no default-DB-path test |

1. 49b68985, 63b4915b
3. d3f17cb4
4. 690a6138, ebb20fa6
6. a0aab5ea
