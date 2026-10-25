# skillfetch 1b — 5태스크 × A/B/C × 2회 (report)

실행 2026-10-22 KST 20:59–21:31, 30세션 (5태스크 × A/B/C × 2회), 고정 시드 큐(`runs/_queue.txt`), 동시 4. 숫자는 `scripts/report_s1b.py`, 블라인드 판정 원본 `blind-ranking.md`, unblind 결과 `blind-ranking-results.md`.

## 0. 설정

| 항목 | 값 |
|---|---|
| 하네스 | 1단계와 동일(`stage1/scripts/run_stage1.py`의 prepare/세션/diff 함수 재사용). 차이: `--max-turns 40`, 프론트 태스크(s1b-fa-landing, s1b-fa-tags-plan)는 세션 전 `bun install --frozen-lockfile`, 체크는 `checks/run_check_1b.py` |
| 조건 | A 업스트림 트리(레포 내장 fastapi/sqlmodel 스킬 유지) / B A + 전문가 스킬의 `load_skills` 출력(`expert-content/<id>.md`)을 `--append-system-prompt-file` / C 머지된 라우터(`main@96f0f3b` SKILL.md, 1단계와 같은 `s1-c` 브랜치) + `.mcp.json` |
| 전문가 스킬(B) | s1b-nx-landing·s1b-fa-landing `anthropics-skills/frontend-design`(2268 tok), s1b-fa-tags-plan `uasl/writing-plans`(1315), s1b-fa-service `uasl/caveman`(401), s1b-fa-utils-tests `uasl/tdd`(1032). 5번은 `uasl/tdd`(top-50 #44)가 `uasl/test-driven-development`(#47)보다 상위라 선택. 인덱스 순위(내 영어 재서술 쿼리, k=50): frontend-design nx #34·fa #9, writing-plans #38, caveman >50, tdd #44 — `expert-index-ranks.txt` |
| skillfetch | 서버 `uvx --from git+…` HEAD `53b81df`(실행 전후 동일). 1단계(`96f0f3b`) 이후 변경은 `cli.py`, `ingest/obedience.py`, 문서·테스트뿐 — `mcp/`, `index/`, `resolve/`, 라우터 스킬 변경 없음. 인덱스 `built_at` 2026-10-22T06:15:43Z(30세션 동일) |
| 체크 | 세션 전 작성·검증·동결(`checks/FROZEN.sha256`: run_check_1b.py + 재사용한 1단계 run_check.py·screenshot.py). 업스트림 트리에서 5개 모두 실패, 최소 참조 구현에서 5개 모두 통과(`checks/VALIDATION.md`). 체크 직전 `<E2 plugin>/` 제거(1단계와 동일) |
| 블라인드 | 랜딩 2태스크 PNG(데스크톱 1280 + 모바일 375) → `screens-blind/`, 플랜 태스크 PLAN.md + 구현 diff → `plans-blind/`(skill·skillfetch·router 도구 이름 `[redacted]` 6회). 매핑은 `screens-key.jsonl`, `plans-key.jsonl` |
| 도구 승인 | 30세션 모두 `permission_denials: []` |

### 기록 사항

- **판정자 1명(이 세션)**. 판정 전 1b `runs/`·키 파일은 열지 않았다. 실행 후 남은 프로세스 정리 중 `s1b-fa-tags-plan-A-r1` worktree 경로가 프로세스 목록에 보였다(그 세션이 띄운 vite dev 서버와 `/tmp/pgtags.*` Postgres를 하네스가 정지·삭제).
- **플랜 형식 단서**: 플랜 2개(c92f3fba, f8953e63)는 writing-plans 계열 형식("For agentic workers … subagent-driven-development / executing-plans", 체크박스 단계)이 redaction 후에도 남아 판정 시 보였다. unblind 결과 두 개 모두 **B**(writing-plans 주입 조건)였다.
- **결과 이벤트가 여러 개인 세션**: B s1b-fa-tags-plan r1·r2는 stream에 result 이벤트가 3개씩 있다(첫 번째 `error_max_turns` 41턴, 이어서 백그라운드 Agent 완료 후 후속 턴 2개). 표의 턴·시간·토큰은 세 구간 합계, subtype은 `error_max_turns (+2 follow-up)`. 0단계·0.5단계·1단계 180세션은 모두 result 이벤트 1개.
- **체크 실패 2건의 원인(세션 산출물)**: A s1b-fa-tags-plan r1 — 세션이 고친 `frontend/tests/items.spec.ts`가 biome 포맷 불일치. C s1b-fa-landing r1 — 세션이 실행한 Playwright가 남긴 `frontend/test-results/.last-run.json`이 biome 포맷 검사에 걸림.
- **s1b-fa-tags-plan은 6세션 모두 `--max-turns 40`에 도달**(B 2개는 그 뒤 후속 턴 진행).

## 1. 조건별 집계

| 태스크 | 조건 | check pass | 중앙 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 시간 s | error_max_turns |
|---|---|---|---|---|---|---|---|
| s1b-nx-landing | A | 2/2 | 25 | 2,040,503 | 25,570 | 255 | 0 |
| s1b-nx-landing | B | 2/2 | 29 | 2,296,860 | 23,064 | 394 | 0 |
| s1b-nx-landing | C | 2/2 | 37 | 2,859,273 | 22,894 | 248 | 0 |
| s1b-fa-landing | A | 2/2 | 18 | 1,405,058 | 8,766 | 117 | 0 |
| s1b-fa-landing | B | 2/2 | 24 | 1,962,316 | 15,498 | 179 | 0 |
| s1b-fa-landing | C | 1/2 | 38 | 2,708,836 | 14,410 | 170 | 0 |
| s1b-fa-tags-plan | A | 1/2 | 41 | 4,971,364 | 31,947 | 367 | 2 |
| s1b-fa-tags-plan | B | 2/2 | 48 | 6,762,960 | 48,398 | 763 | 2 |
| s1b-fa-tags-plan | C | 2/2 | 41 | 5,162,615 | 30,552 | 334 | 2 |
| s1b-fa-service | A | 2/2 | 18 | 1,198,680 | 7,456 | 89 | 0 |
| s1b-fa-service | B | 2/2 | 22 | 1,575,148 | 8,540 | 110 | 0 |
| s1b-fa-service | C | 2/2 | 28 | 2,314,739 | 9,116 | 128 | 0 |
| s1b-fa-utils-tests | A | 2/2 | 13 | 970,864 | 7,201 | 95 | 0 |
| s1b-fa-utils-tests | B | 2/2 | 16 | 1,158,498 | 9,355 | 102 | 0 |
| s1b-fa-utils-tests | C | 2/2 | 20 | 1,543,604 | 8,286 | 122 | 0 |

- A 전체: check pass 9/10, 중앙 턴 20, 중앙 입력 1,405,058, 중앙 출력 8,766
- B 전체: check pass 10/10, 중앙 턴 24, 중앙 입력 1,754,410, 중앙 출력 15,498
- C 전체: check pass 9/10, 중앙 턴 34, 중앙 입력 2,708,836, 중앙 출력 14,410

## 2. C: 전문가 스킬이 search top-10에 들었나, 실제 로드

| 태스크 | run | search | query | 전문가 스킬 (top-10 순위) | 로드한 스킬 | load 토큰 | MCP ready s | 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|
| s1b-nx-landing | r1 | Y (search+resolve+load) | Build a new product landing page at the /landing route in a Next.js TypeScript app with hero, three feature sections, pricing, and call-to-action | `anthropics-skills/frontend-design` 없음 | `uasl/taste-skill`, `uasl/next-best-practices` | 6,162 | 3.2 | 14.1 |
| s1b-nx-landing | r2 | Y (search+resolve+load) | Build a new product landing page at the /landing route in a Next.js TypeScript pages-router app with hero, three feature cards, pricing section and call-to-action | `anthropics-skills/frontend-design` 없음 | `uasl/next-best-practices`, `uasl/taste-skill` | 6,162 | 2.8 | 11.2 |
| s1b-fa-landing | r1 | Y (search+resolve+load) | Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards, and a call-to-action, served by a FastAPI app | `anthropics-skills/frontend-design` 없음 | `fastapi(local)`, `uasl/landing-page`, `uasl/copywriting` | 7,045 | 3.8 | 10.4 |
| s1b-fa-landing | r2 | Y (search+resolve+load) | Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards and a call-to-action in this repo's frontend | `anthropics-skills/frontend-design` 없음 | `uasl/frontend-design`, `uasl/copywriting` | 4,151 | 4.0 | 10.7 |
| s1b-fa-tags-plan | r1 | Y (search+resolve+load) | Add a tags feature to items in a FastAPI + SQLModel full-stack app: write a PLAN.md, then add a Tag model with many-to-many link to Item, an Alembic migration, REST API endpoints, and React frontend UI | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)`, `uasl/api-design` | 7,669 | 3.4 | 12.9 |
| s1b-fa-tags-plan | r2 | Y (search+resolve+load) | Add a tags feature to items in a FastAPI + SQLModel backend with Alembic migration, REST API endpoints, and a React TypeScript frontend, writing a PLAN.md implementation plan first | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)`, `uasl/fastapi-endpoint` | 8,215 | 2.8 | 10.7 |
| s1b-fa-service | r1 | Y (search+resolve+load) | Refactor the FastAPI items router by extracting its business logic into a separate service layer module | `uasl/caveman` 없음 | `fastapi(local)`, `uasl/fastapi-templates` | 6,133 | 4.5 | 10.7 |
| s1b-fa-service | r2 | Y (search+resolve+load) | Refactor the FastAPI items router by extracting its business logic into a separate service layer module in Python | `uasl/caveman` 없음 | `uasl/fastapi-templates`, `uasl/python-design-patterns` | 6,698 | 2.4 | 9.4 |
| s1b-fa-utils-tests | r1 | Y (search+resolve+load) | Add pytest unit tests for the Python FastAPI backend utility module backend/app/utils.py | `uasl/tdd` 없음 | `uasl/python-testing-patterns` | 6,213 | 3.5 | 19.3 |
| s1b-fa-utils-tests | r2 | Y (search+resolve+load) | Add pytest unit tests for the FastAPI backend helper module backend/app/utils.py in backend/tests/ | `uasl/tdd` 없음 | `uasl/python-testing-patterns` | 6,213 | 3.1 | 14.5 |

