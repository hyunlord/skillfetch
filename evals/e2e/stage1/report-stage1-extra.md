# skillfetch 1단계 — 추가 집계 (선택 일치, 턴/도구 분포)

데이터: `runs/_extract.json` + 세션 jsonl. 표 생성 `scripts/report_s1_extra.py`. 1)의 판정 열만 수기.

## 1. 선택 일치: C가 로드한 스킬 vs B의 전문가 스킬 (전문가 태스크 15개 × C 2회)

판정: **같음** = 같은 id 집합 · **동급** = 집합은 다르지만(전문가 세트 ⊂ C 세트 포함) 전문가 세트가 이 태스크에 대해 다루는 내용을 C 세트도 다룸 · **다름** = 다루지 않음 · **로드 없음** = C가 로드하지 않음(search 미호출 또는 search만).

| 태스크 | run | B 전문가 스킬 | C 로드 스킬 | C 체인 | 전문가 스킬이 C search 상위 10에 있었나 | 판정 | 근거 |
|---|---|---|---|---|---|---|---|
| s1-fa-01 | r1 | `uasl/api-design` | `fastapi(local)`, `sqlmodel(local)` | search+resolve+load | `uasl/api-design` #7 | **동급** | fastapi(local)의 `Annotated`/`Query`·`Field` 제약 선언이 허용값 외 422를 다룸. api-design의 정렬 파라미터 관례(`?sort=-created_at`)는 없음. |
| s1-fa-01 | r2 | `uasl/api-design` | - | none | search 안 함 | **로드 없음** |  |
| s1-fa-02 | r1 | `uasl/postgresql-table-design` | `sqlmodel(local)`, `fastapi(local)` | search+resolve+load | 없음 | **다름** | B(postgresql-table-design)는 행이 있는 테이블의 NOT NULL+default 컬럼 추가(safe schema evolution)를 다룸. sqlmodel(local)은 "Changing the model does not alter existing columns" 한 줄뿐, alembic 없음. |
| s1-fa-02 | r2 | `uasl/postgresql-table-design` | - | search | 없음 | **로드 없음** |  |
| s1-fa-03 | r1 | `uasl/shadcn` | `uasl/design-to-code` | search+resolve+load | 없음 | **동급** | design-to-code "prioritizing alignment with … the existing project … reusable components"가 '기존 UI 컴포넌트 스타일에 맞춰' 부분을 다룸. shadcn 컴포넌트·CLI 규칙은 없음. |
| s1-fa-03 | r2 | `uasl/shadcn` | `uasl/design-to-code` | search+resolve+load | 없음 | **동급** | r1과 같은 스킬. |
| s1-fa-04 | r1 | `uasl/refactoring-patterns` | - | none | search 안 함 | **로드 없음** |  |
| s1-fa-04 | r2 | `uasl/refactoring-patterns` | - | none | search 안 함 | **로드 없음** |  |
| s1-fa-05 | r1 | `uasl/python-design-patterns` | `fastapi(local)` | search+resolve+load | `uasl/python-design-patterns` #10 | **동급** | fastapi(local) Dependency Injection 절 "Use dependencies when the logic … is shared across endpoints"가 공통 페이지네이션 의존성에 해당. B는 일반 DI(생성자 주입). |
| s1-fa-05 | r2 | `uasl/python-design-patterns` | - | none | search 안 함 | **로드 없음** |  |
| s1-fa-06 | r1 | `uasl/integration-testing` | `uasl/python-testing-patterns` | search+resolve+load | `uasl/integration-testing` #6 | **동급** | python-testing-patterns의 pytest fixture·격리 패턴이 B(integration-testing)의 API+DB 테스트 범위를 다룸. Testcontainers/CI 절은 없음. |
| s1-fa-06 | r2 | `uasl/integration-testing` | `uasl/radar` | search+resolve+load | `uasl/integration-testing` #5 | **다름** | radar 본문은 테스트 일반 규칙 + 에이전트 핸드오프 프로토콜. B의 API 통합 테스트·DB 정리 패턴 없음. |
| s1-fa-07 | r1 | `uasl/python-testing-patterns` | `uasl/python-testing-patterns` | search+resolve+load | `uasl/python-testing-patterns` #7 | **같음** |  |
| s1-fa-07 | r2 | `uasl/python-testing-patterns` | `fastapi(local)` | search+resolve+load | `uasl/python-testing-patterns` #7 | **다름** | fastapi(local)에는 테스트 내용 없음. B(python-testing-patterns)의 예외·monkeypatch·에러 경로 테스트 패턴 없음. |
| s1-fa-08 | r1 | `uasl/defense-in-depth`, `uasl/api-design` | `fastapi(local)`, `uasl/fastapi-endpoint` | search+resolve+load | `uasl/api-design` #5 | **동급** | fastapi(local) Pydantic `Field` 검증 + fastapi-endpoint의 Pydantic 스키마가 null 입력을 API 계층에서 막는 부분을 다룸. defense-in-depth의 계층별 검증 원칙, api-design의 422 상태코드 표는 없음. |
| s1-fa-08 | r2 | `uasl/defense-in-depth`, `uasl/api-design` | `fastapi(local)`, `sqlmodel(local)` | search+resolve+load | `uasl/api-design` #8 | **동급** | fastapi(local) `Field` 검증 + sqlmodel(local) Creates and Updates(`exclude_unset`)가 같은 부분을 다룸. 계층별 검증 원칙·상태코드 표는 없음. |
| s1-fa-10 | r1 | `uasl/quill` | - | search | 없음 | **로드 없음** |  |
| s1-fa-10 | r2 | `uasl/quill` | - | none | search 안 함 | **로드 없음** |  |
| s1-nx-02 | r1 | `uasl/backend-patterns`, `uasl/api-design` | `uasl/next-best-practices`, `uasl/api-design` | search+resolve+load | `uasl/backend-patterns` #1, `uasl/api-design` #8 | **동급** | api-design 공통(1/2). backend-patterns 대신 next-best-practices(App Router 하위 문서 링크; Route Handlers는 App Router 기준). |
| s1-nx-02 | r2 | `uasl/backend-patterns`, `uasl/api-design` | `uasl/next-best-practices`, `uasl/api-design` | search+resolve+load | `uasl/backend-patterns` #1, `uasl/api-design` #8 | **동급** | r1과 같은 세트. |
| s1-nx-04 | r1 | `uasl/responsive-design` | `uasl/responsive-design`, `uasl/vercel-react-best-practices` | search+resolve+load | `uasl/responsive-design` #1 | **동급** | B 세트 포함 + vercel-react-best-practices. |
| s1-nx-04 | r2 | `uasl/responsive-design` | `uasl/responsive-design`, `uasl/vercel-react-best-practices` | search+resolve+load | `uasl/responsive-design` #1 | **동급** | r1과 같은 세트. |
| s1-nx-06 | r1 | `uasl/refactoring-patterns` | `uasl/next-best-practices` | search+resolve+load | 없음 | **다름** | next-best-practices(App Router 링크 목록)는 B(refactoring-patterns)의 동작 보존 리팩토링 절차를 다루지 않음. |
| s1-nx-06 | r2 | `uasl/refactoring-patterns` | `uasl/zen`, `uasl/next-best-practices` | search+resolve+load | 없음 | **동급** | zen "refactor code … while preserving behavior … verifying changes"가 refactoring-patterns의 동작 보존·검증 부분을 다룸. 본문 다수가 핸드오프 프로토콜. |
| s1-nx-07 | r1 | `uasl/tdd-workflow` | `uasl/unit-testing` | search+resolve+load | 없음 | **동급** | unit-testing과 tdd-workflow 모두 일반 테스트 스킬, Vitest 설정 예시 있음. React Testing Library 예시는 tdd-workflow에만 있음. |
| s1-nx-07 | r2 | `uasl/tdd-workflow` | `uasl/tdd-workflow` | search+resolve+load | `uasl/tdd-workflow` #9 | **같음** |  |
| s1-nx-08 | r1 | `uasl/unit-testing` | `uasl/radar`, `uasl/typescript-unit-testing` | search+resolve+load | `uasl/unit-testing` #1 | **동급** | typescript-unit-testing(TS 단위 테스트, Jest/NestJS 지향) + radar가 B(unit-testing)의 TS 단위 테스트 부분을 다룸. |
| s1-nx-08 | r2 | `uasl/unit-testing` | `uasl/radar` | search+resolve+load | `uasl/unit-testing` #3 | **동급** | radar(테스트 추가 일반 규칙, JS/TS 지원)가 B(unit-testing, 다언어 일반 단위 테스트)와 같은 수준의 일반 규칙을 다룸. |
| s1-nx-10 | r1 | `uasl/quill` | `uasl/quill` | search+resolve+load | `uasl/quill` #3 | **같음** |  |
| s1-nx-10 | r2 | `uasl/quill` | - | none | search 안 함 | **로드 없음** |  |

