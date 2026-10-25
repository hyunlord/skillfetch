# stage 2 judgments, pass 2 (정답·조건 비공개 하위 에이전트 4개, 도메인당 1개, rubrics.md)

## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 5c993b3b | 5 | 5 | 5 | 5 | 5 | 5 | 기능별 4파일로 나눔, 정확한 메시지 단언, 시드 고정 300케이스를 독립 brute-force 오라클과 비교, 실제 버그는 strict xfail로 고정; 100%/100% |
| 7f664e8a | 5 | 5 | 5 | 5 | 5 | 5 | 문서화된 엣지케이스를 전부 다룸, 공유 코드 없는 일 단위 참조 구현과 300 시드 비교, 랜덤 round trip, strict xfail로 버그 문서화 |
| 77a7a9e9 | 5 | 5 | 5 | 5 | 5 | 5 | re.escape로 메시지 정확히 비교, 랜덤 규칙 200개 round trip과 불변식/between·next_after 일치 검사, 버그 사유 상수로 정리 |
| 5b5851d8 | 5 | 5 | 5 | 5 | 5 | 5 | 모든 함수·빈도·옵션을 다룸, 'got ...'까지 맞추는 메시지 단언, 2100 윤년·date.min·MAX_SCAN 리셋까지 다루고 정확한 날짜 리스트로 단언 |
| 60bd94c8 | 5 | 5 | 5 | 5 | 5 | 5 | UNTIL 형식 오류를 세분화, __cause__ 억제 확인, 단조 증가 불변식 매트릭스, 중복/비정렬 weekday와 date.max는 strict xfail |
| 556d0d9d | 5 | 5 | 5 | 5 | 5 | 5 | 파라미터화된 오류표, canonical 문자열 고정점, 불변식 테스트, 패키지 export 확인, 버그 4종 strict xfail |
| 46c45124 | 5 | 5 | 5 | 5 | 5 | 5 | 오류 31종을 id 붙여 파라미터화, -31 SKIP/CLAMP·2000→2400 윤년·MAX_SCAN 경계 처리, 정확한 날짜로 단언, 버그는 strict xfail |
| 663e35eb | 5 | 5 | 5 | 5 | 5 | 5 | 평평한 함수형 구성이지만 이름이 명확함, 정확한 메시지, 모든 엣지케이스와 date.max·limit=0 버그 xfail, fixture 사용이 적절함 |
| b47f5a21 | 5 | 5 | 5 | 4 | 5 | 5 | WEEKLY를 126케이스 brute-force와 비교, 위첨자 숫자 UNTIL까지 다룸; D/W/M/Y 한 글자 별칭이 읽기 어렵고 단언 없는 경계 테스트가 있음 |
| 8a1063ae | 5 | 5 | 4 | 5 | 5 | 5 | re.escape로 정확한 메시지 비교, 2096→2104 MAX_SCAN 경계; boundary 테스트에 assert가 없고 COUNT 검사는 길이만 봄 |
| f8609f0b | 5 | 5 | 4 | 5 | 5 | 5 | 시작 요일과 맞지 않는 UNTIL==start, next_after 파라미터화, date.max xfail; 메시지는 일부만 비교하고 boundary 테스트에 단언이 없음 |
| dd693d56 | 5 | 5 | 4 | 5 | 5 | 5 | 엣지케이스는 충분하고 UNTIL 형식 오류와 날짜 오류를 나눔; Rule의 BYDAY×freq 검증이 DAILY에서만 확인되고 일부 메시지 매칭이 느슨함 |
| d05929b7 | 5 | 5 | 4 | 5 | 5 | 5 | -30/-31 SKIP·CLAMP, MAX_SCAN 리셋, date.max xfail; 모음이 상대적으로 작고 boundary 테스트에 assert가 없으며 일부는 길이만 단언 |
| 9be399cd | 5 | 5 | 4 | 5 | 5 | 5 | 간결하지만 필수 엣지케이스는 다 있음(INTERVAL=3 윤일, UNTIL 공백 구간); lazy 검사는 길이만 보고 boundary 테스트에 assert가 없음 |
| ba2e939e | 5 | 5 | 4 | 5 | 5 | 4 | 범위는 넓지만 메시지 매칭이 'INTERVAL'·'COUNT'·'UNTIL'·'unknown key' 수준으로 느슨해 형식 오류와 날짜 오류를 구분하지 못하고, 길이만 보는 단언이 많음 |

