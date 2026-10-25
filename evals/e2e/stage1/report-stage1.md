# skillfetch 1단계 — 3조건 비교 (report)

> 블라인드 판정 결과는 `blind-ranking-results.md` (판정자 1명, 두 번째 판정자 없음 — 세트 구별 불가, nx-10 문서 판정 비블라인드 노출 기록 포함). 판정 원본 `blind-ranking.md`.

실행 2026-10-22 KST 17:16:45–18:04:25, 110세션 (전문가 스킬 있는 15태스크 × A/B/C × 2회 = 90, 없는 5태스크 × A/C × 2회 = 20). 순서는 고정 시드(20261022)로 섞은 큐 `runs/_queue.txt`, 동시 4. 숫자는 `scripts/extract_s1.py`, 표는 `scripts/report_s1.py`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 모델/CLI | Claude Code 2.1.280, 기본 모델(`claude-opus-5-5[1m]`), 구독 플랜. `claude -p "<prompt>" --output-format stream-json --verbose --max-turns 25 --allowedTools "Read,Edit,Write,Bash,Glob,Grep,mcp__skillfetch__*" --debug-file …` (전 조건 동일; B만 `--append-system-prompt-file` 추가) |
| 트리 | A·B: 업스트림 (`repos/fastapi` `b1125d88`, `repos/nextjs` `76de3ce2`), 브랜치 `s1-a`. C: `s1-c` = 업스트림 + skillfetch `main@96f0f3b`의 `assets/router-skill/SKILL.md`(59줄, PR #19 머지본) + `claude mcp add -s project` 로 만든 `.mcp.json` (fastapi `00d0b3be`, nextjs `e59cccf6`) |
| skillfetch | 서버 `uvx --from git+https://github.com/hyunlord/skillfetch` HEAD `96f0f3b` (시작·종료 동일). 인덱스 `~/.skillfetch/index` `built_at` 2026-10-22T06:15:43Z — 110세션 전부 동일 (meta `index_built_at`, 파일 mtime 15:36:26 이후 변화 없음) |
| B 입력 | `stage1/expert-content/<id>.md` = 전문가 id를 `resolve_set(auto_ids=[], pinned_ids=…)` → `load_skills` 한 `content` 그대로 (15세트, errors/excluded/warnings 0) |
| 레포 내장 스킬 | fastapi 레포의 `.claude/skills/{library-skills, fastapi, sqlmodel}` 전 조건 유지 |
| 체크 | `stage1/checks/` (세션 전 작성·검증·동결, `FROZEN.sha256` 53파일 실행 전후 일치). 각 세션 종료 후 하네스가 실행. 시각 판정 항목은 `pass: null`로 자동 판정에서 제외 |
| 스크린샷 | UI 태스크(s1-fa-03, s1-nx-01, s1-nx-03, s1-nx-04, s1-nx-05)의 PNG만 `screens-blind/<task>/<code>/`에 복사, 조건 매핑은 `screens-key.jsonl` (블라인드 폴더 밖). 시각 판정은 수행하지 않음 |
| 환경 | 사용자 전역 `~/.claude`(CLAUDE.md, 플러그인, 훅) 상속 — 0단계와 동일. 태스크별 Postgres DB(:55432), fastapi 세션 env에 `DATABASE_URL`만 주입. s1-fa-03은 세션 전 `bun install --frozen-lockfile` |
| 도구 승인 | 110세션 모두 `permission_denials: []`, timeout 0 |

### 실행 중 발생한 하네스 수정 (기록)

- 첫 실패 판정(B s1-fa-03 r2)이 `bunx biome ci`에서 났고, 원인은 세션 코드가 아니라 사용자 전역 <E2 plugin> 훅이 쓴 `frontend/<E2 plugin>/state/idle-notif-cooldown.json`의 포맷이었음. 동결된 체크는 그대로 두고, 17:28:51부터 러너가 체크 직전에 worktree의 `<E2 plugin>/` 디렉터리를 지우도록 수정(전 조건 동일). 그 전에 체크가 돈 세션은 실행 종료 후 같은 방식으로 재검사(`scripts/recheck_s1.py`); 원래 결과는 meta의 `check_original`, 표는 재검사 결과. 재검사로 판정이 바뀐 세션은 아래 1절 끝에 나열.

### stage1/README.md 질문 11개 중 지시 기본값과 다르거나 지시에 없던 항목 (⚑)

- ⚑ 조건 라벨: 초안은 A 없음 / B 라우터 / C 전문가. 지시(“C는 search·load·MCP ready 추가”, “C에서 로컬 스킬 pin 허용”, “전문가 스킬 없는 5개는 A vs C”)에 맞춰 **A 없음 / B 전문가 / C 라우터**로 실행.
- ⚑ Q1 (전문가 스킬 전달 방식): 지시 없음 → load_skills 출력 형식 그대로 `--append-system-prompt-file`. 사용자 프롬프트는 전 조건 동일, B에는 MCP·라우터 없음.
- ⚑ Q6 (뮤턴트): 세션이 대상 코드를 바꿔 뮤턴트가 적용되지 않으면 `not_applicable`(잡음도 실패도 아님, `pass: null`), 체크 `pass`는 적용 가능한 뮤턴트만으로 판정.
- ⚑ Q7 (스크린샷 판정자): 미정 → 블라인드 폴더만 생성, 판정 안 함.
- Q2·Q3·Q4·Q5는 지시대로(5개 A/C만, 내장 스킬 유지, C = 머지된 라우터만·훅 없음, 2회). Q8 max-turns 25, Q9 프롬프트 초안 그대로, Q10 전역 환경 상속, Q11 음성 대조군 없음 — 0단계 하네스 그대로.
- 체크 작성 시 해석(`checks/VALIDATION.md` deviations): hidden test 위치 `backend/tests/hidden_s1/`, “58 existing pass” = 비-hidden 전부 pass이고 ≥58 pass, s1-fa-02 “previous head” = 업스트림 head `fe56fa70289e` 등.
- 세션이 Bash에서 `initdb`로 자체 Postgres를 띄운 세션: A 4 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-06-r1, s1-fa-06-r2), B 3 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-02-r2), C 5 (s1-fa-01-r2, s1-fa-02-r1, s1-fa-06-r1, s1-fa-09-r1, s1-fa-09-r2). 종료 후 남아 있던 서버 1개(C s1-fa-09-r2, `/tmp/pgcase.gg3d`, :54329)는 하네스가 정지·삭제. 체크는 세션 DB와 무관하게 하네스의 `chk_` DB에서 실행.