집계(30 run): 같음 3 · 동급 15 · 다름 4 · 로드 없음 8

## 2. C의 추가 턴: 도구 호출 분포와 스킬 로드 전 턴

메시지 = 메인 스레드 assistant 메시지 1개(같은 메시지 안 병렬 도구 호출 포함). `num_turns` = result 이벤트 값. 체인 메시지 = `Skill(skillfetch-router)`, `ToolSearch`, `mcp__skillfetch__*` 중 하나라도 포함한 메시지.

### 세션당 평균 도구 호출 수 — 전문가 태스크 15개

| 조건 | 세션 | num_turns | 메시지 | 체인 메시지 | 체인 외 메시지 | 첫 Edit/Write 메시지 순번(중앙) | Bash | Edit | Read | Write | Grep | Skill | Glob | ToolSearch | sf:profile_repo | sf:search_skills | sf:resolve_set | sf:load_skills |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 30 | 14.6 | 10.6 | 0.00 | 10.60 | 4.0 | 6.70 | 2.90 | 2.33 | 0.87 | 0.60 | 0.17 | 0.10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| B | 30 | 16.1 | 11.7 | 0.00 | 11.70 | 5.0 | 7.77 | 2.90 | 2.40 | 0.80 | 0.87 | 0.13 | 0.33 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C | 30 | 21.0 | 15.6 | 4.67 | 10.97 | 10.0 | 7.17 | 3.17 | 2.43 | 0.80 | 0.57 | 0.93 | 0.47 | 0.80 | 0.80 | 0.80 | 0.73 | 0.73 |