1. 5c993b3b, 7f664e8a, 77a7a9e9, 5b5851d8, 60bd94c8, 556d0d9d, 46c45124, 663e35eb
9. b47f5a21, 8a1063ae, f8609f0b, dd693d56, d05929b7, 9be399cd
15. ba2e939e

## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 713e65a1 | 5 | 5 | 5 | 5 | 5 | 5 | 계약 27/27; errors/repository/routes/schemas로 나눔; `{"error":{code,message,details}}` 형식을 404/405/422/500에 일관 적용하고 내부 오류가 새지 않음; path id 범위 검사; 71개 테스트가 필드 단위 오류와 500 미노출까지 확인 |
| 081fe80d | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; db/schemas/main 3단으로 간결; 일관된 오류 envelope와 catch-all 500; 갱신 시 BEGIN IMMEDIATE 사용; null 거부와 tag 중복 제거; 59개 테스트가 오류 code와 field를 정확히 확인 |
| 914d71d5 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; repository 클래스와 중복 url을 409로 바꾸는 context manager(경합 상황도 처리); envelope와 로깅하는 500 handler; 테스트가 envelope 전체 본문과 field까지 확인 |
| cfb2caca | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; APIError와 envelope, 500 handler; url은 HttpUrl로 검증하되 입력한 문자열 그대로 저장; 400행 남짓으로 규모에 맞음; 테스트가 code와 field, id 재사용 안 함까지 확인 |
| a2113356 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; path/offset의 SQLite 정수 상한 검사, tag 길이 제한; 오류는 FastAPI 기본 `detail` 형식이라 envelope가 아님; 72개 테스트가 DB 내용까지 직접 확인 |
| 1bab0640 | 5 | 5 | 4 | 5 | 5 | 4 | 27/27; 목록은 배열 + X-Total-Count 헤더; urlsplit으로 직접 url 검증(공백 거부); 오류 형식은 기본 detail(422는 list, 404/409는 str); 테스트가 loc까지 확인 |
| 272d0a4b | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; repository 분리가 깔끔하고 HttpUrl 검증 후 원문 저장; 기본 detail 형식; tag 쿼리에 min_length 없음; 422 테스트는 대부분 상태 코드만 확인 |
| 357c708d | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; 도메인 예외를 handler로 매핑, model_validator로 null 거부; 기본 detail 형식; 422 테스트가 상태 코드만 확인 |
| 58ed1535 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; 목록은 배열 + X-Total-Count; 직접 작성한 url 검증; 기본 detail 형식; 404/409는 본문 전체를 확인하지만 422는 상태 코드만 확인 |
| bf97b119 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; 명시적 BEGIN IMMEDIATE 트랜잭션 helper; 스키마 생성은 lifespan에만 있음; 기본 detail 형식; 422 테스트는 상태 코드 위주 |
| 6e4089be | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; routes/repository 분리; 스키마는 lifespan에서만 만들고 tag 순서는 rowid에 의존; 404/409 메시지가 고정 문자열; 테스트는 상태 코드 위주 |
| c877fbe5 | 5 | 4 | 4 | 5 | 4 | 4 | 27/27; envelope 오류 형식은 좋지만 500 handler가 없고 모든 IntegrityError를 중복으로 매핑; url 검증이 host 안의 공백을 막지 못함; update의 존재 확인이 트랜잭션 밖에 있음 |
| e9c0ab20 | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; tag 쿼리에 아무 제약 없음, 목록 오래된 순; tag 순서는 rowid에 의존; 기본 detail 형식; 422 테스트가 상태 코드만 확인 |
| f6032ba6 | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; 구조는 간결하지만 update의 존재 확인이 트랜잭션 밖에 있음; Location 헤더 없음; 기본 detail 형식; 테스트는 상태 코드 위주 |
| 72989b3e | 5 | 5 | 3 | 4 | 4 | 4 | 27/27; tags를 JSON 컬럼에 저장하고 json_each로 필터(인덱스 사용 불가); 모든 IntegrityError를 409로 매핑; db.py가 schemas를 import함; 목록은 배열 + 헤더 |

