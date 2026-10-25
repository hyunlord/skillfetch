# stage 2 judgments, pass 1 (정답·조건 비공개 하위 에이전트 4개, 도메인당 1개, rubrics.md)

## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 072a1549 | 5 | 5 | 5 | 5 | 5 | 5 | Covers every documented edge case with exact date lists, adds a seeded independent reference implementation (300 seeds) plus random round trips, and pins real bugs (limit=0, unsorted by_weekday, date.max) as strict xfail; 100% line/branch |
| 088a6277 | 5 | 5 | 4 | 5 | 5 | 5 | Thorough class-based suite with all edge cases (SKIP/CLAMP, -30/-31, 2096 leap, scan reset) and strict-xfail bugs; error matches are partly short fragments ("unknown FREQ", "COUNT and UNTIL") |
| 21f8502a | 5 | 5 | 4 | 5 | 5 | 5 | Complete coverage with exact dates, a well-built MAX_SCAN monkeypatch on leap years, and UNTIL format/validity split out; some message matches are fragments, no property tests |
| 24333ee7 | 5 | 5 | 4 | 5 | 5 | 5 | Full coverage plus an invariant test, date.max/limit≤0/duplicate-weekday strict xfails and a package export check; several validation matches only "BYDAY"/"BYMONTHDAY" |
| 3dae4e2a | 5 | 5 | 4 | 5 | 5 | 5 | Very thorough (date.min week, 2000→2400 century, between cross-checked against occurrences, scan reset); message matches are mostly specific but not exact |
| 4dc855d6 | 5 | 5 | 4 | 5 | 5 | 5 | All functions and edge cases covered with exact dates (INTERVAL=3 leap-day cycle, far-future next_after); some validation matches are weak ("INTERVAL", "COUNT", "UNTIL") |
| 73f8212c | 5 | 5 | 4 | 5 | 5 | 5 | Complete and well parametrised (next_after table, count/limit grid, fixture for between); unsorted-weekday xfail only checks sortedness and messages are fragments |
| 78c7043f | 5 | 5 | 5 | 4 | 5 | 5 | Exact full error messages via re.escape, all edge cases and a 7-vs-8 empty-period scan test; flat module with globals defined mid-file |
| 917fe20d | 5 | 5 | 5 | 5 | 5 | 5 | Exact re.escape messages, 200 random round trips, 300-seed invariants and between/next_after consistency checks, named bug-reason constants for strict xfails |
| d1cec521 | 5 | 5 | 4 | 5 | 5 | 5 | Clean, complete suite (count-only-emitted, UNTIL before first match, MONTHLY INTERVAL=12 equals YEARLY); message matches are partial and the property tests are thin |
| d38abc88 | 5 | 5 | 4 | 4 | 5 | 5 | Covers every behaviour and the required edge cases compactly; fewer describe cases, a boundary test that asserts nothing, flat layout |
| e4d7aa62 | 5 | 5 | 4 | 5 | 5 | 5 | Complete with exact date lists, a between fixture and limit≤0/date.max strict xfails; error matches are a mix of exact and fragment |
| ea075d48 | 5 | 5 | 4 | 5 | 5 | 5 | Very broad (exception chaining suppressed, date-range end for all frequencies, a 6×3 invariant grid); some message fragments and set/sortedness-only checks in the bug tests |
| fb34058b | 5 | 5 | 5 | 5 | 5 | 5 | Split sensibly into parse/occurrences/describe/property files, with a brute-force day-walk oracle over 300 seeds for occurrences, next_after, between and round trip, plus exact edge-case tests |
| fdd05fce | 5 | 5 | 4 | 5 | 5 | 5 | Complete coverage plus a parametrised weekly brute-force check and a superscript-digit UNTIL case; validation matches are often fragments without values |

1. 072a1549, 917fe20d, fb34058b
4. 088a6277, 21f8502a, 24333ee7, 3dae4e2a, 4dc855d6, 73f8212c, 78c7043f, d1cec521, e4d7aa62, ea075d48, fdd05fce
15. d38abc88

## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 8b15cf06 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; schemas/repository/routes/errors split; one error envelope for every error, including 405/404 routing and a 500 that leaks nothing (tested); id/offset capped at the SQLite integer max; 71 tests check error codes and fields |
| 48207e90 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; one error envelope for 404/409/422/405/500; HttpUrl-validated URL stored as sent; null rejected on PATCH; transactional rollback tested; tests assert error codes and field paths |
| 355539b9 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; clean db/repository/routes/schemas split with lifespan init; domain exceptions mapped through global handlers; null rejected; strong tests (rollback, normalised duplicates, persistence); errors use the default `detail` shape |
| 4dc95264 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; explicit BEGIN IMMEDIATE transactions in autocommit mode, lifespan schema init; precise check for url IntegrityError; thorough tests with ids; default FastAPI error shape |
| 9f002b92 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; id and offset bounds checked, UNIQUE(bookmark_id, tag), tag filter stripped; 72 tests incl. a raw DB check of stored rows; error shape is the default `detail` |
| b33c4e29 | 5 | 5 | 5 | 4 | 5 | 5 | 27/27; full error envelope incl. 500, BEGIN IMMEDIATE on update; tests check error codes, fields and the OpenAPI error schema; main.py mixes the dependency, error handlers and routes |
| be9f190a | 5 | 4 | 5 | 5 | 5 | 5 | 27/27; repository class, URL-conflict context manager, full error envelope with logged 500; tag count unbounded; `environ.get` default lets an empty BOOKMARKS_DB through |
| 42a12ca5 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; sound crud/db/schemas split; 404/409 raised as HTTPException in routes; existence check runs outside the update transaction; good but slightly thinner tests (53) |
| 47a49ca9 | 5 | 4 | 4 | 5 | 5 | 4 | 27/27; list returns a bare array with X-Total-Count; hand-written urlsplit URL check is weaker than HttpUrl; storage and connection share db.py; tests assert `loc` and the default db in cwd |
| 59e1ccf2 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; tidy repository with domain errors and precise IntegrityError check; tests mostly assert status codes only (52) |
| 7c4d8f84 | 5 | 4 | 4 | 5 | 5 | 4 | 27/27; error envelope with codes, but every IntegrityError becomes duplicate_url and there is no 500 handler; urlsplit check accepts a host with spaces; tests assert error codes and fields |
| 8edee18d | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; correct and simple; tag order relies on rowid, `?tag=` not validated; adequate tests (55) that check mostly status codes |
| 6ba2f14e | 5 | 4 | 4 | 4 | 5 | 4 | 27/27; tags kept in a JSON column filtered with json_each; any IntegrityError becomes 409; bare list + X-Total-Count; db.py imports response schemas and uses `assert`; tests are solid |
| df6fcde4 | 5 | 4 | 4 | 5 | 4 | 4 | 27/27; bare list + X-Total-Count; urlsplit-based URL check; generic 404 text; tests cover the paths but assert little beyond status codes |
| eda80050 | 5 | 4 | 4 | 5 | 4 | 4 | 27/27; validator re-raises pydantic ValidationError inside AfterValidator; `?tag=` unvalidated; default error shape; tests mostly status-only (61) |

1. 8b15cf06, 48207e90
3. 355539b9, 4dc95264, 9f002b92, b33c4e29, be9f190a
8. 42a12ca5, 47a49ca9, 59e1ccf2, 7c4d8f84, 8edee18d
13. 6ba2f14e, df6fcde4, eda80050

## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0ed4a79f | 5 | 5 | 5 | 4 | 5 | 5 | 코드와 일치(fallback false, 메서드 미구분, @/ 별칭 사용처, item undefined 주의까지), README=개요/usage=확장으로 깔끔히 분리; usage가 다소 김 |
| 2dad6746 | 5 | 5 | 5 | 3 | 4 | 4 | 정확하고 dev/prod 차이 표가 유용하나 AGENTS.md 생성 등 레포와 무관한 환경 잡음과 긴 분량, README 주의사항과 usage 문제해결 중복 |
| 496ea4d3 | 5 | 5 | 5 | 4 | 4 | 4 | 정확·완전하고 예제(/api/users/[id]) 실용적이나 usage '실행하기'가 README 설치/스크립트를 반복 |
| 68555dea | 5 | 5 | 5 | 4 | 4 | 4 | 정확하고 컴포넌트 표까지 갖춤; usage가 설치/실행과 라우트 표를 README와 중복 |
| 700f4205 | 5 | 5 | 5 | 4 | 5 | 5 | 정확(errors 분기, <a> 사용 이유, id 숫자·고유 조건), README/USAGE 역할 분리 명확, 문제해결 표 간결 |
| 751dd610 | 5 | 5 | 5 | 4 | 5 | 5 | 정확하고 dev/start 반영 시점 표, 컴포넌트 표, 제약사항까지 충실; 분량이 약간 많음 |
| 7c0d0cd3 | 5 | 5 | 5 | 5 | 5 | 5 | 모든 주장이 코드와 일치, 필요한 항목을 과하지 않게 다루고 README(실행)/usage(동작·확장) 분리와 상호 링크가 가장 깔끔 |
| 805ddcac | 5 | 5 | 5 | 4 | 4 | 4 | usage는 정확하고 우수(동적 라우트·API 예제)하나 README에 AGENTS.md 생성 같은 환경 잡음이 들어가 개요 문서가 산만 |
| 9bb2ef1f | 5 | 5 | 5 | 4 | 4 | 4 | 정확·완전, 문제해결 표 유용; usage 첫 절이 README의 dev/build/start 명령을 반복 |
| a5b65b6f | 5 | 5 | 4 | 4 | 4 | 4 | 정확하고 ISR/fallback 대안 등 확장 안내 좋으나 README에 '[redacted]' 잔재와 무관한 .mcp.json 언급, 주의사항이 README/usage에 중복 |
| b2e539cb | 5 | 5 | 5 | 5 | 5 | 5 | 가장 간결하면서 요구 항목(스크립트·라우트·API·데이터 위치·확장) 모두 정확히 커버, 중복 없음 |
| cdd39e8c | 5 | 5 | 5 | 4 | 4 | 4 | 정확하고 fallback blocking/notFound·Link 작성법 등 유익하나 README에 AGENTS.md/.claude 등 앱 외 내용, next latest 주의가 양쪽에 반복 |
| d008732d | 5 | 5 | 5 | 4 | 5 | 5 | 정확하고 앱 둘러보기·API 레퍼런스·문제해결이 잘 정리됨, README/USAGE 분리 적절 |
| d4d8e027 | 5 | 5 | 5 | 4 | 4 | 4 | 정확하고 버전 표·curl 예시 좋으나 AGENTS.md/agentRules 같은 앱 외 내용과 next latest 설명이 README/usage에 중복 |
| fa46baf7 | 5 | 5 | 5 | 3 | 4 | 4 | 정확·완전하나 usage가 245줄로 길고 설치/실행을 README와 중복, Vercel CLI 등 일반적 내용 포함 |

