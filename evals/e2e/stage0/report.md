# skillfetch 실사용 테스트 0단계 — 라우터 발화 측정 (report)

실행일 2026-10-22 (KST 15:34–15:44). 숫자는 `scripts/extract.py`가 `runs/<id>.jsonl`에서 추출, 표는 `scripts/report.py`가 생성. 적합성·준수·결과 판정 열만 수기.

## 0. 조건 (기록)

| 항목 | 값 |
|---|---|
| 하네스 루트 | `<e2e>` (지시의 `~/skillfetch-e2e/`는 존재하지 않아 현재 디렉터리 사용) |
| Claude Code | 2.1.280, 모델 기본값 → init `claude-opus-5-5[1m]` (사용자 설정 `model: opus[1m]`, effort high). 구독 플랜, `ANTHROPIC_API_KEY` 없음 |
| 실행 명령 | `claude -p "<task>" --output-format stream-json --verbose --max-turns 25 --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*"` — `--verbose`는 print 모드 stream-json 필수 옵션이라 추가. stdin=/dev/null. 동시 4세션 |
| skillfetch | `uvx --from git+https://github.com/hyunlord/skillfetch` — 시작 시 HEAD `ccb5abd`, 종료 시 `9afa309` (실행 중 push됨; 두 커밋 차이는 README.md 1개 파일뿐) |
| 인덱스 | `skillfetch sync` 시점(준비 단계) `index-2026-10-22` built 2026-10-22T04:45:24Z. **실행 도중 15:36:26 KST에 `~/.skillfetch/index`가 외부에서 교체됨** (파일 mtime, `manifest.built_at` = 2026-10-22T06:15:43Z; 이 하네스가 한 것 아님). 서버는 시작 시 인덱스를 읽으므로 15:36:26 이전 시작 세션(fa-01, fa-02, fa-03, fa-04, fa-10)은 04:45 빌드, 나머지 15세션은 06:15 빌드 |
| 라우터 스킬 | `assets/router-skill/SKILL.md` (main) → 각 레포 `.claude/skills/skillfetch-router/SKILL.md` |
| MCP | 각 레포 `claude mcp add -s project skillfetch -- uvx --from git+… skillfetch serve` → `.mcp.json`. init 시점 skillfetch 상태: `pending` 13 / `connected` 7 (세션별 값은 요약 표 'init MCP' 열). `connected`면 init `tools`에 `mcp__skillfetch__*` 4개가 이미 있고, `pending`이면 없음. 발화 7세션은 모두 `ToolSearch`로 skillfetch 도구를 로드한 뒤 호출 |
| fastapi 레포 | `fastapi/full-stack-fastapi-template` @ `b1125d88`, 베이스라인(라우터+.mcp.json 커밋) `91132287`. 기존 테스트 58 pass. 레포 자체에 `.claude/skills/{library-skills, fastapi→.venv 심볼릭, sqlmodel→.venv 심볼릭}` 포함(업스트림 tracked; `uv sync` 후 활성). CLAUDE.md 없음 |
| nextjs 레포 | `vercel/next.js` `examples/with-typescript` @ `fa3830c4`를 독립 레포로 복사(npm install + 첫 build 후 커밋 `76de3ce2`), 베이스라인 `415e4893`. next 16.4.2, react 18.3.1. 테스트 러너 없음 → 기존 검사 = `npm run type-check` + `next build` 통과. CLAUDE.md 없음 |
| 격리 | 태스크마다 `git worktree` (`~/skillfetch-e2e-wt/<id>`, 하네스 루트 밖 — 하네스 디렉터리의 `.claude/settings.local.json`이 섞이지 않게). 세션 전 `uv sync`/`npm ci` 선실행 |
| DB | Docker 데몬 미실행 → 하네스 전용 Postgres 16 (`infra/pgdata`, :55432), 태스크별 DB `app_<id>` + alembic upgrade. 세션 env에 `DATABASE_URL`만 주입 (`.env`는 5432 그대로). `FASTAPI_ENV`는 주입 안 함 |
| 사용자 전역 환경 (그대로 상속) | `~/.claude/CLAUDE.md`, <E2 plugin> 12개, <E2 hook>, <E2 MCP server> 4개. init `skills` 목록 137개(fastapi)/134개(nextjs) 중 skillfetch-router 포함 |
| 도구 승인 | 20세션 모두 `permission_denials: []`. `Skill`·`ToolSearch`는 allowedTools에 없지만 거부 없이 실행됨. 승인 대기로 멈춘 세션 없음 |

## 1. 발화율