## 3. 태스크별 측정

### s1b-fa-tags-plan — PLAN.md를 코드보다 먼저 썼나 (세션 로그의 Write/Edit 순서)

| 조건 | run | PLAN.md 경로 | PLAN.md 편집 순번 | 첫 코드 편집 순번 | 플랜 먼저 | check | 실패 항목 |
|---|---|---|---|---|---|---|---|
| A | r1 | ['PLAN.md'] | 10 | 13 | Y | False | frontend: bunx biome ci ./ |
| A | r2 | ['PLAN.md'] | 16 | 20 | Y | True | - |
| B | r1 | ['PLAN.md'] | 26 | 29 | Y | True | - |
| B | r2 | ['PLAN.md'] | 20 | 28 | Y | True | - |
| C | r1 | ['PLAN.md'] | 26 | 28 | Y | True | - |
| C | r2 | ['PLAN.md'] | 18 | 23 | Y | True | - |

### s1b-fa-service — 최종 응답 길이와 출력 토큰 ("간결하게" 없음)

| 조건 | run | 최종 응답 문자 수 | 출력 토큰 | 턴 | check | items.py 직접 DB 호출 수 | items.py 줄 수 |
|---|---|---|---|---|---|---|---|
| A | r1 | 1,068 | 6,826 | 16 | True | 0 | 89 |
| A | r2 | 1,187 | 8,085 | 20 | True | 0 | 89 |
| B | r1 | 987 | 7,934 | 20 | True | 0 | 91 |
| B | r2 | 1,093 | 9,146 | 24 | True | 0 | 87 |
| C | r1 | 2,217 | 7,160 | 24 | True | 0 | 91 |
| C | r2 | 1,625 | 11,073 | 33 | True | 0 | 85 |
- A: 최종 응답 문자 수 중앙 1,128, 출력 토큰 중앙 7,456
- B: 최종 응답 문자 수 중앙 1,040, 출력 토큰 중앙 8,540
- C: 최종 응답 문자 수 중앙 1,921, 출력 토큰 중앙 9,116