1. 7c0d0cd3, b2e539cb
3. 0ed4a79f, 700f4205, 751dd610, d008732d
7. 496ea4d3, 68555dea, 805ddcac, 9bb2ef1f, cdd39e8c, d4d8e027
13. 2dad6746, a5b65b6f, fa46baf7

## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 06b38889 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 problems handled. Day-first rule is justified, 2 of the 3 outliers rescaled (the third sits in a row rejected for qty), conflicts resolved by a stated lifecycle rule and listed, future dates blanked via --as-of, flags column, shipped revenue by category/country/month/status. None missed. |
| 2596b43e | 5 | 5 | 4 | 5 | 4 | 5 | All 10 handled. All 3 x100 prices fixed, both copies of each conflict quarantined in a "needs a decision" table, flags column, action table. Status table has counts only, no value per status. Clean CSV floats unformatted (4.2, 0.0). None missed. |
| 55deb506 | 5 | 5 | 4 | 5 | 5 | 5 | All 10 handled, with catalog-price and variant tables, Decimal rounding and quality_flags. The headline revenue includes pending orders (stated, but debatable). None missed. |
| 69d3abee | 5 | 4 | 4 | 5 | 5 | 5 | All 10 handled, issues column, rules listed. Normalisation (country/category/status/email case) not counted. Status table has counts only. None missed. |
| 7d650861 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled. Issue/action table, remaining gaps, assumptions section (day-first justified, negatives are not returns), value by status, shares. Only flaw is a "six date formats" typo. None missed. |
| 849cc485 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled. The most detailed per-fix counts, cleaning_notes, assumptions section, 34 passing tests. None missed. |
| 89077ad9 | 5 | 4 | 5 | 4 | 5 | 4 | All 10 handled, per-cell issues.csv, conflicts keep the first occurrence (stated). Report says 12 duplicates in one table and 11 in another. The fix table is split per price value and conflict reasons per line, so it reads messily. None missed. |
| a754d400 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled. Rows-changed-per-column table, flags plus rejection reasons with rationale, revenue by status/category/country/month/product. None missed. |
| b0afc020 | 5 | 4 | 5 | 5 | 4 | 4 | All 10 handled (conflicts keep the most advanced status). The DD/MM rule appears only in the docstring, unjustified and absent from the report. Format normalisation not counted. Clean CSV floats unformatted. None missed. |
| b4558fa9 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled. Per-step cleaning log with counts, conflict table with the kept-row rule, issues column, 27 passing tests. Exact-duplicate check runs on raw values only (works here). None missed. |
| b6c22a55 | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled, with a cell-level cleaning_log.csv and both conflict copies quarantined. The 4 future (2027) dates are only flagged and stay in the clean CSV, though they are excluded from the monthly table. None missed. |
| e1b9e48e | 5 | 4 | 5 | 4 | 4 | 4 | All 10 handled. Conflicts keep the settled status (stated). The clean CSV has no per-row flags column, and fix counts are taken before dedup. Unparseable quantity is labelled "missing". None missed. |
| ed3ec908 | 5 | 4 | 4 | 4 | 4 | 4 | The 3 x100 prices are rejected as generic "unit_price_mismatch" and not corrected, and future-date rows are rejected whole, so valid orders are lost. Missing emails are not counted as a fix. No total-revenue headline and no product breakdown. No flags column. |
| fc31ad56 | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled. Rules section (day-first justified), data_issues column, conflicts quarantined, 6 passing tests. Clean CSV floats unformatted (4.2, 0.0). None missed. |
| fe7ccbff | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled. Field/issue/rows/action fix log, rejection reasons with line numbers, gaps table. The clean CSV has no per-row flags column. None missed. |

1. 06b38889, 7d650861, 849cc485, a754d400, b4558fa9
6. 55deb506, b6c22a55, fc31ad56, fe7ccbff
10. 2596b43e, 69d3abee
12. 89077ad9, b0afc020
14. e1b9e48e
15. ed3ec908