- 비트리비얼 17개 중 `search_skills` 호출 세션: **7/17** (fa-01, fa-02, fa-05, fa-06, nx-03, nx-05, nx-06)
- 트리비얼 3개(fa-10, nx-09, nx-10) 중 호출(오발화): **0/3**
- `Skill(skillfetch-router)` 호출 세션: 7/20 — 발화 7세션 모두 search 전에 Skill(skillfetch-router) 호출, 미발화 13세션은 0회
- 레포별: fastapi 비트리비얼 9개 중 4 (fa-01, 02, 05, 06) / nextjs 비트리비얼 8개 중 3 (nx-03, 05, 06)
- 종류별(비트리비얼): feature 2/4, refactor 1/4, test 4/4, bugfix 0/3, docs 0/2
- 언어별(비트리비얼): en 3/9, ko 4/8
- init MCP `pending`인 비트리비얼 세션 중 발화: 6/12
- init MCP `connected`인 비트리비얼 세션 중 발화: 1/5
- 라우터 외 Skill 호출: fa-01→`fastapi`, fa-03→`sqlmodel` (레포 내장 `.claude/skills/` 스킬)

## 2. 체인 완주

| 세션 | ToolSearch | profile_repo | search_skills | resolve_set | load_skills | load errors | 끊긴 지점 |
|---|---|---|---|---|---|---|---|
| fa-01 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| fa-02 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| fa-05 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| fa-06 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| nx-03 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| nx-05 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |
| nx-06 | 1 | 1 | 1 | 1 | 1 | 0 | 없음 (완주) |

- search → resolve_set → load_skills 완주: **7/7** (발화 세션 기준), 17개 기준 7/17
- search만 하고 미로드 0, resolve 에러 0 (`errors: []`, `excluded: []`, `warnings: []` 전부), load 실패 0
- 모든 search_skills 호출에 `profile_repo` 결과를 `profile`로 전달함. fastapi 레포 profile: `frameworks: []`, `languages: [javascript, python]`, `package_managers: [bun, uv]` (FastAPI 미검출)
- fa-02: search 결과 10개 중 아무것도 고르지 않고 `auto_ids: []`, `pinned_ids: [path:…/.venv/…/fastapi/.agents/skills/fastapi, path:…/sqlmodel/.agents/skills/sqlmodel]`로 resolve. resolve notes: `no extracted constraints (run skillfetch ingest … --with-api); included without conflict checks` ×2
- fa-02 세션 텍스트 인용: “The search results from the skillfetch skill index assumed async SQLAlchemy, which this sync SQLModel codebase doesn't use”

## 3. 쿼리 품질 (search_skills에 넘긴 query 전부)

| 세션 | 언어 | 원 태스크 | query | 영어 재서술 |
|---|---|---|---|---|
| fa-01 | ko | 로그인 엔드포인트에 rate limit 붙여줘 | Add rate limiting to the FastAPI login access-token endpoint in backend/app/api/routes/login.py to prevent brute-force attacks | 예 |
| fa-02 | en | Add a case-insensitive title search query parameter to GET /api/v1/items/. | Add a case-insensitive title search query parameter to the FastAPI GET /api/v1/items/ endpoint using SQLModel in backend/app/api/routes/items.py | (원문 영어) |
| fa-05 | en | Add tests for the password reset flow. | Add pytest tests for the FastAPI password reset flow (password-recovery and reset-password endpoints) in backend/tests/api/routes/test_login.py using TestClient and SQLModel | (원문 영어) |
| fa-06 | ko | 아이템 목록 API의 skip/limit 페이지네이션 동작 테스트 작성해줘 | Write pytest tests for skip/limit pagination of the FastAPI items list endpoint in backend/tests/api/routes/test_items.py using SQLModel and TestClient | 예 |
| nx-03 | ko | users 페이지들을 pages 라우터에서 App Router로 옮겨줘 | Migrate the Next.js TypeScript users pages (pages/users/index.tsx and pages/users/[id].tsx using getStaticProps/getStaticPaths) from the Pages Router to the App Router | 예 |
| nx-05 | en | Add unit tests for the List and ListItem components. | Add unit tests for the React List and ListItem components in components/ of a Next.js TypeScript app using Jest and React Testing Library | (원문 영어) |
| nx-06 | ko | /api/users API 핸들러 테스트 작성해줘 | Write unit tests for the Next.js Pages Router API route handler in pages/api/users/index.ts using TypeScript | 예 |

- 세션당 search_skills 호출 1회 (재검색 0). 한국어 발화 4세션(fa-01, fa-06, nx-03, nx-06) 모두 영어 1문장으로 재서술, 4개 모두 대상 파일 경로 포함.

