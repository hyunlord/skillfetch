# skillfetch 0.5단계 — 라우터 발화 수정 후 재측정 (report)

실행 2026-10-22 KST 15:59–16:08. 0단계 미발화 10개 태스크 × (R1, R1R2) 각 1회 = 20세션. 숫자는 `scripts/extract05.py`, 표는 `scripts/report05.py`. 적합성 열만 수기.

## 0. 조건

| 항목 | 값 |
|---|---|
| 변경 위치 | skillfetch 레포 브랜치 `fix/router-trigger` (worktree `<workspace>/router-fix`, `origin/main`=`9afa309` 기준). 커밋 `c229053` (router skill + CLAUDE.md 라우터 절 5번), `65a1c2b` (hook + README). push 안 함 |
| R1 | 테스트 레포 브랜치 `e2e-r1` = 0단계 베이스라인 + 새 `SKILL.md` (59줄) |
| R1R2 | `e2e-r1r2` = R1 + `.claude/hooks/skillfetch-user-prompt-submit.sh` + `.claude/settings.json`(UserPromptSubmit) — README 안내 그대로 |
| 하네스 | 0단계와 동일 (`scripts/run_task.py`, 같은 명령·allowedTools·max-turns 25, 동시 4, worktree `~/skillfetch-e2e-wt/<id>-<cond>`, 태스크별 DB, 인덱스는 `~/.skillfetch/index` `manifest.built_at` 2026-10-22T06:15:43Z — 0단계 도중 15:36:26 KST에 외부에서 교체된 것으로, 0단계의 fa-01·02·03·04·10은 04:45:24Z 빌드, 나머지 0단계 15세션과 0.5단계 20세션은 06:15:43Z 빌드). 추가된 계측: `--debug-file <id>.debug.log`, stdout 줄별 수신 시각 `<id>.ts` (두 조건 동일) |
| skillfetch 서버 | `uvx --from git+…` HEAD `9afa309` (실행 전후 동일) |
| 훅 주입 확인 | debug log의 `Hook UserPromptSubmit … If this task is non-trivial and you have not yet called skillfetch's search_skills, do that first.` 줄: R1R2 10/10, R1 0/10. (사용자 전역 UserPromptSubmit 훅은 두 조건 모두 그대로 실행) |
| 도구 승인 | 20세션 모두 `permission_denials: []` |

라우터 SKILL.md 변경 요지 (0단계 미발화 10세션 첫 3턴 인용에 맞춘 것):

- nx-01·nx-04 “This is a small … so I'll make it directly”, nx-02 “Three small edits” → `"It looks small" is not a reason to skip`, `a feature, even one that fits in a single file`
- fa-04·fa-07·fa-08·nx-07: T1이 Grep/Glob, 이후 복귀 안 함 → description `— before reading the codebase`, When `Run the steps first, before you grep, glob or read the codebase`, Step 1 `Do not explore the code first`
- fa-03: T3 `Skill(sqlmodel)` (레포 내장 스킬로 대체) → `Neither is a project skill that seems to fit … run the steps and pin it`, Step 5 project skill을 `path:`로 pin
- fa-07·fa-08·nx-07 (bugfix), fa-09·nx-08 (docs) → When에 bug fix / documentation / configuration 명시
- 트리비얼 = 한 파일의 한 줄 수정, 이름 바꾸기(다른 변경 없음), 질문 답변
- Step 2 추가: skillfetch 도구가 아직 없으면 ToolSearch `+skillfetch`로 로드 (0단계 init 13/20이 `pending`)

## 1. 조건별 발화율 (`search_skills` 호출 세션)

| 태스크 | 종류/언어 | 0단계 | R1 | R1R2 |
|---|---|---|---|---|
| fa-03 | refactor/en | N | Y | Y |
| fa-04 | refactor/ko | N | Y | Y |
| fa-07 | bugfix/en | N | Y | N |
| fa-08 | bugfix/ko | N | Y | N |
| fa-09 | docs/ko | N | Y | N |
| nx-01 | feature/en | N | Y | Y |
| nx-02 | feature/ko | N | Y | Y |
| nx-04 | refactor/en | N | Y | Y |
| nx-07 | bugfix/en | N | N | N |
| nx-08 | docs/en | N | Y | Y |