### s1b-fa-utils-tests — 커버리지 전/후, 테스트 먼저

app/utils.py 업스트림 커버리지(전체 스위트) 89.06%.

| 조건 | run | 커버리지 후 (전체 스위트) | 새 테스트만 | 새 테스트 파일 | 테스트 편집이 app 편집보다 먼저 | app 수정 여부 | check |
|---|---|---|---|---|---|---|---|
| A | r1 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| A | r2 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| B | r1 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| B | r2 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| C | r1 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| C | r2 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |

### 랜딩 2태스크 — 자동 체크

| 태스크 | 조건 | run | check | 실패 항목 | 라우트 |
|---|---|---|---|---|---|
| s1b-nx-landing | A | r1 | True | - | /landing |
| s1b-nx-landing | A | r2 | True | - | /landing |
| s1b-nx-landing | B | r1 | True | - | /landing |
| s1b-nx-landing | B | r2 | True | - | /landing |
| s1b-nx-landing | C | r1 | True | - | /landing |
| s1b-nx-landing | C | r2 | True | - | /landing |
| s1b-fa-landing | A | r1 | True | - | /welcome |
| s1b-fa-landing | A | r2 | True | - | /welcome |
| s1b-fa-landing | B | r1 | True | - | /welcome |
| s1b-fa-landing | B | r2 | True | - | /welcome |
| s1b-fa-landing | C | r1 | False | frontend: bunx biome ci ./ | /welcome |
| s1b-fa-landing | C | r2 | True | - | /welcome |