1. 713e65a1, 081fe80d, 914d71d5, cfb2caca
5. a2113356
6. 1bab0640
7. 272d0a4b, 357c708d, 58ed1535, bf97b119
11. 6e4089be, c877fbe5, e9c0ab20, f6032ba6
15. 72989b3e

## s2-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0968d80f | 5 | 4 | 4 | 5 | 5 | 4 | 가장 간결하고 코드와 정확히 일치(메서드 미검사, fallback 404, 별칭), 다만 lockfile/npm ci·배포·문제 해결 안내가 없어 다소 얇음 |
| 3b930054 | 5 | 5 | 4 | 3 | 3 | 4 | 내용은 정확·충실하나 usage가 README의 설치/실행을 다시 반복하고 Vercel CLI 등 일반 내용으로 길어짐 |
| 4f795934 | 5 | 5 | 5 | 3 | 4 | 4 | 화면 둘러보기·dev/prod 차이 표 등 충실하고 정확하나 AGENTS.md(node_modules 경로)·React 19 업그레이드 등 부수 내용이 많아 김 |
| 547b5dae | 5 | 5 | 5 | 4 | 5 | 5 | README 간결, usage에 렌더링 방식·API 200/500·데이터 수정 반영 시점·컴포넌트 props 표까지 정확, 분담 깔끔 |
| 5eb6d7e1 | 5 | 5 | 5 | 5 | 5 | 5 | 짧은 README + 핵심만 담은 usage, 데이터 흐름·필드 추가 절차·배포·문제 해결 모두 코드와 일치, 중복 거의 없음 |
| 6e08ba3d | 4 | 5 | 5 | 5 | 5 | 4 | 간결하고 통찰 있음(API도 재빌드 필요, ListItem as 레거시, fallback blocking) 다만 `agentRules: false` 설정은 근거 확인 불가한 주장 |
| 8e2fc040 | 5 | 5 | 5 | 4 | 4 | 4 | 정확하고 친절하나 README '알려진 주의 사항'과 USAGE 문제 해결이 TS 경고·latest 내용을 중복 |
| 97941275 | 5 | 5 | 5 | 4 | 5 | 5 | dev/start별 반영 시점 표, API 응답 표, 컴포넌트·tsconfig 표 등 정확하고 정리 잘 됨, 제약 사항 명시 |
| bae321aa | 5 | 5 | 5 | 4 | 5 | 5 | 정확(API 파일 기준 상대경로 ../../../ 정확), fallback 변경 시 notFound 처리 등 실질적 안내, 구성 명료 |
| c83bb6ad | 5 | 5 | 5 | 3 | 4 | 4 | 정확·완전하고 소스 링크까지 있으나 README가 가장 길고 AGENTS.md 등 앱과 무관한 내용이 README에 들어감 |
| cbe55220 | 4 | 5 | 5 | 4 | 4 | 4 | 충실하고 대체로 정확하나 `agentRules` 설정·Turbopack 등 검증 불가 주장, README 기술 스택 표와 usage 문제 해결이 일부 중복 |
| e5020c17 | 5 | 5 | 4 | 3 | 3 | 4 | 정확하지만 usage가 설치/실행을 반복하고 Vercel CLI 설치·참고 링크 등 일반적 내용이 많음 |
| eb6958b1 | 5 | 5 | 5 | 4 | 4 | 4 | 정확하고 문제 해결 표가 유용하나 usage '개발과 빌드'가 README 스크립트와 겹침 |
| f788b3ce | 5 | 5 | 5 | 4 | 5 | 5 | 화면별 실제 표시 문구까지 코드와 일치, 데이터 소스 교체 시 ISR/fallback/SSR 선택지 안내, 분담 명확 |
| fc748a95 | 5 | 5 | 5 | 4 | 5 | 5 | 앱 둘러보기·API 레퍼런스·추가 방법·문제 해결이 정확하고 README와 중복이 적음 |