| 종류 | n | 0단계 | R1 | R1R2 |
|---|---|---|---|---|
| feature | 2 | 0/2 | 2/2 | 2/2 |
| refactor | 3 | 0/3 | 3/3 | 3/3 |
| bugfix | 3 | 0/3 | 2/3 | 0/3 |
| docs | 2 | 0/2 | 2/2 | 1/2 |
| **합계** | 10 | 0/10 | **9/10** | **6/10** |

- R1 언어별: en 5/6, ko 4/4; `Skill(skillfetch-router)` 호출 9/10 (발화 세션과 일치)
- R1R2 언어별: en 4/6, ko 2/4; `Skill(skillfetch-router)` 호출 6/10 (발화 세션과 일치)
- 라우터 외 Skill 호출: R1R2 fa-03→`sqlmodel`

미발화 세션 첫 3턴 (인용):

- **R1 nx-07** “The /api/users endpoint returns 200 for POST and DELETE too; it should only allow GET and return 405 otherwise.”
  - T1: `Glob`(pattern=`{pages,app,src}/**/api/users*/**`); `Glob`(pattern=`{pages,app,src}/**/api/users*`)
  - T2: `Read`(file_path=`pages/api/users/index.ts`)
  - T3: `Edit`(file_path=`pages/api/users/index.ts`)
- **R1R2 fa-07** “GET /api/v1/items/?limit=-1 returns a 500 instead of a validation error, fix it.”
  - T1: `Grep`(pattern=`limit`)
  - T2: `Read`(file_path=`backend/app/api/routes/items.py`); `Grep`(pattern=`skip: int\|limit: int\|Query\(`)
  - T3: text: “Postgres rejects a negative `LIMIT`/`OFFSET`, so the raw `int` parameters go straight to the DB and come back as a 500. I'll add bounds with `Query` so FastAPI returns a 422 first.”; `Grep`(pattern=`limit=\|skip=`); `Grep`(pattern=`^def test_read_items`)
- **R1R2 fa-08** “슈퍼유저로 /api/v1/password-recovery-html-content/{email} 호출하면 500 에러 나는데 고쳐줘”
  - T1: `Grep`(pattern=`password-recovery-html-content`)
  - T2: `Read`(file_path=`backend/app/api/routes/login.py`); `Grep`(pattern=`def generate_reset_password_email\|def generate_password_reset_token\|def render_email_template`)
  - T3: `Bash`(command=`cd backend && ls app/email-templates app/email-templates/* ; grep -r`)
- **R1R2 fa-09** “backend/README.md에 Docker 없이 로컬 Postgres로 백엔드 테스트 돌리는 방법 섹션 추가해줘”
  - T1: `Bash`(command=`git status --short && git branch --show-current; ls backend backend/scripts; cat backend/README.md`)
  - T2: `Bash`(command=`for f in backend/scripts/test.sh backend/scripts/tests-start.sh backend/scripts/prestart.sh backend/tests/conf`)
  - T3: `Bash`(command=`cat backend/app/core/db.py; grep -rn "send_email\\|patch\\|smtp" backend/tests \| head -20; cat .github/workflows`)
- **R1R2 nx-07** “The /api/users endpoint returns 200 for POST and DELETE too; it should only allow GET and return 405 otherwise.”
  - T1: `Glob`(pattern=`pages/api/**/*`)
  - T2: `Read`(file_path=`pages/api/users/index.ts`)
  - T3: `Edit`(file_path=`pages/api/users/index.ts`)
- 위 미발화 세션의 text/thinking에 skill·router·skillfetch·hook·trivial 언급: 없음 (R1R2 fa-07의 “items router”는 FastAPI 라우터 언급).

