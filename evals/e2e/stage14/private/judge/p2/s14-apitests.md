## s14-apitests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 2108337c | 5 | 5 | 5 | 5 | 4 | 4 | 48→153 tests, 8/8 mutants; per-endpoint files, assert_422 with exact loc, exact 404/409 bodies, persistence, concurrency, IDN, limits. API edited: the int64 bound on ids/offset fixes a real 500, but it also changes behaviour the contract does not require (id 0/-1 now 422 instead of 404; tag cap now counts distinct tags, so 40 duplicated tags become valid). README updated |
| 2989c066 | 5 | 5 | 4 | 5 | 5 | 5 | 47→167 tests, 8/8 mutants; very wide coverage (scheme list, limits, wildcard and injection tags, 404-vs-409 precedence, rollback, cascade, OpenAPI). Only API change is a Path/Query int64 bound fixing a real overflow 500; many 422 cases assert status only |
| 319d1808 | 5 | 5 | 5 | 5 | 4 | 5 | 51→153 tests, 8/8 mutants; exact envelope/code/field assertions, boundaries, non-ASCII, concurrency through the repository, OpenAPI, idempotent schema. API untouched; the int64-overflow 500 is recorded as strict xfail rather than fixed. Committed a stray binary `api/.coverage` |
| 6a727d13 | 5 | 5 | 5 | 5 | 5 | 5 | 44→139 tests, 8/8 mutants; tests only. Exact error envelope incl. location, URL normalisation table, length limits on both sides, unusable bodies, 500 non-leak with log check, OpenAPI status-code map, HTTP-level race; overflow bug pinned with a strict xfail marker instead of editing the API |
| c60acedd | 5 | 5 | 4 | 4 | 4 | 4 | 42→160 tests, 8/8 mutants; broad URL edge table, frozen-clock tie-break, cascade and storage tests. API edited beyond the overflow 500 fix: ids 0/-1 now 422 and the URL validator was tightened (whitespace/control chars, ports), a change of validation scope. conftest switches every test to raise_server_exceptions=False; most 422 checks status-only |
| d5bed1c4 | 5 | 5 | 5 | 5 | 5 | 5 | 50→166 tests, 8/8 mutants; error_locs asserts exact loc lists, created_at ordering and id tie-break via raw DB, default limit, 0/-1/max-int stay 404 per contract, DB-level race; only API change is the int64 bound fixing a real overflow 500, docs/usage.md updated to match |

1. 6a727d13, d5bed1c4
3. 2989c066, 319d1808
5. 2108337c
6. c60acedd