Skill 도구 호출(조건, 스킬): A·`fastapi` 5, B·`fastapi` 2, B·`sqlmodel` 2, C·`fastapi` 3, C·`skillfetch-router` 24, C·`sqlmodel` 1

### 세션당 평균 도구 호출 수 — 전체 20개

| 조건 | 세션 | num_turns | 메시지 | 체인 메시지 | 체인 외 메시지 | 첫 Edit/Write 메시지 순번(중앙) | Bash | Edit | Read | Write | Grep | Skill | Glob | ToolSearch | sf:profile_repo | sf:search_skills | sf:resolve_set | sf:load_skills |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 40 | 13.8 | 10.2 | 0.00 | 10.22 | 4.0 | 6.58 | 2.75 | 1.98 | 0.75 | 0.53 | 0.15 | 0.15 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C | 40 | 19.9 | 14.9 | 4.55 | 10.38 | 9.0 | 6.62 | 3.20 | 2.52 | 0.72 | 0.55 | 0.88 | 0.47 | 0.78 | 0.78 | 0.78 | 0.72 | 0.72 |

Skill 도구 호출(조건, 스킬): A·`fastapi` 5, A·`sqlmodel` 1, B·`fastapi` 2, B·`sqlmodel` 2, C·`fastapi` 3, C·`skillfetch-router` 31, C·`sqlmodel` 1