## 2. 체인 완주

| 조건 | 발화 | search→resolve→load 완주 | search만 | resolve 에러 | load 에러 |
|---|---|---|---|---|---|
| R1 | 9 | 8 | 1 | 0 | 0 |
| R1R2 | 6 | 6 | 0 | 0 | 0 |

- R1 fa-08: search 후 resolve/load 없이 작업 진행. 최종 응답 인용: “The skill search found nothing that fit this bug, so I didn't load any skills.”
- resolve_set `excluded`/`warnings`: 전 세션 빈 배열. 세션당 search 1회.

| 조건 | 태스크 | query |
|---|---|---|
| R1 | fa-03 (en) | Refactor FastAPI items route handlers so SQLModel database queries move into crud.py functions |
| R1 | fa-04 (ko) | Refactor the FastAPI users.py route module to extract the repeated email-uniqueness check into a single helper function |
| R1 | fa-07 (en) | Fix the FastAPI GET /api/v1/items/ endpoint so a negative limit query parameter returns a 422 validation error instead of a 500 |
| R1 | fa-08 (ko) | Fix a 500 Internal Server Error in the FastAPI backend endpoint GET /api/v1/password-recovery-html-content/{email} when called by a superuser |
| R1 | fa-09 (ko) | Add a section to the FastAPI full-stack template's backend/README.md explaining how to run the backend pytest suite against a locally installed PostgreSQL without Docker |
| R1 | nx-01 (en) | Add a client-side search input to the Next.js TypeScript users list page that filters the displayed users by name |
| R1 | nx-02 (ko) | Add an email field to the User type in a Next.js TypeScript app and display it on the user detail page |
| R1 | nx-04 (en) | Refactor the React Layout component in a Next.js TypeScript app into separate Header and Footer components |
| R1 | nx-08 (en) | Update the README of a Next.js TypeScript example app to document the project structure and the npm scripts from package.json |
| R1R2 | fa-03 (en) | Refactor FastAPI items route handlers so their SQLModel database queries move into crud.py functions |
| R1R2 | fa-04 (ko) | Refactor the FastAPI user routes in backend/app/api/routes/users.py to extract the repeated email-uniqueness check into a single helper function |
| R1R2 | nx-01 (en) | Add a client-side search input to the Next.js Pages Router users list page (pages/users/index.tsx) in TypeScript React that filters users by name |
| R1R2 | nx-02 (ko) | Add an email field to the User type and sample data in a Next.js TypeScript app and display it on the user detail page |
| R1R2 | nx-04 (en) | Refactor the Next.js React TypeScript Layout component in components/Layout.tsx into separate Header and Footer components |
| R1R2 | nx-08 (en) | Update the README.md of a Next.js TypeScript project to document the project directory structure and the available npm scripts from package.json |

## 3. 선택 적합성