## 4. 블라인드 판정 (판정자 1명, unblind 후)

| 세트 | 지표 | 조건별 평균 (n) |
|---|---|---|
| plans A+B+C | 검증 방법 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| plans A+B+C | 단계 구체성 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| plans A+B+C | 리스크 1-5 | A 3.00 (2), B 4.00 (2), C 2.00 (2) |
| plans A+B+C | 순서 1-5 | A 4.50 (2), B 5.00 (2), C 5.00 (2) |
| plans A+B+C | 순위 | A 2.50 (2), B 1.00 (2), C 5.00 (2) |
| plans A+B+C | 정규화 순위 | A 0.30 (2), B 0.00 (2), C 0.80 (2) |
| plans A+B+C | 파일 명시 1-5 | A 5.00 (2), B 5.00 (2), C 5.00 (2) |
| plans A+B+C | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.00 (2) |
| screens A+B+C | (a) AI느낌 수 | A 1.75 (4), B 0.50 (4), C 2.00 (4) |
| screens A+B+C | (b) 쓸만함 1-5 | A 3.50 (4), B 5.00 (4), C 3.75 (4) |
| screens A+B+C | 순위 | A 4.00 (4), B 1.00 (4), C 4.25 (4) |
| screens A+B+C | 정규화 순위 | A 0.60 (4), B 0.00 (4), C 0.65 (4) |

세트별 코드·조건·점수와 판정 근거: `blind-ranking-results.md`, `blind-ranking.md`. 랜딩 두 세트는 순위·점수를 함께 `screens` 묶음으로 집계(n=4/조건).

## 5. 세션별 전체