## 조건

- **A**: skillfetch 없음 (업스트림 트리, 레포 내장 fastapi/sqlmodel 스킬은 그대로)
- **B**: A + 전문가 스킬(`expert-skills.md` id를 pinned로 resolve_set/load_skills 한 출력)을 `--append-system-prompt-file`로 주입
- **C**: A + 머지된 라우터 스킬 + 프로젝트 `.mcp.json`(skillfetch). 로컬 스킬 `path:` pin 허용

## 1. 조건별 집계

### 전문가 스킬이 있는 15개 태스크 (A/B/C, 각 2회)

| 조건 | 세션 | check pass | check fail | check 없음/오류 | 중앙 턴 | 평균 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 duration s | 중앙 diff +/- (정제, lockfile 제외) | error_max_turns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 30 | 30 | 0 | 0 | 14 | 14.6 | 878,868 | 4,854 | 72 | 46/1 | 1 |
| B | 30 | 30 | 0 | 0 | 16 | 16.1 | 962,558 | 5,746 | 77 | 50/1 | 1 |
| C | 30 | 30 | 0 | 0 | 21 | 21.0 | 1,400,246 | 6,022 | 92 | 51/1 | 2 |

### 전문가 스킬이 없는 5개 태스크 (A/C, 각 2회)

| 조건 | 세션 | check pass | check fail | check 없음/오류 | 중앙 턴 | 평균 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 duration s | 중앙 diff +/- (정제, lockfile 제외) | error_max_turns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 10 | 0 | 0 | 8 | 11.6 | 576,564 | 2,922 | 43 | 24/3 | 0 |
| C | 10 | 10 | 0 | 0 | 14 | 16.9 | 1,019,950 | 3,547 | 52 | 22/3 | 1 |

### 전체 20개 태스크 (A/C, 각 2회)

| 조건 | 세션 | check pass | check fail | check 없음/오류 | 중앙 턴 | 평균 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 duration s | 중앙 diff +/- (정제, lockfile 제외) | error_max_turns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 40 | 40 | 0 | 0 | 13 | 13.8 | 772,719 | 4,487 | 62 | 42/1 | 1 |
| C | 40 | 40 | 0 | 0 | 19 | 19.9 | 1,227,728 | 5,612 | 71 | 45/1 | 3 |

### 종류별 check pass (세션 수 기준)

| 종류 | 태스크 수 | A | B (전문가 있는 태스크만) | C |
|---|---|---|---|---|
| feature | 7 | 14/14 | 10/10 | 14/14 |
| refactor | 4 | 8/8 | 6/6 | 8/8 |
| test | 4 | 8/8 | 8/8 | 8/8 |
| bugfix | 3 | 6/6 | 2/2 | 6/6 |
| docs | 2 | 4/4 | 4/4 | 4/4 |