## 4. 선택 적합성

| 세션 | 태스크 | 로드된 스킬 | search 결과 내 순위 | token_estimate | 판정 | 근거 |
|---|---|---|---|---|---|---|
| fa-01 | 로그인 엔드포인트에 rate limit 붙여줘 | `uasl/api-design@bba608f8c974` | 4/10 | 3218 | **적합** | 본문에 Rate Limiting 절(429, Retry-After, X-RateLimit-* 헤더, 티어 표)이 있음. 예시는 언어 중립. |
| fa-02 | Add a case-insensitive title search query parameter to GET /api/v1/items/. | `path:…/fastapi/.agents/skills/fastapi` | 검색 결과 밖 (pinned) | 2451 | **적합** | Query 파라미터를 `Annotated`로 선언하라는 규칙이 이 태스크(쿼리 파라미터 추가)에 직접 해당. 인덱스 결과가 아니라 레포 .venv 안의 로컬 스킬을 pinned로 넣음. |
| fa-02 | Add a case-insensitive title search query parameter to GET /api/v1/items/. | `path:…/sqlmodel/.agents/skills/sqlmodel` | 검색 결과 밖 (pinned) | 2000 | **적합** | `session.exec(select(...))`·`col()` 쿼리 작성 규칙이 title 필터 쿼리 작성에 해당. 로컬 pinned 스킬. |
| fa-05 | Add tests for the password reset flow. | `uasl/radar@a47ea6fd5f95` | 7/10 | 2635 | **모호** | 테스트 추가 일반 규칙(변경 전후 테스트 실행, AAA, 50줄)은 해당되나, 본문 상당 부분이 다른 에이전트(Scout/Builder/Voyager)로의 라우팅·NEXUS_HANDOFF·AUTORUN 프로토콜이고 `references/` 파일 참조는 로드되지 않음. |
| fa-06 | 아이템 목록 API의 skip/limit 페이지네이션 동작 테스트 작성해줘 | `uasl/python-testing-patterns@e62d0f1ca316` | 5/10 | 6213 | **적합** | pytest fixture·parametrize·AAA 패턴 중심. pytest 기반 페이지네이션 테스트 작성에 해당. |
| nx-03 | users 페이지들을 pages 라우터에서 App Router로 옮겨줘 | `uasl/next-best-practices@ee058f89acea` | 8/10 | 942 | **모호** | 주제(App Router, async params, metadata)는 맞으나 본문 942토큰 대부분이 `See [async-patterns.md](./async-patterns.md)` 형태의 하위 문서 링크이고, 세션은 그 하위 파일을 읽지 않음. |
| nx-05 | Add unit tests for the List and ListItem components. | `uasl/unit-testing@6c5fbb821103` | 2/10 | 5809 | **모호** | Vitest/Jest AAA 예시는 해당되나 5809토큰 중 대부분이 C#/Java/Go/Python 절이고 React 컴포넌트 렌더링(Testing Library) 내용은 없음. |
| nx-06 | /api/users API 핸들러 테스트 작성해줘 | `uasl/radar@a47ea6fd5f95` | 5/10 | 2635 | **모호** | fa-05와 동일 스킬. 테스트 추가 규칙은 해당, 라우팅/핸드오프 프로토콜 비중이 큼. |
| nx-06 | /api/users API 핸들러 테스트 작성해줘 | `uasl/tdd-workflow@6eadb0bf0ea8` | 4/10 | 2357 | **모호** | Next.js API route 통합 테스트 예시(`NextRequest`, App Router `route.ts`)가 있으나 핵심 규칙 '테스트 먼저 쓰고 구현'은 기존 코드에 테스트만 추가하는 태스크와 맞지 않음. 예시는 Pages Router 핸들러(이 레포)와 형태가 다름. |

- 집계(스킬-태스크 쌍 9개): 적합 4 / 부적합 0 / 모호 5
- 각 세션 search 결과 상위 10개 id는 `runs/_extract.json`의 `search_calls[].result`에 전부 있음.

## 5. 비용

입력 토큰 = `usage.input_tokens + cache_creation_input_tokens + cache_read_input_tokens` (result 이벤트). 턴 = result `num_turns`. 시간 = result `duration_ms` / 하네스 측정 벽시계. load 토큰 = load_skills 응답의 `skills[].token_estimate` 합 (skillfetch 자체 추정치), 괄호는 응답 전체 문자 수.

