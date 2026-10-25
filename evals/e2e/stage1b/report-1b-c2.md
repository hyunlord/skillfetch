# skillfetch 1b — A / B / 기존 C / 새 C (C2, search k=50) (report)

C2 실행 2026-10-22 KST 22:54–23:05, 10세션 (5태스크 × C2 × 2회), 고정 시드 큐 `runs/_queue_c2.txt`, 동시 4. A·B·C는 1b 첫 실행(20:59–21:31) 그대로. 숫자는 `scripts/report_s1b.py`(`report(..., conds=ABC+C2)`), 블라인드는 `rejudge/`.

## 0. 설정

| 항목 | 값 |
|---|---|
| C2 | C와 같은 하네스·태스크·체크·`--max-turns 40`. 차이: 라우터 SKILL.md와 MCP 서버가 skillfetch `main@e2a1b65`(PR #23: search_skills 기본 k=50, 압축 결과 `{id, title, 한 줄 summary, tier, token_estimate}`, 라우터 4단계 "50개 한 줄 요약을 모두 읽고 1–3개"). 레포 브랜치 `s1b-c2`(fastapi `aa3241d`, nextjs `3212825`) = `s1-c` + SKILL.md 교체(5줄 diff) |
| 서버 버전 | `.mcp.json`은 C와 동일(`uvx --from git+https://github.com/hyunlord/skillfetch`). 실행 전 `uvx --refresh`로 캐시 갱신, `--refresh` 없는 uvx에서 `DEFAULT_K == 50` 확인. 원격 HEAD 실행 전후 `e2a1b65` |
| 인덱스 | `built_at` 2026-10-22T06:15:43Z — A/B/C와 같음 |
| 체크 | 1b 동결 체크 그대로(`checks/FROZEN.sha256`) |
| 블라인드 | 새 세트 `rejudge/`: 랜딩 2태스크 각 8세트(A·B·C·C2 × 2, 데스크톱+375px), 플랜 8세트(PLAN.md + impl.diff, 1b와 같은 redaction, 6회). 새 무작위 코드, 키 `rejudge/*-key.jsonl` |

### 기록 사항

- **판정자: 정답·조건 비공개 하위 에이전트 3개**(같은 모델; 랜딩 nx·랜딩 fa·플랜 각 1). 이 세션은 1b 첫 판정 뒤 A/B/C 매핑을 unblind해 알고 있어 같은 세트를 다시 판정하면 블라인드가 아니다. 그래서 A/B/C/C2 전부를 새 코드로 섞어 하위 에이전트가 같은 루브릭(`rubric.md` = 1b 판정 기준 번역)으로 판정했다. 하위 에이전트에게는 루브릭과 해당 세트 폴더만 줬다(키·runs·다른 폴더 열지 말 것). 1b 첫 판정(이 세션, A/B/C만)은 참고로 나란히 둔다 — 판정자가 달라 두 판정의 점수를 직접 비교하지 않는다.
- **이 세션이 판정 전에 본 것**: 실행 중 C2 세션 4개의 skillfetch 호출 목록(로드한 스킬)을 확인했다. 판정은 하위 에이전트가 했고 이 세션은 판정에 관여하지 않았다.
- **체크 실패 2건(C2)**: s1b-fa-tags-plan r2 — 세션이 고친 `frontend/src/components/Items/columns.tsx`, `src/routes/_layout/items.tsx`가 biome 포맷 불일치(세션은 40턴 한도 도달). s1b-fa-landing r2 — 세션이 실행한 Playwright가 남긴 `frontend/test-results/.last-run.json`이 biome 포맷 검사에 걸림(기존 C r1과 같은 원인).
- **C2 s1b-fa-tags-plan r2**: `resolve_set`에 넣은 `uasl/fastapi-endpoint`가 로컬 fastapi·sqlmodel 핀과 합쳐 8000토큰을 넘어 `load_skills`에서 빠짐(errors에 기록).
- s1b-fa-tags-plan은 C2 2세션도 `--max-turns 40`에 도달.

## 1. 조건별 집계

| 태스크 | 조건 | check pass | 중앙 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 시간 s | error_max_turns |
|---|---|---|---|---|---|---|---|
| s1b-nx-landing | A | 2/2 | 25 | 2,040,503 | 25,569.5 | 254.9 | 0 |
| s1b-nx-landing | B | 2/2 | 29 | 2,296,860 | 23,064 | 394.1 | 0 |
| s1b-nx-landing | C | 2/2 | 37 | 2,859,273 | 22,893.5 | 248.5 | 0 |
| s1b-nx-landing | C2 | 2/2 | 28 | 2,266,572.5 | 23,986 | 257.7 | 0 |
| s1b-fa-landing | A | 2/2 | 18.5 | 1,405,058 | 8,766.5 | 116.9 | 0 |
| s1b-fa-landing | B | 2/2 | 24 | 1,962,316 | 15,498 | 178.6 | 0 |
| s1b-fa-landing | C | 1/2 | 38 | 2,708,835.5 | 14,409.5 | 170.0 | 0 |
| s1b-fa-landing | C2 | 1/2 | 29 | 2,295,534 | 13,620 | 192.6 | 0 |
| s1b-fa-tags-plan | A | 1/2 | 41 | 4,971,363.5 | 31,947 | 367.2 | 2 |
| s1b-fa-tags-plan | B | 2/2 | 48 | 6,762,960 | 48,397.5 | 762.8 | 2 |
| s1b-fa-tags-plan | C | 2/2 | 41 | 5,162,615 | 30,551.5 | 334.2 | 2 |
| s1b-fa-tags-plan | C2 | 1/2 | 41 | 5,074,516.5 | 32,020.5 | 323.6 | 2 |
| s1b-fa-service | A | 2/2 | 18 | 1,198,680 | 7,455.5 | 89.1 | 0 |
| s1b-fa-service | B | 2/2 | 22 | 1,575,148 | 8,540 | 109.9 | 0 |
| s1b-fa-service | C | 2/2 | 28.5 | 2,314,739 | 9,116.5 | 128.4 | 0 |
| s1b-fa-service | C2 | 2/2 | 23 | 1,814,853 | 7,280.5 | 102.4 | 0 |
| s1b-fa-utils-tests | A | 2/2 | 13 | 970,864.5 | 7,201 | 95.0 | 0 |
| s1b-fa-utils-tests | B | 2/2 | 16.5 | 1,158,498.5 | 9,355 | 102.4 | 0 |
| s1b-fa-utils-tests | C | 2/2 | 20 | 1,543,603.5 | 8,286.5 | 121.8 | 0 |
| s1b-fa-utils-tests | C2 | 2/2 | 23.5 | 1,945,906 | 9,779 | 116.4 | 0 |

- A 전체: check pass 9/10, 중앙 턴 19.5, 중앙 입력 1,405,058, 중앙 출력 8,766.5
- B 전체: check pass 10/10, 중앙 턴 24, 중앙 입력 1,754,409.5, 중앙 출력 15,498
- C 전체: check pass 9/10, 중앙 턴 34, 중앙 입력 2,708,835.5, 중앙 출력 14,409.5
- C2 전체: check pass 8/10, 중앙 턴 26.5, 중앙 입력 2,153,239.5, 중앙 출력 13,620

## 2. C: 전문가 스킬의 search 순위, 실제 로드

순위 = 세션이 받은 search_skills 결과 목록 안의 순위(C는 k=10, C2는 기본 k=50). 결과 크기 = 도구 결과 문자 수 / 4.

| 태스크 | 조건 | run | search | query | k / 받은 수 / 결과 크기 | 전문가 스킬 순위 | 로드한 스킬 | load 토큰 | MCP ready s | 첫 skillfetch 호출 s |
|---|---|---|---|---|---|---|---|---|---|---|
| s1b-nx-landing | C | r1 | Y (search+resolve+load) | Build a new product landing page at the /landing route in a Next.js TypeScript app with hero, three feature sections, pricing, and call-to-action | default / 10 / 2,290.8 | `anthropics-skills/frontend-design` 없음 | `uasl/taste-skill`, `uasl/next-best-practices` | 6,162 | 3.2 | 14.1 |
| s1b-nx-landing | C | r2 | Y (search+resolve+load) | Build a new product landing page at the /landing route in a Next.js TypeScript pages-router app with hero, three feature cards, pricing section and call-to-action | default / 10 / 2,302.8 | `anthropics-skills/frontend-design` 없음 | `uasl/next-best-practices`, `uasl/taste-skill` | 6,162 | 2.8 | 11.2 |
| s1b-nx-landing | C2 | r1 | Y (search+resolve+load) | Build a new product landing page route /landing in a Next.js TypeScript React app with hero section, three feature cards, pricing section and call-to-action | default / 50 / 3,145.5 | `anthropics-skills/frontend-design` #47 | `anthropics-skills/frontend-design`, `uasl/next-best-practices` | 3,210 | 2.5 | 9.5 |
| s1b-nx-landing | C2 | r2 | Y (search+resolve+load) | Build a new product landing page route /landing in a Next.js TypeScript app with a hero section, three feature cards, a pricing section, and a call-to-action | default / 50 / 3,151.8 | `anthropics-skills/frontend-design` #41 | `anthropics-skills/frontend-design`, `uasl/next-best-practices`, `uasl/copywriting` | 6,372 | 4.7 | 10.8 |
| s1b-fa-landing | C | r1 | Y (search+resolve+load) | Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards, and a call-to-action, served by a FastAPI app | default / 10 / 2,175.2 | `anthropics-skills/frontend-design` 없음 | `fastapi(local)`, `uasl/landing-page`, `uasl/copywriting` | 7,045 | 3.8 | 10.4 |
| s1b-fa-landing | C | r2 | Y (search+resolve+load) | Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards and a call-to-action in this repo's frontend | default / 10 / 2,175.5 | `anthropics-skills/frontend-design` 없음 | `uasl/frontend-design`, `uasl/copywriting` | 4,151 | 4.0 | 10.7 |
| s1b-fa-landing | C2 | r1 | Y (search+resolve+load) | Build a new public pre-login marketing landing page route in the React TypeScript frontend (frontend/src/routes/) with a hero section, three feature cards, and a call-to-action | default / 50 / 3,224.2 | `anthropics-skills/frontend-design` #16 | `anthropics-skills/frontend-design`, `uasl/artisan` | 5,095 | 2.4 | 20.0 |
| s1b-fa-landing | C2 | r2 | Y (search+resolve+load) | Build a new pre-login marketing landing page route from scratch with a hero section, three feature cards, and a call-to-action in the project's frontend | default / 50 / 3,235.5 | `anthropics-skills/frontend-design` #13 | `anthropics-skills/frontend-design`, `uasl/responsive-design` | 5,300 | 3.2 | 9.8 |
| s1b-fa-tags-plan | C | r1 | Y (search+resolve+load) | Add a tags feature to items in a FastAPI + SQLModel full-stack app: write a PLAN.md, then add a Tag model with many-to-many link to Item, an Alembic migration, REST API endpoints, and React frontend UI | default / 10 / 2,147.8 | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)`, `uasl/api-design` | 7,669 | 3.4 | 12.9 |
| s1b-fa-tags-plan | C | r2 | Y (search+resolve+load) | Add a tags feature to items in a FastAPI + SQLModel backend with Alembic migration, REST API endpoints, and a React TypeScript frontend, writing a PLAN.md implementation plan first | default / 10 / 2,193.5 | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)`, `uasl/fastapi-endpoint` | 8,215 | 2.8 | 10.7 |
| s1b-fa-tags-plan | C2 | r1 | Y (search+resolve+load) | Add a tags feature to items in a full-stack FastAPI + SQLModel + Alembic backend and React TypeScript frontend: write PLAN.md first, then implement model, migration, API endpoints, and frontend UI | default / 50 / 3,229 | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)` | 4,451 | 3.1 | 10.4 |
| s1b-fa-tags-plan | C2 | r2 | Y (search+resolve+load) | Add a tags feature to items in a full-stack FastAPI + SQLModel + Alembic backend and React/TypeScript frontend: model, migration, API endpoints, and frontend UI, writing PLAN.md first | default / 50 / 3,205.2 | `uasl/writing-plans` 없음 | `fastapi(local)`, `sqlmodel(local)` | 4,451 | 3.4 | 10.3 |
| s1b-fa-service | C | r1 | Y (search+resolve+load) | Refactor the FastAPI items router by extracting its business logic into a separate service layer module | default / 10 / 1,922.5 | `uasl/caveman` 없음 | `fastapi(local)`, `uasl/fastapi-templates` | 6,133 | 4.5 | 10.7 |
| s1b-fa-service | C | r2 | Y (search+resolve+load) | Refactor the FastAPI items router by extracting its business logic into a separate service layer module in Python | default / 10 / 1,990.2 | `uasl/caveman` 없음 | `uasl/fastapi-templates`, `uasl/python-design-patterns` | 6,698 | 2.4 | 9.4 |
| s1b-fa-service | C2 | r1 | Y (search+resolve+load) | Refactor the FastAPI items router to move its business logic into a separate service layer module | default / 50 / 3,173 | `uasl/caveman` 없음 | `uasl/fastapi-templates`, `uasl/python-design-patterns` | 6,698 | 3.7 | 15.2 |
| s1b-fa-service | C2 | r2 | Y (search+resolve+load) | Refactor the FastAPI items router by extracting its business logic into a separate service layer module in Python | default / 50 / 3,208.2 | `uasl/caveman` 없음 | `fastapi(local)`, `uasl/fastapi-templates` | 6,133 | 2.5 | 10.1 |
| s1b-fa-utils-tests | C | r1 | Y (search+resolve+load) | Add pytest unit tests for the Python FastAPI backend utility module backend/app/utils.py | default / 10 / 2,064.2 | `uasl/tdd` 없음 | `uasl/python-testing-patterns` | 6,213 | 3.5 | 19.3 |
| s1b-fa-utils-tests | C | r2 | Y (search+resolve+load) | Add pytest unit tests for the FastAPI backend helper module backend/app/utils.py in backend/tests/ | default / 10 / 1,993.8 | `uasl/tdd` 없음 | `uasl/python-testing-patterns` | 6,213 | 3.1 | 14.5 |
| s1b-fa-utils-tests | C2 | r1 | Y (search+resolve+load) | Add pytest unit tests for the Python FastAPI backend utility module backend/app/utils.py (email sending, token generation and verification helpers) | default / 50 / 3,204.5 | `uasl/tdd` 없음 | `uasl/python-testing-patterns` | 6,213 | 2.7 | 9.5 |
| s1b-fa-utils-tests | C2 | r2 | Y (search+resolve+load) | Add pytest unit tests for the FastAPI backend helper functions in backend/app/utils.py | default / 50 / 3,159.5 | `uasl/tdd` #44 | `uasl/python-testing-patterns` | 6,213 | 3.6 | 11.4 |

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
| C2 | r1 | ['PLAN.md'] | 24 | 27 | Y | True | - |
| C2 | r2 | ['PLAN.md'] | 16 | 19 | Y | False | frontend: bunx biome ci ./ |

### s1b-fa-service — 최종 응답 길이와 출력 토큰 ("간결하게" 없음)

| 조건 | run | 최종 응답 문자 수 | 출력 토큰 | 턴 | check | items.py 직접 DB 호출 수 | items.py 줄 수 |
|---|---|---|---|---|---|---|---|
| A | r1 | 1,068 | 6,826 | 16 | True | 0 | 89 |
| A | r2 | 1,187 | 8,085 | 20 | True | 0 | 89 |
| B | r1 | 987 | 7,934 | 20 | True | 0 | 91 |
| B | r2 | 1,093 | 9,146 | 24 | True | 0 | 87 |
| C | r1 | 2,217 | 7,160 | 24 | True | 0 | 91 |
| C | r2 | 1,625 | 11,073 | 33 | True | 0 | 85 |
| C2 | r1 | 1,438 | 7,669 | 27 | True | 0 | 87 |
| C2 | r2 | 1,175 | 6,892 | 19 | True | 0 | 91 |
- A: 최종 응답 문자 수 중앙 1,127.5, 출력 토큰 중앙 7,455.5
- B: 최종 응답 문자 수 중앙 1,040, 출력 토큰 중앙 8,540
- C: 최종 응답 문자 수 중앙 1,921, 출력 토큰 중앙 9,116.5
- C2: 최종 응답 문자 수 중앙 1,306.5, 출력 토큰 중앙 7,280.5

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
| C2 | r1 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |
| C2 | r2 | 100.0% | 100.0% | ['backend/tests/test_utils.py'] | Y | N | True |

### 랜딩 2태스크 — 자동 체크

| 태스크 | 조건 | run | check | 실패 항목 | 라우트 |
|---|---|---|---|---|---|
| s1b-nx-landing | A | r1 | True | - | /landing |
| s1b-nx-landing | A | r2 | True | - | /landing |
| s1b-nx-landing | B | r1 | True | - | /landing |
| s1b-nx-landing | B | r2 | True | - | /landing |
| s1b-nx-landing | C | r1 | True | - | /landing |
| s1b-nx-landing | C | r2 | True | - | /landing |
| s1b-nx-landing | C2 | r1 | True | - | /landing |
| s1b-nx-landing | C2 | r2 | True | - | /landing |
| s1b-fa-landing | A | r1 | True | - | /welcome |
| s1b-fa-landing | A | r2 | True | - | /welcome |
| s1b-fa-landing | B | r1 | True | - | /welcome |
| s1b-fa-landing | B | r2 | True | - | /welcome |
| s1b-fa-landing | C | r1 | False | frontend: bunx biome ci ./ | /welcome |
| s1b-fa-landing | C | r2 | True | - | /welcome |
| s1b-fa-landing | C2 | r1 | True | - | /welcome |
| s1b-fa-landing | C2 | r2 | False | frontend: bunx biome ci ./ | /welcome |

## 4. 블라인드 재판정 A/B/C/C2 (판정자: 정답·조건 비공개 하위 에이전트, unblind 후)

| 세트 | 지표 | 조건별 평균 (n) |
|---|---|---|
| plans A+B+C+C2 | 검증 방법 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| plans A+B+C+C2 | 단계 구체성 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| plans A+B+C+C2 | 리스크 1-5 | A 2.50 (2), B 4.00 (2), C 2.00 (2), C2 2.00 (2) |
| plans A+B+C+C2 | 순서 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| plans A+B+C+C2 | 순위 | A 3.50 (2), B 1.00 (2), C 6.50 (2), C2 6.00 (2) |
| plans A+B+C+C2 | 정규화 순위 | A 0.36 (2), B 0.00 (2), C 0.79 (2), C2 0.71 (2) |
| plans A+B+C+C2 | 파일 명시 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| plans A+B+C+C2 | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.50 (2), C2 4.00 (2) |
| screens A+B+C+C2 | (a) AI느낌 수 | A 2.00 (4), B 0.50 (4), C 2.00 (4), C2 0.50 (4) |
| screens A+B+C+C2 | (b) 쓸만함 1-5 | A 3.50 (4), B 4.75 (4), C 4.50 (4), C2 4.75 (4) |
| screens A+B+C+C2 | 순위 | A 6.50 (4), B 1.75 (4), C 5.00 (4), C2 1.75 (4) |
| screens A+B+C+C2 | 정규화 순위 | A 0.79 (4), B 0.11 (4), C 0.57 (4), C2 0.11 (4) |

세트별 코드·조건·점수와 판정 근거: `rejudge/blind-ranking-results.md`, `rejudge/blind-ranking.md`. 랜딩 두 세트(각 8개)는 순위·점수를 함께 `screens` 묶음으로 집계(n=4/조건). 플랜 세트는 8개.

### 4a. 랜딩 태스크별 (새 판정, 조건별 평균, n=2)

| 태스크 | 지표 | A | B | C | C2 |
|---|---|---|---|---|---|
| s1b-nx-landing | (a) AI느낌 수 | 1.00 | 0.00 | 1.50 | 0.00 |
| s1b-nx-landing | (b) 쓸만함 1-5 | 4.00 | 4.50 | 4.50 | 4.50 |
| s1b-nx-landing | 순위 (1=최상, 8개 중) | 6.00 | 2.50 | 4.50 | 2.50 |
| s1b-fa-landing | (a) AI느낌 수 | 3.00 | 1.00 | 2.50 | 1.00 |
| s1b-fa-landing | (b) 쓸만함 1-5 | 3.00 | 5.00 | 4.50 | 5.00 |
| s1b-fa-landing | 순위 (1=최상, 8개 중) | 7.00 | 1.00 | 5.50 | 1.00 |

### 4b. 참고: 1b 첫 판정 (판정자 = 이 세션, A/B/C만, `blind-ranking-results.md`)

판정자가 달라 4의 점수와 직접 비교하지 않는다.

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

## 5. 세션별 전체

| 태스크 | 조건 | run | subtype | 턴 | 입력 토큰 | 출력 토큰 | 시간 s | diff 파일 수 | check |
|---|---|---|---|---|---|---|---|---|---|
| s1b-nx-landing | A | r1 | success | 24 | 1,934,933 | 30,795 | 299.7 | 4 | True |
| s1b-nx-landing | A | r2 | success | 26 | 2,146,073 | 20,344 | 210.1 | 4 | True |
| s1b-nx-landing | B | r1 | success | 34 | 2,727,738 | 22,464 | 452.9 | 4 | True |
| s1b-nx-landing | B | r2 | success | 24 | 1,865,982 | 23,664 | 335.2 | 5 | True |
| s1b-nx-landing | C | r1 | success | 33 | 2,609,800 | 21,059 | 243.1 | 5 | True |
| s1b-nx-landing | C | r2 | success | 41 | 3,108,746 | 24,728 | 253.9 | 5 | True |
| s1b-nx-landing | C2 | r1 | success | 26 | 1,968,666 | 20,540 | 214.3 | 6 | True |
| s1b-nx-landing | C2 | r2 | success | 30 | 2,564,479 | 27,432 | 301.2 | 6 | True |
| s1b-fa-landing | A | r1 | success | 18 | 1,456,536 | 9,074 | 126.2 | 4 | True |
| s1b-fa-landing | A | r2 | success | 19 | 1,353,580 | 8,459 | 107.6 | 5 | True |
| s1b-fa-landing | B | r1 | success | 30 | 2,408,147 | 18,081 | 210.8 | 3 | True |
| s1b-fa-landing | B | r2 | success | 18 | 1,516,485 | 12,915 | 146.4 | 7 | True |
| s1b-fa-landing | C | r1 | success | 41 | 2,726,748 | 12,772 | 148.9 | 5 | False |
| s1b-fa-landing | C | r2 | success | 35 | 2,690,923 | 16,047 | 191.2 | 6 | True |
| s1b-fa-landing | C2 | r1 | success | 33 | 2,461,500 | 14,290 | 226.5 | 6 | True |
| s1b-fa-landing | C2 | r2 | success | 25 | 2,129,568 | 12,950 | 158.8 | 6 | False |
| s1b-fa-tags-plan | A | r1 | error_max_turns | 41 | 4,915,548 | 30,506 | 315.5 | 15 | False |
| s1b-fa-tags-plan | A | r2 | error_max_turns | 41 | 5,027,179 | 33,388 | 419.0 | 20 | True |
| s1b-fa-tags-plan | B | r1 | error_max_turns (+2 follow-up) | 42 | 5,876,277 | 46,698 | 1,011.1 | 14 | True |
| s1b-fa-tags-plan | B | r2 | error_max_turns (+2 follow-up) | 54 | 7,649,643 | 50,097 | 514.4 | 20 | True |
| s1b-fa-tags-plan | C | r1 | error_max_turns | 41 | 5,079,843 | 28,647 | 338.1 | 11 | True |
| s1b-fa-tags-plan | C | r2 | error_max_turns | 41 | 5,245,387 | 32,456 | 330.4 | 18 | True |
| s1b-fa-tags-plan | C2 | r1 | error_max_turns | 41 | 5,212,016 | 34,889 | 349.3 | 19 | True |
| s1b-fa-tags-plan | C2 | r2 | error_max_turns | 41 | 4,937,017 | 29,152 | 297.9 | 17 | False |
| s1b-fa-service | A | r1 | success | 16 | 1,085,625 | 6,826 | 84.7 | 4 | True |
| s1b-fa-service | A | r2 | success | 20 | 1,311,735 | 8,085 | 93.4 | 4 | True |
| s1b-fa-service | B | r1 | success | 20 | 1,642,837 | 7,934 | 103.0 | 4 | True |
| s1b-fa-service | B | r2 | success | 24 | 1,507,459 | 9,146 | 116.7 | 8 | True |
| s1b-fa-service | C | r1 | success | 24 | 1,837,016 | 7,160 | 95.8 | 7 | True |
| s1b-fa-service | C | r2 | success | 33 | 2,792,462 | 11,073 | 161.0 | 6 | True |
| s1b-fa-service | C2 | r1 | success | 27 | 2,104,479 | 7,669 | 125.6 | 6 | True |
| s1b-fa-service | C2 | r2 | success | 19 | 1,525,227 | 6,892 | 79.1 | 4 | True |
| s1b-fa-utils-tests | A | r1 | success | 14 | 879,905 | 6,232 | 83.4 | 3 | True |
| s1b-fa-utils-tests | A | r2 | success | 12 | 1,061,824 | 8,170 | 106.6 | 2 | True |
| s1b-fa-utils-tests | B | r1 | success | 13 | 957,816 | 8,032 | 86.7 | 2 | True |
| s1b-fa-utils-tests | B | r2 | success | 20 | 1,359,181 | 10,678 | 118.0 | 2 | True |
| s1b-fa-utils-tests | C | r1 | success | 22 | 1,660,949 | 8,833 | 140.2 | 2 | True |
| s1b-fa-utils-tests | C | r2 | success | 18 | 1,426,258 | 7,740 | 103.4 | 4 | True |
| s1b-fa-utils-tests | C2 | r1 | success | 24 | 1,714,901 | 9,218 | 103.9 | 4 | True |
| s1b-fa-utils-tests | C2 | r2 | success | 23 | 2,176,911 | 10,340 | 128.9 | 4 | True |