### C: skillfetch 사용

- `search_skills` 호출 세션: 31/40; search→resolve→load 완주: 29; search만: 2
- 로드 스킬 수(완주 세션) 중앙 1, load 토큰 중앙 4,160
- 로컬 `path:` pin 포함 세션: 7
- MCP ready (spawn 기준) 중앙 3.1s, 범위 2.4–14.8s; 연결 실패 0
- 종류별 search 호출: feature 12/14, refactor 5/8, test 8/8, bugfix 4/6, docs 2/4; 언어별: en 15/20, ko 16/20
- search 미호출 C 세션: s1-fa-01-r2, s1-fa-04-r1, s1-fa-04-r2, s1-fa-05-r2, s1-fa-10-r2, s1-nx-03-r2, s1-nx-09-r1, s1-nx-09-r2, s1-nx-10-r2
- B 주입 토큰(전문가 세트 token_estimate 합) 중앙 3,957

### 재검사 (`<E2 plugin>` 제거 후)

- 재검사 세션 26개, 판정 변경 1개: B s1-fa-03-r2 (False → True)
- `<E2 plugin>/`가 지워진 세션(체크 직전): 110/110

## 2. 태스크별 상세

### s1-fa-01 — feature/en

> GET /api/v1/items/ always sorts newest first. Add an `order_by` query parameter that accepts `created_at` (default) or `title`, and an `order` parameter that accepts `asc` or `desc` (default `desc`). Any other value should be rejected with a 422.

전문가 스킬(B): `uasl/api-design`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 21 | 1,347,983 | 6,109 | 107 | +73/-6 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 16 | 1,057,937 | 7,173 | 82 | +83/-6 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 18 | 1,211,557 | 5,831 | 75 | +69/-6 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 25 | 1,965,107 | 10,167 | 139 | +120/-6 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 29 | 2,229,956 | 7,354 | 103 | +86/-6 | success | Add validated order_by and order query parameters to the FastAPI GET /api/v1/items/ endpoint with SQLModel sorting and 422 on invalid values, with tests | `fastapi(local)`, `sqlmodel(local)` | 4,451 | 4.0 | 9.7 |
| C | 2 | pass | - | - | 24 | 1,613,333 | 8,276 | 103 | +88/-6 | success |  |  | - | 2.7 | - |

### s1-fa-02 — feature/ko

> 아이템에 완료 여부를 나타내는 `is_done` 불리언 필드를 추가해줘. 기본값은 false이고, 아이템 생성·수정·조회 API에서 다룰 수 있어야 해. 기존 데이터가 있는 DB에도 적용되도록 alembic 마이그레이션도 만들어줘.

전문가 스킬(B): `uasl/postgresql-table-design`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 26 | 2,376,944 | 11,462 | 175 | +70/-0 | error_max_turns |  |  |  |  |  |
| A | 2 | pass | - | - | 26 | 1,863,116 | 9,917 | 131 | +64/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 26 | 2,568,054 | 11,638 | 190 | +64/-0 | error_max_turns |  |  |  |  |  |
| B | 2 | pass | - | - | 25 | 1,915,761 | 9,659 | 151 | +70/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 30 | 2,224,647 | 10,590 | 138 | +65/-0 | success | Add an is_done boolean field (default false) to the SQLModel Item model in a FastAPI backend, expose it in create/update/read API schemas, and write an Alembic migration that applies to existing databases | `sqlmodel(local)`, `fastapi(local)` | 4,451 | 6.3 | 13.1 |
| C | 2 | pass | - | - | 26 | 2,489,499 | 10,754 | 131 | +62/-0 | error_max_turns | Add an is_done boolean field (default false) to the Item SQLModel model in a FastAPI backend, expose it in item create/update/read APIs, and write an Alembic migration for existing databases |  | - | 2.9 | 9.4 |

### s1-fa-03 — feature/ko (UI)

> 프론트엔드 대시보드(/)가 인사말만 있고 비어 있어. 내 아이템 개수와 가장 최근 아이템 3개의 제목을 보여주는 카드를 대시보드에 추가해줘. 기존 UI 컴포넌트 스타일에 맞춰줘.