| 세션 | 발화 | 턴 | 입력 합계 | (uncached / cache write / cache read) | 출력 | duration_ms | 벽시계 s | API 환산 $ | load_skills 토큰 |
|---|---|---|---|---|---|---|---|---|---|
| fa-01 | Y | 30 | 1,768,075 | 34 / 105,885 / 1,662,156 | 10,381 | 165,416 | 175.9 | 1.39 | 3,218 (14,090 chars) |
| fa-02 | Y | 26 | 1,908,409 | 40 / 94,735 / 1,813,634 | 8,338 | 179,297 | 189.0 | 1.29 | 4,451 (19,512 chars) |
| fa-03 | - | 19 | 1,161,866 | 26 / 82,700 / 1,079,140 | 5,338 | 113,855 | 124.4 | 0.98 | - |
| fa-04 | - | 14 | 762,608 | 18 / 76,681 / 685,909 | 4,927 | 104,726 | 115.1 | 0.85 | - |
| fa-05 | Y | 26 | 2,543,302 | 50 / 104,558 / 2,438,694 | 13,411 | 229,651 | 234.5 | 1.59 | 2,635 (11,267 chars) |
| fa-06 | Y | 30 | 1,977,674 | 38 / 101,036 / 1,876,600 | 9,931 | 161,872 | 167.0 | 1.38 | 6,213 (27,299 chars) |
| fa-07 | - | 11 | 664,539 | 16 / 67,046 / 597,477 | 2,946 | 44,114 | 48.0 | 0.71 | - |
| fa-08 | - | 13 | 1,029,251 | 24 / 72,219 / 957,008 | 5,034 | 69,943 | 73.9 | 0.87 | - |
| fa-09 | - | 9 | 679,143 | 16 / 68,516 / 610,611 | 3,099 | 37,001 | 41.0 | 0.73 | - |
| fa-10 | - | 6 | 479,453 | 12 / 81,086 / 398,355 | 834 | 27,608 | 33.6 | 0.75 | - |
| nx-01 | - | 9 | 491,041 | 12 / 65,144 / 425,885 | 1,892 | 29,736 | 33.9 | 0.64 | - |
| nx-02 | - | 11 | 404,960 | 10 / 71,028 / 333,922 | 1,942 | 32,594 | 36.4 | 0.67 | - |
| nx-03 | Y | 23 | 1,223,030 | 26 / 86,737 / 1,136,267 | 8,674 | 121,437 | 125.3 | 1.09 | 942 (4,457 chars) |
| nx-04 | - | 10 | 501,995 | 12 / 65,785 / 436,198 | 1,834 | 34,521 | 38.8 | 0.65 | - |
| nx-05 | Y | 24 | 1,625,604 | 34 / 86,820 / 1,538,750 | 5,856 | 180,686 | 184.7 | 1.12 | 5,809 (24,839 chars) |
| nx-06 | Y | 27 | 1,813,863 | 38 / 96,928 / 1,716,897 | 9,538 | 132,310 | 136.8 | 1.31 | 4,992 (21,386 chars) |
| nx-07 | - | 6 | 397,831 | 10 / 68,538 / 329,283 | 1,262 | 27,609 | 32.2 | 0.64 | - |
| nx-08 | - | 5 | 411,784 | 10 / 72,909 / 338,865 | 2,139 | 26,922 | 30.8 | 0.69 | - |
| nx-09 | - | 6 | 325,281 | 8 / 63,562 / 261,711 | 1,993 | 30,026 | 33.5 | 0.60 | - |
| nx-10 | - | 7 | 405,766 | 10 / 62,187 / 343,569 | 1,058 | 23,644 | 27.1 | 0.59 | - |

| 집단 | n | 평균 턴 | 평균 입력 | 평균 출력 | 평균 duration_ms | 평균 load 토큰 |
|---|---|---|---|---|---|---|
| 발화(비트리비얼) | 7 | 26.6 | 1,837,137 | 9,447 | 167,238 | 4,037 |
| 미발화(비트리비얼) | 10 | 10.7 | 650,502 | 3,041 | 52,102 | 0 |
| 트리비얼 | 3 | 6.3 | 403,500 | 1,295 | 27,093 | 0 |

- 비용은 구독 플랜 실행이라 실제 과금 아님; `total_cost_usd`는 Claude Code가 보고한 API 환산값 그대로.
- `--max-turns 25`인데 result `num_turns`가 25를 넘은 세션: fa-01(30, success), fa-02(26, success), fa-05(26, error_max_turns), fa-06(30, success), nx-06(27, success). `error_max_turns`로 끝난 세션은 fa-05(num_turns 26)뿐.
- 서브에이전트 이벤트: nx-05에서만 2건 (parent_tool_use_id 있는 이벤트), 나머지 0.