| 조건 | 태스크 | 로드된 스킬 | search 순위 | token_estimate | 판정 | 근거 |
|---|---|---|---|---|---|---|
| R1 | fa-03 | `uasl/python-design-patterns` | 7/10 | 3016 | **적합** | 'Pattern 3: Separation of Concerns' — API Layer(handlers) / Service / Repository Layer(data access) 분리 도식이 '쿼리를 crud.py로' 태스크에 해당. |
| R1 | fa-04 | `uasl/refactoring-patterns` | 10/10 | 5116 | **적합** | 'Copy-pasted logic → Extract Method', '테스트 통과 확인 → 작은 변경 → 재확인' 루프가 중복 이메일 체크 헬퍼 추출에 해당. |
| R1 | fa-07 | `fastapi(local)` | 검색 결과 밖 (pinned) | 2451 | **적합** | `Annotated[int, Path(ge=1, ...)]` 형태의 파라미터 제약 선언이 음수 limit을 422로 막는 수정에 해당. 레포 .venv의 로컬 스킬을 pinned. |
| R1 | fa-09 | `uasl/quill` | 10/10 | 3133 | **모호** | readme_management 항목은 해당하나 본문이 JSDoc/TSDoc·Nexus 라우팅 중심이고 README 템플릿(`references/readme-templates.md`)은 로드되지 않음. |
| R1 | nx-01 | `uasl/frontend-patterns` | 3/10 | 3808 | **적합** | React state·controlled input·forms 패턴이 검색 입력으로 목록 필터링하는 태스크에 해당. |
| R1 | nx-01 | `uasl/vercel-react-best-practices` | 1/10 | 1561 | **모호** | 64개 성능 규칙 색인(waterfall, bundle, rerender 등). 4명짜리 정적 목록 필터에 직접 해당하는 규칙은 rerender 계열 정도. |
| R1 | nx-02 | `uasl/next-best-practices` | 8/10 | 942 | **부적합** | 타입·샘플 데이터·상세 컴포넌트에 필드 추가 태스크. 본문의 App Router/RSC/async 링크 목록 중 해당 항목 없음. |
| R1 | nx-04 | `uasl/web-component-design` | 3/10 | 1796 | **적합** | 컴포넌트 composition 패턴, 'Refactoring legacy components into modern patterns'가 Layout → Header/Footer 분리에 해당. |
| R1 | nx-04 | `uasl/next-best-practices` | 8/10 | 942 | **부적합** | nx-02와 같은 이유. Pages Router 컴포넌트 분리에 해당하는 항목 없음. |
| R1 | nx-08 | `uasl/quill` | 8/10 | 3133 | **모호** | fa-09와 동일 스킬. README 갱신 항목은 해당, 템플릿 참조는 미로드. |
| R1R2 | fa-03 | `uasl/python-design-patterns` | 7/10 | 3016 | **적합** | 'Pattern 3: Separation of Concerns' — API Layer(handlers) / Service / Repository Layer(data access) 분리 도식이 '쿼리를 crud.py로' 태스크에 해당. |
| R1R2 | fa-04 | `uasl/zen` | 3/10 | 3130 | **모호** | capabilities에 function_extraction이 있으나 본문 상당 부분이 Judge/Atlas/Radar 등과의 핸드오프 프로토콜이고 `references/refactoring-recipes.md`는 로드되지 않음. |
| R1R2 | nx-01 | `uasl/next-best-practices` | 8/10 | 942 | **부적합** | 본문이 App Router/RSC/async API 하위 문서 링크 목록. 이 레포는 Pages Router이고 태스크는 클라이언트 입력 필터라 해당 항목 없음. |
| R1R2 | nx-01 | `uasl/vercel-react-best-practices` | 1/10 | 1561 | **모호** | 64개 성능 규칙 색인(waterfall, bundle, rerender 등). 4명짜리 정적 목록 필터에 직접 해당하는 규칙은 rerender 계열 정도. |
| R1R2 | nx-01 | `uasl/accessibility-compliance` | 9/10 | 2879 | **적합** | 'Creating accessible forms with proper labeling' — 검색 입력의 label/ARIA에 해당. |
| R1R2 | nx-02 | `uasl/next-best-practices` | 8/10 | 942 | **부적합** | 타입·샘플 데이터·상세 컴포넌트에 필드 추가 태스크. 본문의 App Router/RSC/async 링크 목록 중 해당 항목 없음. |
| R1R2 | nx-04 | `uasl/web-component-design` | 3/10 | 1796 | **적합** | 컴포넌트 composition 패턴, 'Refactoring legacy components into modern patterns'가 Layout → Header/Footer 분리에 해당. |
| R1R2 | nx-04 | `uasl/next-best-practices` | 8/10 | 942 | **부적합** | nx-02와 같은 이유. Pages Router 컴포넌트 분리에 해당하는 항목 없음. |
| R1R2 | nx-08 | `uasl/quill` | 9/10 | 3133 | **모호** | fa-09와 동일 스킬. README 갱신 항목은 해당, 템플릿 참조는 미로드. |