전문가 스킬(B): `uasl/shadcn`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | visual screens/ | 9 | 772,908 | 4,216 | 66 | +84/-1 | success |  |  |  |  |  |
| A | 2 | pass | - | visual screens/ | 13 | 771,286 | 5,073 | 81 | +98/-1 | success |  |  |  |  |  |
| B | 1 | pass | - | visual screens/ | 12 | 826,469 | 5,561 | 62 | +110/-1 | success |  |  |  |  |  |
| B | 2 | pass | - | visual screens/ | 9 | 830,385 | 4,423 | 63 | +87/-1 | success |  |  |  |  |  |
| C | 1 | pass | - | visual screens/ | 20 | 1,340,334 | 6,040 | 68 | +92/-1 | success | Add a dashboard card to the React frontend home page showing the current user's item count and the titles of the three most recent items, matching existing UI component styles | `uasl/design-to-code` | 659 | 3.8 | 9.1 |
| C | 2 | pass | - | visual screens/ | 19 | 1,448,712 | 6,005 | 92 | +107/-1 | success | Add a dashboard card to the React TypeScript frontend home route showing the user's item count and three most recent item titles, matching existing UI component styles | `uasl/design-to-code` | 659 | 3.0 | 13.1 |

블라인드 스크린샷: `screens-blind/s1-fa-03/` (6개 폴더, 조건 매핑은 `screens-key.jsonl`)

### s1-fa-04 — refactor/en

> read_item, update_item and delete_item in backend/app/api/routes/items.py each repeat the same "load the item, 404 if missing, 403 if not the owner and not a superuser" block. Move it into one reusable FastAPI dependency (or helper) and use it in all three. The API behaviour must not change.

전문가 스킬(B): `uasl/refactoring-patterns`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 17 | 895,497 | 4,969 | 61 | +28/-18 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 11 | 589,052 | 3,917 | 70 | +17/-16 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 16 | 1,125,599 | 6,571 | 111 | +28/-18 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 17 | 1,222,785 | 8,304 | 112 | +28/-18 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 13 | 677,556 | 4,613 | 64 | +26/-18 | success |  |  | - | 3.0 | - |
| C | 2 | pass | - | - | 12 | 589,751 | 4,046 | 55 | +25/-18 | success |  |  | - | 2.9 | - |

### s1-fa-05 — refactor/ko

> users.py의 사용자 목록과 items.py의 아이템 목록 엔드포인트가 skip/limit 파라미터를 각자 선언하고 있어. 공통 페이지네이션 의존성 하나로 묶어서 두 엔드포인트가 같이 쓰게 해줘. 기존 동작(기본값 skip=0, limit=100)은 그대로 유지해.

전문가 스킬(B): `uasl/python-design-patterns`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 21 | 992,777 | 5,849 | 91 | +28/-7 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 20 | 998,031 | 5,669 | 117 | +24/-7 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 19 | 959,997 | 5,662 | 66 | +24/-7 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 19 | 949,660 | 5,207 | 65 | +28/-7 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 26 | 1,571,920 | 6,859 | 87 | +24/-7 | success | Refactor FastAPI user list and item list endpoints in users.py and items.py to share a common pagination dependency for skip/limit query parameters | `fastapi(local)` | 2,451 | 4.1 | 11.6 |
| C | 2 | pass | - | - | 21 | 1,185,646 | 7,090 | 95 | +28/-7 | success |  |  | - | 2.6 | - |

### s1-fa-06 — test/en

> There are no tests showing that a normal user's GET /api/v1/items/ only returns their own items. Add tests that cover the item list and its `count` for a normal user who owns some items while other users own others.

전문가 스킬(B): `uasl/integration-testing`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 19 | 1,246,229 | 5,650 | 77 | +67/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 16 | 1,150,976 | 6,564 | 88 | +57/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 29 | 2,315,269 | 9,917 | 169 | +71/-3 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 20 | 1,371,550 | 7,204 | 98 | +84/-3 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 27 | 2,631,294 | 11,321 | 174 | +73/-0 | success | Add pytest tests for the FastAPI GET /api/v1/items/ endpoint verifying a normal user only sees their own items and the correct count when other users own items | `uasl/python-testing-patterns` | 6,213 | 3.2 | 14.2 |
| C | 2 | pass | - | - | 29 | 2,200,526 | 7,706 | 103 | +75/-0 | success | Add pytest tests for the FastAPI SQLModel backend verifying GET /api/v1/items/ returns only the normal user's own items and correct count in backend/tests/api/routes/test_items.py | `uasl/radar` | 2,635 | 2.6 | 9.7 |

### s1-fa-07 — test/ko

> 인증 의존성 get_current_user(backend/app/api/deps.py)에 대한 테스트가 없어. 잘못된 서명의 토큰, 만료된 토큰, 삭제된 사용자의 토큰, 비활성 사용자의 토큰 각각에 대해 API가 어떤 응답을 주는지 테스트를 작성해줘.