## 6. 준수 (로드된 스킬 규칙 1개씩)

| 세션 | 스킬 | 확인한 규칙 | 판정 | 출력에서 확인한 사실 |
|---|---|---|---|---|
| fa-01 | api-design | 한도 초과 시 `429 Too Many Requests` + `Retry-After` 헤더 | **준수** | login.py diff: `status_code=status.HTTP_429_TOO_MANY_REQUESTS`, `headers={"Retry-After": ...}`; 테스트에서 `r.status_code == 429`, `int(r.headers["Retry-After"]) > 0` 검증. (같은 절의 X-RateLimit-* 헤더는 diff에 없음) |
| fa-02 | fastapi | 파라미터 선언은 `Annotated` 스타일 (`Query` 포함) | **준수** | items.py diff: `title: Annotated[ ... Query( ... description="Case-insensitive substring match on the item title"` |
| fa-05 | radar | Always: Run tests before and after changes | **준수** | load_skills 이후 첫 Edit 전에 `uv run pytest tests/api/routes/test_login.py` 실행(DB 없어 실패 → 세션이 자체 Postgres를 initdb로 띄운 뒤 재실행), Edit 후 `pytest tests/api/routes/test_login.py`·전체 스위트 실행. |
| fa-06 | python-testing-patterns | Pattern 3: 여러 입력 케이스는 `@pytest.mark.parametrize` | **준수** | test_items.py diff: `@pytest.mark.parametrize(("skip", "limit"), [pytest.param(0, 2, id="first-page"), ...` |
| nx-03 | next-best-practices | Async Patterns: Next.js 15+에서 `params`는 async (await) | **준수** | app/users/[id]/page.tsx diff: `params: Promise<{ id: string }>`, `const { id } = await params;` (generateMetadata·page 둘 다) |
| nx-05 | unit-testing | AAA (Arrange-Act-Assert) 구조 | **준수(구조상)** | List.test.tsx: 데이터 준비 → `render(...)` → 빈 줄 → `expect(...)` 순서. Arrange/Act/Assert 주석은 없음. |
| nx-06 | radar (precedence 1위) | Always: Run tests before and after changes | **부분** | 변경 전 테스트 실행 없음(레포에 테스트 러너가 없어 vitest를 먼저 설치), 테스트 작성 후 `npm test` 3회 실행. 2순위 tdd-workflow의 'Tests BEFORE Code'는 구현 변경이 없는 태스크라 확인 불가. |

## 7. 태스크 결과

세션 종료 후 하네스가 worktree에서 직접 실행: fastapi `uv run pytest tests/` (`FASTAPI_ENV=development`, 태스크 DB), nextjs `npm run type-check` + `next build` (+ `test` 스크립트가 생겼으면 `npm test`). 기존 = 베이스라인에서 수집된 58개 테스트 id. diff = 베이스라인 커밋 대비 (미추적 포함) — <E2 MCP server> 훅이 쓴 `.gitignore`/`.ignore` 블록과 `<E2 plugin>/` 상태 파일은 제외, lockfile 줄은 별도 열.

| 세션 | 기존 테스트 | 새 테스트 | type-check / build | diff +/- (정제) | lockfile +/- | 변경 파일 | 판정 |
|---|---|---|---|---|---|---|---|
| fa-01 | 58/58 pass | 2 pass | n/a | +126/-4 | - | 6 | 성공 |
| fa-02 | 58/58 pass | 5 pass | n/a | +120/-26 | - | 2 | 성공 |
| fa-03 | 58/58 pass | - | n/a | +52/-44 | - | 2 | 성공 |
| fa-04 | 58/58 pass | - | n/a | +37/-25 | - | 1 | 성공 |
| fa-05 | 58/58 pass | 10 pass, 1 xfail | n/a | +195/-2 | - | 1 | 부분 — error_max_turns로 종료(최종 보고 없음). 작성된 테스트 10 pass + 1 xfail, 기존 58 pass. |
| fa-06 | 58/58 pass | 10 pass | n/a | +129/-0 | - | 1 | 성공 |
| fa-07 | 58/58 pass | 2 pass | n/a | +28/-3 | - | 2 | 성공 |
| fa-08 | 58/58 pass | 1 pass | n/a | +17/-1 | - | 2 | 성공 |
| fa-09 | 58/58 pass | - | n/a | +32/-0 | - | 1 | 성공 |
| fa-10 | 58/58 pass | - | n/a | +3/-3 | - | 1 | 성공 |
| nx-01 | 러너 없음 | - | pass / pass | +35/-13 | - | 1 | 성공 |
| nx-02 | 러너 없음 | - | pass / pass | +6/-4 | - | 3 | 성공 |
| nx-03 | 러너 없음 | - | pass / pass | +135/-111 | - | 10 | 성공 |
| nx-04 | 러너 없음 | - | pass / pass | +28/-12 | - | 3 | 성공 |
| nx-05 | 러너 없음 | 5 pass (`jest`, rc=0) | pass / pass | +80/-3 | +6374/-822 | 6 | 성공 |
| nx-06 | 러너 없음 | 3 pass (`vitest run`, rc=0) | pass / pass | +78/-2 | +1205/-45 | 4 | 성공 |
| nx-07 | 러너 없음 | - | pass / pass | +16/-1 | - | 2 (+AGENTS.md(`next dev` 실행이 생성)) | 성공 |
| nx-08 | 러너 없음 | - | pass / pass | +37/-0 | - | 1 | 성공 |
| nx-09 | 러너 없음 | - | pass / pass | +3/-3 | - | 1 | 성공 |
| nx-10 | 러너 없음 | - | pass / pass | +5/-5 | - | 2 | 성공 |