- R1: 스킬-태스크 쌍 10개 — 적합 5 / 부적합 2 / 모호 3
- R1R2: 스킬-태스크 쌍 9개 — 적합 3 / 부적합 3 / 모호 3
- 참고 0단계(다른 태스크 7개): 9쌍 — 적합 4 / 부적합 0 / 모호 5

## 4. MCP ready 시각 (세션 프로세스 spawn 기준, 초)

start = debug log `MCP server "skillfetch": Starting connection`, ready = `Successfully connected`, init = stream의 init 이벤트 수신, 첫 도구 = 메인 스레드 첫 tool_use 수신, ToolSearch·skillfetch = 각 첫 호출 수신. `connect` = Claude Code가 보고한 연결 소요(ms).

| 조건 | 태스크 | init 상태 | MCP start | MCP ready | connect ms | init | 첫 도구 | ready − 첫 도구 | 첫 ToolSearch | 첫 skillfetch 호출 | 발화 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | fa-03 | pending | 2.9 | 4.7 | 1786 | 4.4 | 6.9 | -2.3 | 9.0 | 10.5 | Y |
| R1 | fa-04 | pending | 3.0 | 4.6 | 1543 | 4.4 | 6.3 | -1.8 | 8.8 | 10.5 | Y |
| R1 | fa-07 | pending | 1.7 | 3.6 | 1854 | 3.5 | 5.4 | -1.9 | 7.7 | 9.7 | Y |
| R1 | fa-08 | pending | 5.1 | 9.0 | 3850 | 5.6 | 21.1 | -12.2 | 26.1 | 30.3 | Y |
| R1 | fa-09 | pending | 4.0 | 9.7 | 5690 | 6.0 | 8.5 | +1.2 | 11.4 | 13.0 | Y |
| R1 | nx-01 | connected | 1.4 | 3.3 | 1815 | 3.6 | 6.3 | -3.1 | 9.1 | 11.3 | Y |
| R1 | nx-02 | pending | 1.6 | 7.4 | 5747 | 4.5 | 7.0 | +0.4 | 9.7 | 11.6 | Y |
| R1 | nx-04 | pending | 1.9 | 4.5 | 2598 | 4.0 | 7.3 | -2.8 | 9.6 | 11.7 | Y |
| R1 | nx-07 | connected | 1.7 | 3.5 | 1783 | 3.5 | 6.9 | -3.5 | - | - | N |
| R1 | nx-08 | connected | 1.5 | 3.2 | 1687 | 3.5 | 6.5 | -3.3 | 11.2 | 13.4 | Y |
| R1R2 | fa-03 | pending | 3.0 | 4.7 | 1680 | 4.6 | 10.9 | -6.2 | 14.5 | 17.6 | Y |
| R1R2 | fa-04 | pending | 2.9 | 4.7 | 1765 | 4.5 | 15.4 | -10.7 | 19.4 | 22.6 | Y |
| R1R2 | fa-07 | pending | 5.4 | 9.3 | 3897 | 6.5 | 9.3 | -0.1 | - | - | N |
| R1R2 | fa-08 | pending | 4.5 | 8.8 | 4308 | 5.0 | 7.6 | +1.2 | - | - | N |
| R1R2 | fa-09 | pending | 3.4 | 5.5 | 2107 | 4.0 | 7.9 | -2.4 | - | - | N |
| R1R2 | nx-01 | pending | 3.6 | 5.5 | 1901 | 4.2 | 7.8 | -2.3 | 11.8 | 13.6 | Y |
| R1R2 | nx-02 | connected | 1.3 | 3.2 | 1886 | 3.3 | 6.1 | -2.9 | 8.2 | 9.9 | Y |
| R1R2 | nx-04 | pending | 1.9 | 4.6 | 2743 | 4.0 | 6.8 | -2.2 | 13.2 | 15.2 | Y |
| R1R2 | nx-07 | pending | 1.8 | 4.0 | 2240 | 3.6 | 6.1 | -2.1 | - | - | N |
| R1R2 | nx-08 | pending | 1.4 | 4.6 | 3192 | 3.8 | 10.6 | -6.0 | 14.7 | 18.6 | Y |