전문가 스킬(B): `uasl/python-testing-patterns`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 10 | 772,149 | 4,277 | 55 | +63/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 16 | 957,267 | 4,700 | 74 | +65/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 22 | 1,362,322 | 6,213 | 90 | +65/-0 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 16 | 965,120 | 4,771 | 78 | +70/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 24 | 1,784,732 | 5,317 | 103 | +65/-0 | success | Add pytest tests for the FastAPI get_current_user dependency in backend/app/api/deps.py covering invalid-signature, expired, deleted-user and inactive-user JWT tokens | `uasl/python-testing-patterns` | 6,213 | 14.3 | 16.1 |
| C | 2 | pass | - | - | 18 | 1,387,298 | 5,907 | 92 | +54/-0 | success | Write pytest tests for the FastAPI authentication dependency get_current_user in backend/app/api/deps.py covering invalid JWT signature, expired token, deleted user, and inactive user | `fastapi(local)` | 2,451 | 14.8 | 16.7 |

### s1-fa-08 — bugfix/en

> Sending PUT /api/v1/items/{id} with {"title": null} makes the server return a 500. It should be rejected as a validation error and the item must stay unchanged.

전문가 스킬(B): `uasl/defense-in-depth`, `uasl/api-design`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 16 | 1,138,136 | 6,184 | 122 | +34/-1 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 13 | 938,517 | 4,739 | 63 | +26/-1 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 16 | 1,306,638 | 6,555 | 81 | +43/-1 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 14 | 1,007,552 | 4,749 | 88 | +43/-1 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 25 | 1,966,653 | 7,835 | 116 | +24/-1 | success | Fix a FastAPI PUT /api/v1/items/{id} update endpoint that returns 500 when a non-nullable field like title is sent as null, so it is rejected with a 422 validation error and the item is not modified | `fastapi(local)`, `uasl/fastapi-endpoint` | 6,215 | 4.4 | 12.8 |
| C | 2 | pass | - | - | 25 | 1,984,868 | 6,307 | 143 | +42/-1 | success | Fix a FastAPI SQLModel PUT /api/v1/items/{id} endpoint in backend/app so that sending null for a required field like title returns a 422 validation error instead of a 500, with a regression test | `fastapi(local)`, `sqlmodel(local)` | 4,451 | 2.6 | 30.2 |

### s1-fa-09 — bugfix/ko

> 대소문자만 다른 이메일로 회원가입하면 계정이 하나 더 생겨요 (foo@example.com이 있는데 FOO@example.com으로 가입 가능). 그리고 ADMIN@EXAMPLE.COM으로는 로그인이 안 돼요. 이메일은 대소문자 구분 없이 같은 계정으로 취급되게 고쳐줘.

전문가 스킬(B): 없음 → A/C만

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 26 | 1,840,927 | 11,581 | 175 | +93/-13 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 24 | 1,845,228 | 10,821 | 133 | +103/-13 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 42 | 2,464,191 | 14,436 | 206 | +97/-12 | success | Fix a FastAPI/SQLModel backend bug so user emails are treated case-insensitively for signup uniqueness and login, normalizing email in the user CRUD and auth routes, with pytest tests | `uasl/systematic-debug` | 3,034 | 11.4 | 15.6 |
| C | 2 | pass | - | - | 26 | 2,601,828 | 11,783 | 288 | +128/-12 | error_max_turns | Fix a FastAPI SQLModel backend bug so user email signup and login are case-insensitive, preventing duplicate accounts that differ only in letter case | `fastapi(local)`, `sqlmodel(local)` | 4,451 | 5.2 | 123.9 |

### s1-fa-10 — docs/en

> Add a table of the backend's configuration environment variables to backend/README.md, based on Settings in app/core/config.py: name, default value (mark it as required if there is none) and a short description.

전문가 스킬(B): `uasl/quill`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 9 | 772,530 | 3,260 | 44 | +29/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 7 | 508,974 | 2,971 | 29 | +29/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 8 | 532,675 | 3,106 | 31 | +29/-0 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 9 | 624,494 | 3,304 | 32 | +29/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 13 | 879,081 | 3,882 | 44 | +29/-0 | success | Document the FastAPI backend's pydantic-settings environment variables from backend/app/core/config.py as a table in backend/README.md |  | - | 4.7 | 9.9 |
| C | 2 | pass | - | - | 9 | 518,927 | 3,736 | 43 | +29/-0 | success |  |  | - | 3.0 | - |

### s1-nx-01 — feature/en (UI)

> On the user detail page, add links labelled "Previous" and "Next" to the neighbouring users (in the order of the users list) and a "Back to list" link to /users. The first user has no Previous link and the last user has no Next link.