- '성공' 기준: 세션 `subtype: success` + 위 검사 전부 통과 + diff가 태스크 대상 파일을 변경. UI 동작(nx-01 검색창 등)은 브라우저로 확인하지 않음 — build 통과까지만.
- nx-05: `@types/react`·`@types/react-dom` 17→18 업그레이드 포함 (jest/RTL 설치 중 peer 충돌). nx-06: `npm install -D vitest --legacy-peer-deps`.
- fa-05: 세션이 `.env`(5432)를 보고 주입된 `DATABASE_URL`을 쓰지 않고, `initdb`로 자체 Postgres(/tmp, :54329)를 띄워 테스트 실행. 세션 종료 후에도 남아 있어 하네스가 정지·삭제함. nx-07: `next dev -p 3917` 실행 (종료 후 프로세스 없음, `AGENTS.md` 생성됨).
- 자체 브랜치 생성 4세션: fa-01 `feature/login-rate-limit`, nx-02 `feature/user-email`, nx-03 `feature/users-app-router`, nx-05 `test/list-components`. 커밋한 세션 0. diff는 베이스라인 커밋 대비.

## 세션별 한 줄 요약

| id | 종류/언어 | 태스크 | init MCP | 발화 | 체인 | 로드 스킬 | 턴 | 결과 |
|---|---|---|---|---|---|---|---|---|
| fa-01 | feature/ko | 로그인 엔드포인트에 rate limit 붙여줘 | pending | Y | search+resolve+load | `uasl/api-design` | 30 | 성공, +126/-4 |
| fa-02 | feature/en | Add a case-insensitive title search query parameter to GET /api/v1/items/. | pending | Y | search+resolve+load | `fastapi(local)`, `sqlmodel(local)` | 26 | 성공, +120/-26 |
| fa-03 | refactor/en | Refactor the items routes so the database queries live in crud.py instead of the route handlers. | pending | N | none | - | 19 | 성공, +52/-44 |
| fa-04 | refactor/ko | users.py 라우트들에 반복되는 이메일 중복 체크 로직을 헬퍼 하나로 정리해줘 | pending | N | none | - | 14 | 성공, +37/-25 |
| fa-05 | test/en | Add tests for the password reset flow. | pending | Y | search+resolve+load | `uasl/radar` | 26 | 부분, +195/-2 |
| fa-06 | test/ko | 아이템 목록 API의 skip/limit 페이지네이션 동작 테스트 작성해줘 | pending | Y | search+resolve+load | `uasl/python-testing-patterns` | 30 | 성공, +129/-0 |
| fa-07 | bugfix/en | GET /api/v1/items/?limit=-1 returns a 500 instead of a validation error, fix it. | pending | N | none | - | 11 | 성공, +28/-3 |
| fa-08 | bugfix/ko | 슈퍼유저로 /api/v1/password-recovery-html-content/{email} 호출하면 500 에러 나는데 고쳐줘 | connected | N | none | - | 13 | 성공, +17/-1 |
| fa-09 | docs/ko | backend/README.md에 Docker 없이 로컬 Postgres로 백엔드 테스트 돌리는 방법 섹션 추가해줘 | connected | N | none | - | 9 | 성공, +32/-0 |
| fa-10 | trivial/en (음성 대조군) | Rename get_datetime_utc in backend/app/models.py to utc_now. | pending | N | none | - | 6 | 성공, +3/-3 |
| nx-01 | feature/en | Add a search box to the users list page that filters users by name. | connected | N | none | - | 9 | 성공, +35/-13 |
| nx-02 | feature/ko | 유저에 email 필드 추가해서 상세 페이지에 보여줘 | pending | N | none | - | 11 | 성공, +6/-4 |
| nx-03 | refactor/ko | users 페이지들을 pages 라우터에서 App Router로 옮겨줘 | connected | Y | search+resolve+load | `uasl/next-best-practices` | 23 | 성공, +135/-111 |
| nx-04 | refactor/en | Refactor the Layout component into separate Header and Footer components. | connected | N | none | - | 10 | 성공, +28/-12 |
| nx-05 | test/en | Add unit tests for the List and ListItem components. | pending | Y | search+resolve+load | `uasl/unit-testing` | 24 | 성공, +80/-3 |
| nx-06 | test/ko | /api/users API 핸들러 테스트 작성해줘 | pending | Y | search+resolve+load | `uasl/radar`, `uasl/tdd-workflow` | 27 | 성공, +78/-2 |
| nx-07 | bugfix/en | The /api/users endpoint returns 200 for POST and DELETE too; it should only allow GET and return 405 otherwise. | pending | N | none | - | 6 | 성공, +16/-1 |
| nx-08 | docs/en | Update the README to describe the project structure and the available npm scripts. | pending | N | none | - | 5 | 성공, +37/-0 |
| nx-09 | trivial/ko (음성 대조군) | README 오타 고쳐줘 | connected | N | none | - | 6 | 성공, +3/-3 |
| nx-10 | trivial/ko (음성 대조군) | ListDetail 컴포넌트 이름을 UserDetail로 바꿔줘 | connected | N | none | - | 7 | 성공, +5/-5 |