- MCP ready: 중앙값 4.7s, 범위 3.2–9.7s (20세션). 연결 실패 0.
- init 이벤트 시점에 `connected`: 4/20, `pending`: 16/20
- 첫 도구 호출이 MCP ready보다 먼저인 세션: 3/20 (R1 fa-09, R1 nx-02, R1R2 fa-08)
- 발화 세션의 첫 skillfetch 호출은 전부 ToolSearch 이후 (ToolSearch는 `select:mcp__skillfetch__…` 또는 `+skillfetch`).

## 5. (참고) 비용·결과

| 태스크 | 0단계 턴/입력/출력/s | R1 턴/입력/출력/s | R1R2 턴/입력/출력/s | R1 load 토큰 | R1R2 load 토큰 | 사후 검사 R1 / R1R2 |
|---|---|---|---|---|---|---|
| fa-03 | 19 / 1.16M / 5,338 / 114 | 20 / 1.47M / 5,477 / 73 | 21 / 1.49M / 5,299 / 112 | 3016 | 3016 | 기존 58/58 / 기존 58/58 |
| fa-04 | 14 / 0.76M / 4,927 / 105 | 24 / 1.70M / 6,205 / 82 | 25 / 1.57M / 6,807 / 137 | 5116 | 3130 | 기존 58/58 / 기존 58/58 |
| fa-07 | 11 / 0.66M / 2,946 / 44 | 22 / 1.74M / 5,124 / 96 | 11 / 0.66M / 4,132 / 54 | 2451 | - | 기존 58/58, 새 2 / 기존 58/58, 새 1 |
| fa-08 | 13 / 1.03M / 5,034 / 70 | 22 / 1.80M / 5,210 / 134 | 18 / 1.34M / 8,073 / 129 | - | - | 기존 58/58, 새 1 / 기존 58/58, 새 3 |
| fa-09 | 9 / 0.68M / 3,099 / 37 | 24 / 1.72M / 7,256 / 107 | 9 / 0.77M / 4,593 / 55 | 3133 | - | 기존 58/58 / 기존 58/58 |
| nx-01 | 9 / 0.49M / 1,892 / 30 | 17 / 1.10M / 3,424 / 78 | 15 / 0.91M / 2,854 / 66 | 5369 | 5382 | tsc ok, build ok / tsc ok, build ok |
| nx-02 | 11 / 0.40M / 1,942 / 33 | 19 / 1.15M / 3,028 / 52 | 18 / 1.05M / 3,014 / 48 | 942 | 942 | tsc ok, build ok / tsc ok, build ok |
| nx-04 | 10 / 0.50M / 1,834 / 35 | 14 / 0.97M / 2,592 / 45 | 17 / 1.08M / 2,998 / 53 | 2738 | 2738 | tsc ok, build ok / tsc ok, build ok |
| nx-07 | 6 / 0.40M / 1,262 / 28 | 8 / 0.57M / 1,751 / 30 | 7 / 0.57M / 1,535 / 30 | - | - | tsc ok, build ok / tsc ok, build ok |
| nx-08 | 5 / 0.41M / 2,139 / 27 | 12 / 0.98M / 3,281 / 49 | 12 / 0.98M / 3,453 / 69 | 3133 | 3133 | tsc ok, build ok / tsc ok, build ok |

- 입력 = uncached + cache write + cache read. 20세션 모두 `subtype: success`.

## 파일

- `runs-0.5/{R1,R1R2}/<id>.{jsonl,ts,debug.log,stderr,diff,meta.json,junit.xml}`, `runs-0.5/loaded/<cond>-<id>.md`, `runs-0.5/_extract.json`
- skillfetch 변경: `router-fix/assets/router-skill/SKILL.md`, `router-fix/assets/hooks/user-prompt-submit.sh`, `router-fix/README.md`, `router-fix/CLAUDE.md`