전문가 스킬(B): 없음 → A/C만

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | visual screens/users/101, visual screens/users/102, visual screens/users/104 | 13 | 667,208 | 3,181 | 38 | +19/-3 | success |  |  |  |  |  |
| A | 2 | pass | - | visual screens/users/101, visual screens/users/102, visual screens/users/104 | 10 | 583,253 | 2,841 | 41 | +30/-3 | success |  |  |  |  |  |
| C | 1 | pass | - | visual screens/users/101, visual screens/users/102, visual screens/users/104 | 19 | 1,082,167 | 3,558 | 49 | +26/-3 | success | Add Previous/Next and Back to list navigation links to the Next.js TypeScript user detail page (pages/users/[id].tsx) based on the order of the users list | `uasl/frontend-patterns` | 3,808 | 3.1 | 10.1 |
| C | 2 | pass | - | visual screens/users/101, visual screens/users/102, visual screens/users/104 | 19 | 1,097,314 | 3,536 | 49 | +18/-3 | success | Add Previous/Next navigation links and a Back to list link to the Next.js TypeScript user detail page (pages/users/[id].tsx) based on the order of the users list | `uasl/frontend-patterns`, `uasl/vercel-react-best-practices` | 5,369 | 2.5 | 9.6 |

블라인드 스크린샷: `screens-blind/s1-nx-01/` (4개 폴더, 조건 매핑은 `screens-key.jsonl`)

### s1-nx-02 — feature/en

> Add an API endpoint GET /api/users/[id] that returns one user as JSON. Return 404 with a JSON error message if no user has that id, and 400 if the id is not a number.

전문가 스킬(B): `uasl/backend-patterns`, `uasl/api-design`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 7 | 572,483 | 2,746 | 54 | +40/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 6 | 492,227 | 2,577 | 44 | +40/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 6 | 553,999 | 2,200 | 42 | +33/-0 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 6 | 553,636 | 2,325 | 43 | +33/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 17 | 1,086,481 | 3,394 | 63 | +41/-0 | success | Add a Next.js TypeScript API route GET /api/users/[id] that returns a user as JSON with 404 and 400 error handling | `uasl/next-best-practices`, `uasl/api-design` | 4,160 | 2.8 | 12.9 |
| C | 2 | pass | - | - | 16 | 1,084,803 | 3,238 | 45 | +40/-0 | success | Add a Next.js TypeScript API route GET /api/users/[id] that returns a user as JSON with 404 and 400 error handling | `uasl/next-best-practices`, `uasl/api-design` | 4,160 | 2.9 | 9.1 |

### s1-nx-03 — feature/ko (UI)

> 없는 주소로 들어가면 Next.js 기본 404 화면이 나와. 사이트 Layout(상단 내비게이션, 푸터 포함)을 쓰는 404 페이지를 만들고 "페이지를 찾을 수 없습니다" 문구와 홈으로 가는 링크를 넣어줘.

전문가 스킬(B): 없음 → A/C만

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | visual screens/does-not-exist, visual screens/users/999 | 7 | 569,875 | 1,844 | 27 | +13/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | visual screens/does-not-exist, visual screens/users/999 | 5 | 324,216 | 1,315 | 32 | +13/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | visual screens/does-not-exist, visual screens/users/999 | 14 | 1,052,996 | 2,561 | 64 | +14/-0 | success | Add a custom 404 Not Found page to a Next.js TypeScript app that uses the shared site Layout component (navigation and footer), with a "page not found" message and a link back to home | `uasl/vercel-react-best-practices` | 1,561 | 3.0 | 16.1 |
| C | 2 | pass | - | visual screens/does-not-exist, visual screens/users/999 | 8 | 571,884 | 1,897 | 32 | +14/-0 | success |  |  | - | 3.1 | - |

블라인드 스크린샷: `screens-blind/s1-nx-03/` (4개 폴더, 조건 매핑은 `screens-key.jsonl`)

### s1-nx-04 — feature/ko (UI)

> About 페이지에 우리 팀 소개 섹션을 넣어줘. utils/sample-data.ts의 유저들을 카드 그리드로 보여주고, 카드마다 이름, ID, 상세 페이지 링크를 넣어줘. 화면이 좁으면 한 줄에 한 장씩 보이게 해줘.