## 라우터 미발화 세션의 첫 3턴 (인용)

턴 = 메인 스레드 assistant 메시지 1개(같은 메시지 안의 병렬 도구 호출은 한 턴). 경로의 worktree 접두사는 생략. 텍스트는 200자, 인자는 120자에서 자름.

- **fa-03** “Refactor the items routes so the database queries live in crud.py instead of the route handlers.”
  - T1: `Grep`(pattern=`crud`); `Glob`(pattern=`**/crud.py`)
  - T2: `Read`(file_path=`backend/app/crud.py`); `Read`(file_path=`backend/app/api/routes/items.py`); `Read`(file_path=`backend/tests/utils/item.py`)
  - T3: `Skill`(skill=`sqlmodel`)
- **fa-04** “users.py 라우트들에 반복되는 이메일 중복 체크 로직을 헬퍼 하나로 정리해줘”
  - T1: `Glob`(pattern=`**/users.py`)
  - T2: `Read`(file_path=`backend/app/api/routes/users.py`)
  - T3: `Grep`(pattern=`already exists`)
- **fa-07** “GET /api/v1/items/?limit=-1 returns a 500 instead of a validation error, fix it.”
  - T1: `Grep`(pattern=`limit`)
  - T2: `Read`(file_path=`backend/app/api/routes/items.py`); `Grep`(pattern=`skip: int\|limit: int\|Query\(`)
  - T3: `Grep`(pattern=`def test_read_items`)
- **fa-08** “슈퍼유저로 /api/v1/password-recovery-html-content/{email} 호출하면 500 에러 나는데 고쳐줘”
  - T1: `Grep`(pattern=`password-recovery-html-content`)
  - T2: `Read`(file_path=`backend/app/api/routes/login.py`)
  - T3: `Read`(file_path=`backend/app/utils.py`)
- **fa-09** “backend/README.md에 Docker 없이 로컬 Postgres로 백엔드 테스트 돌리는 방법 섹션 추가해줘”
  - T1: `Bash`(command=`git status --short && git branch --show-current; ls; ls backend 2>/dev/null`)
  - T2: `Read`(file_path=`backend/README.md`); `Bash`(command=`cat backend/scripts/*.sh; echo ---; cat .env 2>/dev/null \| grep -iE 'postgres\|first_super\|environment\|secret' ; echo ---`)
  - T3: `Bash`(command=`cat backend/tests/conftest.py; echo ---; grep -n -A15 '^  db:' compose.yml; echo ---; grep -vE '^\s*#\|^\s*$' .env; echo `)
- **fa-10** “Rename get_datetime_utc in backend/app/models.py to utc_now.” — 트리비얼(음성 대조군)
  - T1: `Grep`(pattern=`get_datetime_utc`)
  - T2: `Read`(file_path=`backend/app/models.py`)
  - T3: `Edit`(file_path=`backend/app/models.py`)