| 태스크 | 조건 | run | subtype | 턴 | 입력 토큰 | 출력 토큰 | 시간 s | diff 파일 수 | check |
|---|---|---|---|---|---|---|---|---|---|
| s1b-nx-landing | A | r1 | success | 24 | 1,934,933 | 30,795 | 300 | 4 | True |
| s1b-nx-landing | A | r2 | success | 26 | 2,146,073 | 20,344 | 210 | 4 | True |
| s1b-nx-landing | B | r1 | success | 34 | 2,727,738 | 22,464 | 453 | 4 | True |
| s1b-nx-landing | B | r2 | success | 24 | 1,865,982 | 23,664 | 335 | 5 | True |
| s1b-nx-landing | C | r1 | success | 33 | 2,609,800 | 21,059 | 243 | 5 | True |
| s1b-nx-landing | C | r2 | success | 41 | 3,108,746 | 24,728 | 254 | 5 | True |
| s1b-fa-landing | A | r1 | success | 18 | 1,456,536 | 9,074 | 126 | 4 | True |
| s1b-fa-landing | A | r2 | success | 19 | 1,353,580 | 8,459 | 108 | 5 | True |
| s1b-fa-landing | B | r1 | success | 30 | 2,408,147 | 18,081 | 211 | 3 | True |
| s1b-fa-landing | B | r2 | success | 18 | 1,516,485 | 12,915 | 146 | 7 | True |
| s1b-fa-landing | C | r1 | success | 41 | 2,726,748 | 12,772 | 149 | 5 | False |
| s1b-fa-landing | C | r2 | success | 35 | 2,690,923 | 16,047 | 191 | 6 | True |
| s1b-fa-tags-plan | A | r1 | error_max_turns | 41 | 4,915,548 | 30,506 | 315 | 15 | False |
| s1b-fa-tags-plan | A | r2 | error_max_turns | 41 | 5,027,179 | 33,388 | 419 | 20 | True |
| s1b-fa-tags-plan | B | r1 | error_max_turns (+2 follow-up) | 42 | 5,876,277 | 46,698 | 1,011 | 14 | True |
| s1b-fa-tags-plan | B | r2 | error_max_turns (+2 follow-up) | 54 | 7,649,643 | 50,097 | 514 | 20 | True |
| s1b-fa-tags-plan | C | r1 | error_max_turns | 41 | 5,079,843 | 28,647 | 338 | 11 | True |
| s1b-fa-tags-plan | C | r2 | error_max_turns | 41 | 5,245,387 | 32,456 | 330 | 18 | True |
| s1b-fa-service | A | r1 | success | 16 | 1,085,625 | 6,826 | 85 | 4 | True |
| s1b-fa-service | A | r2 | success | 20 | 1,311,735 | 8,085 | 93 | 4 | True |
| s1b-fa-service | B | r1 | success | 20 | 1,642,837 | 7,934 | 103 | 4 | True |
| s1b-fa-service | B | r2 | success | 24 | 1,507,459 | 9,146 | 117 | 8 | True |
| s1b-fa-service | C | r1 | success | 24 | 1,837,016 | 7,160 | 96 | 7 | True |
| s1b-fa-service | C | r2 | success | 33 | 2,792,462 | 11,073 | 161 | 6 | True |
| s1b-fa-utils-tests | A | r1 | success | 14 | 879,905 | 6,232 | 83 | 3 | True |
| s1b-fa-utils-tests | A | r2 | success | 12 | 1,061,824 | 8,170 | 107 | 2 | True |
| s1b-fa-utils-tests | B | r1 | success | 13 | 957,816 | 8,032 | 87 | 2 | True |
| s1b-fa-utils-tests | B | r2 | success | 20 | 1,359,181 | 10,678 | 118 | 2 | True |
| s1b-fa-utils-tests | C | r1 | success | 22 | 1,660,949 | 8,833 | 140 | 2 | True |
| s1b-fa-utils-tests | C | r2 | success | 18 | 1,426,258 | 7,740 | 103 | 4 | True |