전문가 스킬(B): `uasl/responsive-design`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | visual screens/about, visual screens-375/about | 8 | 499,281 | 3,047 | 41 | +67/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | visual screens/about, visual screens-375/about | 6 | 492,135 | 2,251 | 36 | +45/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | visual screens/about, visual screens-375/about | 7 | 526,749 | 2,654 | 34 | +62/-0 | success |  |  |  |  |  |
| B | 2 | pass | - | visual screens/about, visual screens-375/about | 8 | 617,802 | 3,288 | 43 | +58/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | visual screens/about, visual screens-375/about | 13 | 992,274 | 3,675 | 47 | +65/-0 | success | Add a responsive team section to the Next.js TypeScript About page that renders users from utils/sample-data.ts as a card grid with name, ID and a link to each user's detail page, collapsing to one card per row on narrow screens | `uasl/responsive-design`, `uasl/vercel-react-best-practices` | 4,593 | 2.4 | 8.1 |
| C | 2 | pass | - | visual screens/about, visual screens-375/about | 13 | 1,002,673 | 3,492 | 53 | +48/-0 | success | Add a responsive team intro section to the Next.js TypeScript About page rendering users from utils/sample-data.ts as a card grid with name, ID, and a link to each user's detail page, one card per row on narrow screens | `uasl/responsive-design`, `uasl/vercel-react-best-practices` | 4,593 | 3.6 | 12.9 |

블라인드 스크린샷: `screens-blind/s1-nx-04/` (6개 폴더, 조건 매핑은 `screens-key.jsonl`)

### s1-nx-05 — refactor/ko (UI)

> Layout 컴포넌트의 상단 내비게이션 링크를 하드코딩 대신 배열 하나로 정의해서 렌더링하게 바꾸고, 현재 페이지에 해당하는 링크에는 aria-current="page"를 붙여줘. 보이는 모양은 지금과 같게 유지해.

전문가 스킬(B): 없음 → A/C만

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | diff review: nav links defined in one array, visual screens/, visual screens/about, visual screens/users | 8 | 491,356 | 3,003 | 44 | +55/-22 | success |  |  |  |  |  |
| A | 2 | pass | - | diff review: nav links defined in one array, visual screens/, visual screens/about, visual screens/users | 9 | 657,787 | 3,213 | 57 | +54/-21 | success |  |  |  |  |  |
| C | 1 | pass | - | diff review: nav links defined in one array, visual screens/, visual screens/about, visual screens/users | 13 | 986,904 | 3,762 | 56 | +55/-22 | success | Refactor the Next.js TypeScript Layout component's top navigation links into a single array rendered with map, adding aria-current="page" to the link for the current route while keeping the visual output unchanged | `uasl/accessibility-compliance`, `uasl/next-best-practices` | 3,821 | 4.4 | 11.7 |
| C | 2 | pass | - | diff review: nav links defined in one array, visual screens/, visual screens/about, visual screens/users | 14 | 985,920 | 3,741 | 62 | +55/-22 | success | Refactor the Next.js React TypeScript Layout component's top navigation links into a single data array rendered with map, adding aria-current="page" to the active link while keeping the visual appearance unchanged | `uasl/accessibility-compliance`, `uasl/vercel-react-best-practices` | 4,440 | 8.4 | 13.8 |

블라인드 스크린샷: `screens-blind/s1-nx-05/` (4개 폴더, 조건 매핑은 `screens-key.jsonl`)

### s1-nx-06 — refactor/en

> Pages and the API route import sampleUserData directly. Put all user data access behind a small module lib/users.ts with getAllUsers() and getUserById(id), and use it everywhere. Rendered pages and API output must stay exactly the same.

전문가 스킬(B): `uasl/refactoring-patterns`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 20 | 773,547 | 4,697 | 61 | +21/-8 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 22 | 862,238 | 5,158 | 77 | +18/-8 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 19 | 739,635 | 4,933 | 60 | +18/-8 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 21 | 940,511 | 5,830 | 82 | +18/-8 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 26 | 1,269,809 | 6,448 | 74 | +18/-8 | success | Refactor a Next.js TypeScript app so pages and API routes access user data through a new lib/users.ts data-access module with getAllUsers and getUserById instead of importing sample data directly, keeping output identical | `uasl/next-best-practices` | 942 | 2.7 | 9.3 |
| C | 2 | pass | - | - | 27 | 1,413,194 | 6,083 | 137 | +18/-8 | success | Refactor a Next.js TypeScript app so pages and the API route access user data through a new lib/users.ts module with getAllUsers() and getUserById(id) instead of importing sampleUserData directly, preserving output | `uasl/zen`, `uasl/next-best-practices` | 4,072 | 3.5 | 50.9 |

### s1-nx-07 — test/ko

> 이 프로젝트엔 테스트 러너가 없어. Vitest와 React Testing Library를 설정하고 `npm test`로 돌아가게 한 다음, ListDetail 컴포넌트(이름과 ID 표시)와 Layout 컴포넌트(내비게이션 링크 4개와 제목) 테스트를 작성해줘.