1. 5eb6d7e1
2. f788b3ce, 547b5dae, 97941275, bae321aa, fc748a95
7. 6e08ba3d
8. 0968d80f, eb6958b1, 8e2fc040
11. cbe55220, c83bb6ad, 4f795934
14. 3b930054, e5020c17

## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 60e066af | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled (day-first, x100 fixed, conflicting IDs rejected, future dates blanked); per-fix counts plus an Assumptions section in the report; tests; nothing missed |
| 737c52e8 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled; fix table gives field/issue/rows/action including the dd/mm/yyyy reading and counts pre-dedupe (stated); full revenue breakdowns; nothing missed |
| 3d74461c | 5 | 4 | 5 | 5 | 5 | 5 | All 10 handled; catalog table, quality_flags column, revenue by month/country/category/product; day-first rule only in docstring; normalizations shown as variant counts, not rows |
| 450cb7b8 | 5 | 4 | 5 | 5 | 5 | 5 | All 10 handled; per-column change counts and a note on why negatives are not returns; day-first rule only in a code comment, not in the report |
| 00043363 | 5 | 4 | 4 | 5 | 5 | 4 | All 10 handled, but the x100 prices are rejected as "unit_price_mismatch" without explaining x100; day-first only in a code comment; no overall revenue total |
| aab41525 | 5 | 5 | 4 | 4 | 5 | 4 | All 10 handled, with a per-cell issues.csv; conflicting IDs keep the first row (arbitrary, though stated); fix table split by list price; duplicate count shows 11 in one place and 12 in another |
| 60fd776d | 5 | 4 | 5 | 4 | 5 | 4 | All 10 handled; conflicting IDs go to the settled status (stated rule); fix counts taken over raw rows before dedupe, not stated, so they disagree with the gaps table; day-first only in a code comment |
| 949170dd | 5 | 4 | 5 | 5 | 4 | 4 | All 10 handled, with day-first in the Assumptions; invalid quantities are blanked but the rows stay in the clean CSV (37 without line_total); prices written as 4.2; normalizations not counted; says "six date formats" when there are four |
| a76e350c | 5 | 4 | 5 | 5 | 4 | 4 | All 10 handled; the cleaning-steps log has counts; conflicting IDs go to the most advanced status; no rejected file, and 37 rows with blank quantity stay in the clean CSV; day-first only in the docstring |
| ecac6d58 | 5 | 4 | 5 | 5 | 4 | 4 | All 10 handled, with the day-first rule stated in the report; spelling normalizations not counted; rows with blank quantity kept; prices written as 4.2 |
| 7a53b92f | 5 | 4 | 5 | 4 | 4 | 4 | All 10 handled; conflicting duplicates go to the latest lifecycle status and are listed only in the report, not in the rejected CSV; report tables are to_string code blocks; normalizations not counted; paths relative to cwd |
| a1d830dd | 5 | 4 | 4 | 5 | 4 | 4 | All 10 handled; status table has counts but no value; normalizations not counted; day-first only in the docstring; rows with blank quantity kept |
| e2e1ba0a | 5 | 4 | 4 | 5 | 4 | 4 | All 10 handled, but the 2027 dates are only flagged and stay in the clean CSV; day-first only in a code comment; status table mixes rows with and without a total |
| ef244040 | 5 | 4 | 4 | 4 | 4 | 4 | All 10 handled; status table has counts only; normalizations not counted; parse_discount would raise on bad input; day-first only in a code comment; prices written as 4.2 |
| ff28ad80 | 5 | 3 | 4 | 4 | 4 | 4 | All 10 handled, but the report says normalizations are "not counted" and never states the day-first rule (only DD/MM/YYYY in the docstring); clean CSV has a source_line column and 4.2-style prices |

1. 60e066af, 737c52e8
3. 3d74461c, 450cb7b8
5. 00043363, aab41525, 60fd776d, 949170dd, a76e350c, ecac6d58
11. 7a53b92f, a1d830dd, e2e1ba0a
14. ef244040
15. ff28ad80