- **nx-01** “Add a search box to the users list page that filters users by name.”
  - T1: `Glob`(pattern=`{app,pages,components,interfaces,utils}/**/*`); `Bash`(command=`git status && git branch --show-current; cat package.json`)
  - T2: `Read`(file_path=`pages/users/index.tsx`); `Read`(file_path=`components/List.tsx`); `Read`(file_path=`utils/sample-data.ts`)
  - T3: text: “This is a small client-side change to one file, so I'll make it directly.”; `Write`(file_path=`pages/users/index.tsx`)
- **nx-02** “유저에 email 필드 추가해서 상세 페이지에 보여줘”
  - T1: `Bash`(command=`git status && git branch --show-current; git ls-files \| grep -v node_modules \| head -50`)
  - T2: `Read`(file_path=`interfaces/index.ts`); `Read`(file_path=`utils/sample-data.ts`); `Read`(file_path=`components/ListDetail.tsx`); `Read`(file_path=`pages/users/[id].tsx`)
  - T3: text: “Three small edits: type, sample data, detail component. Working in a detached HEAD, so I'll make a branch first.”; `Bash`(command=`git switch -c feature/user-email`); `Edit`(file_path=`interfaces/index.ts`); `Edit`(file_path=`utils/sample-data.ts`); `Edit`(file_path=`components/ListDetail.tsx`)
- **nx-04** “Refactor the Layout component into separate Header and Footer components.”
  - T1: `Glob`(pattern=`**/*.{tsx,ts}`)
  - T2: `Read`(file_path=`components/Layout.tsx`); `Read`(file_path=`components/ListItem.tsx`)
  - T3: text: “This is a small refactor, so I'll make the change directly.”; `Write`(file_path=`components/Header.tsx`); `Write`(file_path=`components/Footer.tsx`); `Edit`(file_path=`components/Layout.tsx`); `Edit`(file_path=`components/Layout.tsx`)
- **nx-07** “The /api/users endpoint returns 200 for POST and DELETE too; it should only allow GET and return 405 otherwise.”
  - T1: `Glob`(pattern=`{pages,app,src}/**/api/users*`); `Glob`(pattern=`{pages,app,src}/**/api/users/**`)
  - T2: `Read`(file_path=`pages/api/users/index.ts`)
  - T3: `Edit`(file_path=`pages/api/users/index.ts`)
- **nx-08** “Update the README to describe the project structure and the available npm scripts.”
  - T1: `Bash`(command=`cat README.md && echo ---- && cat package.json && echo ---- && git ls-files \| grep -v '^\.claude/' \| head -100`)
  - T2: `Bash`(command=`for f in pages/*.tsx pages/users/*.tsx pages/api/users/index.ts interfaces/index.ts utils/sample-data.ts components/*.ts`)
  - T3: `Edit`(file_path=`README.md`)
- **nx-09** “README 오타 고쳐줘” — 트리비얼(음성 대조군)
  - T1: `Glob`(pattern=`README*`)
  - T2: `Read`(file_path=`README.md`)
  - T3: text: “README에는 철자 오타가 없어서, 문법 오류 1건과 잘못된 명령어 2건을 고쳤습니다.”; `Edit`(file_path=`README.md`); `Edit`(file_path=`README.md`); `Edit`(file_path=`README.md`)
- **nx-10** “ListDetail 컴포넌트 이름을 UserDetail로 바꿔줘” — 트리비얼(음성 대조군)
  - T1: `Grep`(pattern=`ListDetail`); `Glob`(pattern=`**/ListDetail*`)
  - T2: `Read`(file_path=`components/ListDetail.tsx`); `Read`(file_path=`pages/users/[id].tsx`)
  - T3: `Bash`(command=`git mv components/ListDetail.tsx components/UserDetail.tsx && sed -i '' 's/ListDetail/UserDetail/g' components/UserDetai`)

## 파일

- `tasks.yaml` — 20 태스크 + 레포 커밋 해시
- `runs/<id>.jsonl` — 세션 전체 stream-json / `runs/<id>.stderr` / `runs/<id>.diff` / `runs/<id>.meta.json` (명령, 종료코드, 벽시계, diff numstat, 사후 테스트 출력) / `runs/<id>.junit.xml` (fastapi)
- `runs/loaded/<id>.md` — load_skills가 반환한 스킬 본문
- `runs/_extract.json` — 추출 결과 전체, `runs/baseline_fastapi_tests.txt` — 기존 테스트 id 58개
- `scripts/run_task.py`, `scripts/extract.py`, `scripts/report.py`; `smoke/` — 본 실행 전 환경 확인용 세션 2개 (태스크 아님)