전문가 스킬(B): `uasl/tdd-workflow`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 21 | 1,521,057 | 9,015 | 111 | +114/-5 (lock +2108/-110) | success |  |  |  |  |  |
| A | 2 | pass | - | - | 19 | 1,334,450 | 9,096 | 138 | +116/-5 (lock +2108/-110) | success |  |  |  |  |  |
| B | 1 | pass | - | - | 23 | 1,725,733 | 9,688 | 142 | +109/-5 (lock +2108/-110) | success |  |  |  |  |  |
| B | 2 | pass | - | - | 23 | 1,685,222 | 10,850 | 147 | +106/-5 (lock +2108/-110) | success |  |  |  |  |  |
| C | 1 | pass | - | - | 32 | 2,476,343 | 9,732 | 162 | +110/-5 (lock +2108/-110) | success | Set up Vitest with React Testing Library in a Next.js TypeScript project so npm test runs, and write component tests for ListDetail and Layout components | `uasl/unit-testing` | 5,809 | 3.5 | 13.5 |
| C | 2 | pass | - | - | 26 | 2,420,566 | 9,392 | 155 | +114/-5 (lock +2108/-110) | error_max_turns | Set up Vitest with React Testing Library in a Next.js TypeScript project so npm test runs, and write component tests for ListDetail and Layout | `uasl/tdd-workflow` | 2,357 | 2.8 | 13.1 |

### s1-nx-08 — test/en

> Add tests for getStaticPaths and getStaticProps in pages/users/[id].tsx: the generated paths, the props for an existing id, and what happens for an unknown id.

전문가 스킬(B): `uasl/unit-testing`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 13 | 963,386 | 5,232 | 99 | +56/-1 (lock +5232/-776) | success |  |  |  |  |  |
| A | 2 | pass | - | - | 9 | 579,088 | 3,128 | 58 | +47/-1 (lock +5232/-776) | success |  |  |  |  |  |
| B | 1 | pass | - | - | 11 | 947,650 | 5,846 | 69 | +57/-2 (lock +1205/-45) | success |  |  |  |  |  |
| B | 2 | pass | - | - | 12 | 1,046,734 | 5,864 | 92 | +43/-3 (lock +1227/-57) | success |  |  |  |  |  |
| C | 1 | pass | - | - | 19 | 1,528,177 | 5,993 | 130 | +63/-1 (lock +5232/-776) | success | Add Jest unit tests for the Next.js Pages Router getStaticPaths and getStaticProps functions in TypeScript file pages/users/[id].tsx | `uasl/radar`, `uasl/typescript-unit-testing` | 5,999 | 7.5 | 11.8 |
| C | 2 | pass | - | - | 16 | 1,166,501 | 4,088 | 60 | +67/-1 (lock +5232/-776) | success | Add unit tests for the Next.js Pages Router data-fetching functions getStaticPaths and getStaticProps in pages/users/[id].tsx (TypeScript), covering generated paths, props for an existing id, and an unknown id | `uasl/radar` | 2,635 | 2.9 | 9.6 |

### s1-nx-09 — bugfix/ko

> 스크린리더 점검에서 지적받았는데, 모든 페이지의 <html> 태그에 lang 속성이 없대. 콘텐츠가 영어니까 모든 페이지(404 포함)에 lang="en"이 들어가게 고쳐줘.

전문가 스킬(B): 없음 → A/C만

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 7 | 491,729 | 2,162 | 38 | +13/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 7 | 569,168 | 1,752 | 46 | +13/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 7 | 569,390 | 1,705 | 30 | +13/-0 | success |  |  | - | 2.4 | - |
| C | 2 | pass | - | - | 7 | 572,235 | 2,352 | 33 | +13/-0 | success |  |  | - | 3.0 | - |

### s1-nx-10 — docs/en

> Add JSDoc comments to every component in components/ and every exported type in interfaces/ describing what it renders or represents and what each prop/field means. Do not change any code.

전문가 스킬(B): `uasl/quill`

| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | pass | - | - | 13 | 414,195 | 2,846 | 30 | +29/-0 | success |  |  |  |  |  |
| A | 2 | pass | - | - | 8 | 326,559 | 2,132 | 34 | +25/-0 | success |  |  |  |  |  |
| B | 1 | pass | - | - | 14 | 524,226 | 2,802 | 32 | +29/-0 | success |  |  |  |  |  |
| B | 2 | pass | - | - | 14 | 523,990 | 3,012 | 31 | +32/-0 | success |  |  |  |  |  |
| C | 1 | pass | - | - | 21 | 892,430 | 3,848 | 42 | +29/-0 | success | Add JSDoc comments to the React TypeScript components in components/ and the exported types in interfaces/index.ts of a Next.js app, without changing any code | `uasl/quill` | 3,133 | 3.2 | 11.2 |
| C | 2 | pass | - | - | 13 | 410,015 | 2,561 | 27 | +25/-0 | success |  |  | - | 2.9 | - |