### C: 스킬 로드 전 턴 (load_skills 호출이 있는 C 세션)

| 세션 | 메시지 총수 | load_skills가 든 메시지 순번 | 그 전 메시지 | 그 전 체인 메시지 | 그 전 체인 외 메시지 | 체인 외 메시지에서 쓴 도구 |
|---|---|---|---|---|---|---|
| s1-fa-01-r1 | 23 | 8 | 7 | 5 | 2 | Glob×1, Bash×1 |
| s1-fa-02-r1 | 22 | 7 | 6 | 5 | 1 | Glob×1 |
| s1-fa-03-r1 | 15 | 6 | 5 | 5 | 0 | - |
| s1-fa-03-r2 | 16 | 6 | 5 | 5 | 0 | - |
| s1-fa-05-r1 | 17 | 8 | 7 | 5 | 2 | Glob×1, Bash×1 |
| s1-fa-06-r1 | 25 | 7 | 6 | 5 | 1 | Glob×1 |
| s1-fa-06-r2 | 23 | 7 | 6 | 5 | 1 | Glob×1 |
| s1-fa-07-r1 | 18 | 7 | 6 | 5 | 1 | Glob×1 |
| s1-fa-07-r2 | 15 | 7 | 6 | 5 | 1 | Bash×1 |
| s1-fa-08-r1 | 20 | 8 | 7 | 5 | 2 | Glob×1, Bash×1 |
| s1-fa-08-r2 | 21 | 8 | 7 | 5 | 2 | Bash×2 |
| s1-fa-09-r1 | 24 | 7 | 6 | 5 | 1 | Glob×1 |
| s1-fa-09-r2 | 25 | 8 | 7 | 5 | 2 | Glob×1, Bash×2 |
| s1-nx-01-r1 | 12 | 6 | 5 | 5 | 0 | - |
| s1-nx-01-r2 | 12 | 6 | 5 | 5 | 0 | - |
| s1-nx-02-r1 | 12 | 6 | 5 | 5 | 0 | - |
| s1-nx-02-r2 | 12 | 6 | 5 | 5 | 0 | - |
| s1-nx-03-r1 | 12 | 6 | 5 | 5 | 0 | - |
| s1-nx-04-r1 | 11 | 6 | 5 | 5 | 0 | - |
| s1-nx-04-r2 | 11 | 6 | 5 | 5 | 0 | - |
| s1-nx-05-r1 | 11 | 6 | 5 | 5 | 0 | - |
| s1-nx-05-r2 | 11 | 6 | 5 | 5 | 0 | - |
| s1-nx-06-r1 | 14 | 6 | 5 | 5 | 0 | - |
| s1-nx-06-r2 | 15 | 6 | 5 | 5 | 0 | - |
| s1-nx-07-r1 | 24 | 6 | 5 | 5 | 0 | - |
| s1-nx-07-r2 | 25 | 6 | 5 | 5 | 0 | - |
| s1-nx-08-r1 | 16 | 6 | 5 | 5 | 0 | - |
| s1-nx-08-r2 | 13 | 6 | 5 | 5 | 0 | - |
| s1-nx-10-r1 | 10 | 6 | 5 | 5 | 0 | - |

- n=29: load 전 메시지 중앙 5 (범위 5–7), 평균 5.55 = 체인 5.00 + 체인 외 0.55
- C 세션당 체인 메시지: search 호출 세션 5.87 (n=31), 미호출 세션 0 (n=9)
- 체인 순서: 29세션 `Skill(skillfetch-router)` → `ToolSearch` → `profile_repo` → `search_skills` → `resolve_set` → `load_skills`, 2세션 `… → search_skills`에서 멈춤 (search 호출 31세션 전부)
