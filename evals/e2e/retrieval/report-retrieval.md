# 검색 수리 — 평가 (세션 실행 없음)

데이터: `retrieval-eval.jsonl` (정답 있음), `retrieval-nogold.jsonl` (정답 없음, 임계값용). 스크립트 `scripts/`. 검색 코드 skillfetch `main@53b81df`(수정 없는 checkout에서 `uv run`), 인덱스 `~/.skillfetch/index` built_at 2026-10-22T06:15:43Z(1단계·1b 세션과 같음). 재실행한 BM25 top-k가 41개 쿼리 모두 세션에 기록된 결과와 일치.

## 평가 세트

- 1단계 C 30 run(전문가 태스크 15개 × 2) + 1b C 10 run = 40 run 중 search_skills를 부른 run은 34개, 쿼리 34개(run당 1회). 부르지 않은 6 run: s1-fa-01-r2, s1-fa-04-r1, s1-fa-04-r2, s1-fa-05-r2, s1-fa-10-r2, s1-nx-10-r2. 그래서 40이 아니라 34.
- 정답 = 그 태스크의 전문가 스킬 id(`tasks-stage1.yaml`, `tasks-1b.yaml`). 정답이 2개인 태스크(s1-fa-08, s1-nx-02)는 둘 중 하나라도 들면 적중. id가 같아야 적중 — 예: `uasl/frontend-design`(별도 id)은 `anthropics-skills/frontend-design` 적중으로 세지 않음.
- 정답 없는 5태스크의 쿼리 7개는 임계값 분석에만 사용.

## 세 방법 비교

| 방법 | 정답 top-1 | 정답 top-3 (b: 고른 1~3개에 포함) | top-10 | top-50 | 비고 |
|---|---|---|---|---|---|
| (a) 현행 BM25 | 5/34 | **7/34 = 0.21** | 17/34 = 0.50 | 24/34 = 0.71 | 랭킹에 아예 없음 2 (caveman 2) |
| (b) BM25 top-50 → 모델이 1~3개 선택 | - | **18/34 = 0.53** | - | - | 정답이 top-50에 있던 24개 중 18개 적중. 쿼리당 1.91개 선택, 빈 선택 0 |
| (c) use_case 태그 필터 → BM25 | 7/34 | **11/34 = 0.32** | 18/34 = 0.53 | - | 필터로 정답이 빠짐 2 |

구현 조건(b 또는 c의 top-3 ≥ 0.7): **미충족** — (b) 0.53, (c) 0.32. (b)의 상한은 정답이 BM25 top-50에 드는 비율 0.71.

### (b) 비용: 쿼리당 요약 50개

- `id — title: summary` 50줄 블록: 토큰(문자/4, skillfetch `token_estimate`와 같은 추정) 최소 3682 · 중앙 3777 · 최대 3890.
- 참고: 현행 search_skills JSON 응답(tags·match_reasons 포함) k=10 중앙 2,257, k=50 중앙 9,909 (최소 8,481, 최대 11,597).

### (c) 태그

- 태그 15개: `use-case-tags.md`. 인덱스의 tier A/B canonical 1489개 모두에 1~3개(1개 1098, 2개 353, 3개 38).
- 분포: other 1081, ui-component 148, planning 121, code-review 77, data-ai 74, devops 67, testing 64, security-review 63, refactor 49, docs 47, debugging 45, landing-page 35, api-endpoint 21, database 18, concise-output 8.
- 쿼리 용례 분포(정답 있는 34 + 없는 7): testing 10, ui-component 7, refactor 7, debugging 4, landing-page 4, api-endpoint 3, database 2, docs 2, planning 2.
- 결과물: `use-cases.json`(스킬 → 태그), `query-use-cases.json`. 인덱스 파일(`~/.skillfetch/index`)에는 쓰지 않았다 — 평가는 사이드카 파일로 필터.

## 임계값: top-1 점수로 '아무것도 로드하지 않음'

search_skills는 점수를 반환하지 않는다. `scripts/scores.py`가 Searcher.search와 같은 계산(BM25 × 프로필 부스트)으로 재계산, top-10이 실제 결과와 같음을 assert.

| 쿼리 | n | top-1 점수 (정렬) |
|---|---|---|
| 정답 있음 | 34 | 32.4, 33.4, 33.8, 38.2, 38.3, 40.6, 42.0, 43.3, 45.3, 46.4, 46.6, 47.9, 50.0, 50.6, 51.3, 53.4, 53.5, 53.7, 54.7, 54.8, 54.8, 55.1, 57.3, 57.3, 57.7, 60.0, 64.3, 65.1, 65.8, 65.8, 68.0, 69.0, 73.8, 74.3 |
| 정답 없음 | 7 | 31.6, 38.6, 38.6, 51.3, 53.3, 53.6, 78.0 |

| 임계값 (top-1 < t면 로드 안 함) | 정답 없는 쿼리 중 로드 안 함 | 정답 있는 쿼리 중 로드 안 함 |
|---|---|---|
| 32.0 | 1/7 | 0/34 |
| 35.0 | 1/7 | 3/34 |
| 38.7 | 3/7 | 5/34 |
| 45.0 | 3/7 | 8/34 |
| 51.3 | 4/7 | 15/34 |
| 53.7 | 6/7 | 17/34 |

- AUC(정답 있음 > 없음): top-1 점수 0.62, top-1/쿼리 토큰 수 0.64, top-1 − top-10 0.71.
- 정답 없는 쿼리의 최고 점수(78.0, s1-nx-05-r2, top-1 vercel-react-best-practices)가 정답 있는 쿼리 34개 전부보다 높다. 정답 있는 쿼리 중 top-1이 정답인 것은 5개.
- 규칙은 라우터에 넣지 않았다(구현 조건 미충족으로 search_skills·라우터 변경 없음).

## 쿼리별

| qid | 정답 | (a) BM25 순위 | (b) 고른 스킬 | (b) | (c) 용례 · 후보 수 | (c) 순위 | top-1 점수 |
|---|---|---|---|---|---|---|---|
| s1-fa-01-r1#1 | uasl/api-design | uasl/api-design 7 | uasl/api-design, uasl/python-testing-patterns | 적중 | api-endpoint · 21 | uasl/api-design 5 | 43.3 |
| s1-fa-02-r1#1 | uasl/postgresql-table-design | uasl/postgresql-table-design 685 | uasl/fastapi-endpoint, uasl/fastapi-templates | - | database · 18 | uasl/postgresql-table-design 14 | 40.6 |
| s1-fa-02-r2#1 | uasl/postgresql-table-design | uasl/postgresql-table-design 495 | uasl/fastapi-templates | - | database · 18 | uasl/postgresql-table-design 13 | 33.4 |
| s1-fa-03-r1#1 | uasl/shadcn | uasl/shadcn 74 | uasl/frontend-patterns | - | ui-component · 148 | uasl/shadcn 51 | 42.0 |
| s1-fa-03-r2#1 | uasl/shadcn | uasl/shadcn 64 | uasl/frontend-patterns | - | ui-component · 148 | uasl/shadcn 38 | 38.2 |
| s1-fa-05-r1#1 | uasl/python-design-patterns | uasl/python-design-patterns 10 | uasl/fastapi-templates, uasl/python-design-patterns | 적중 | refactor · 49 | uasl/python-design-patterns 2 | 38.3 |
| s1-fa-06-r1#1 | uasl/integration-testing | uasl/integration-testing 6 | uasl/python-testing-patterns, uasl/radar | - | testing · 64 | uasl/integration-testing 5 | 53.4 |
| s1-fa-06-r2#1 | uasl/integration-testing | uasl/integration-testing 5 | uasl/python-testing-patterns, uasl/radar, uasl/integration-testing | 적중 | testing · 64 | uasl/integration-testing 5 | 51.3 |
| s1-fa-07-r1#1 | uasl/python-testing-patterns | uasl/python-testing-patterns 7 | uasl/python-testing-patterns, uasl/auth-implementation-patterns | 적중 | testing · 64 | uasl/python-testing-patterns 6 | 64.3 |
| s1-fa-07-r2#1 | uasl/python-testing-patterns | uasl/python-testing-patterns 7 | uasl/python-testing-patterns, uasl/integration-testing | 적중 | testing · 64 | uasl/python-testing-patterns 6 | 69.0 |
| s1-fa-08-r1#1 | uasl/defense-in-depth, uasl/api-design | uasl/defense-in-depth 56, uasl/api-design 5 | uasl/fastapi-endpoint | - | debugging · 45 | uasl/defense-in-depth 7, uasl/api-design - | 32.4 |
| s1-fa-08-r2#1 | uasl/defense-in-depth, uasl/api-design | uasl/defense-in-depth 47, uasl/api-design 8 | uasl/debug-root-cause, uasl/python-testing-patterns | - | debugging · 45 | uasl/defense-in-depth 13, uasl/api-design - | 46.6 |
| s1-fa-10-r1#1 | uasl/quill | uasl/quill 7 | uasl/quill | 적중 | docs · 47 | uasl/quill 2 | 33.8 |
| s1-nx-02-r1#1 | uasl/backend-patterns, uasl/api-design | uasl/backend-patterns 1, uasl/api-design 8 | uasl/api-design, uasl/next-best-practices | 적중 | api-endpoint · 21 | uasl/backend-patterns 1, uasl/api-design 2 | 57.3 |
| s1-nx-02-r2#1 | uasl/backend-patterns, uasl/api-design | uasl/backend-patterns 1, uasl/api-design 8 | uasl/next-best-practices, uasl/api-design | 적중 | api-endpoint · 21 | uasl/backend-patterns 1, uasl/api-design 2 | 57.3 |
| s1-nx-04-r1#1 | uasl/responsive-design | uasl/responsive-design 1 | uasl/responsive-design, uasl/next-best-practices | 적중 | ui-component · 148 | uasl/responsive-design 1 | 65.8 |
| s1-nx-04-r2#1 | uasl/responsive-design | uasl/responsive-design 1 | uasl/responsive-design, uasl/next-best-practices | 적중 | ui-component · 148 | uasl/responsive-design 1 | 65.8 |
| s1-nx-06-r1#1 | uasl/refactoring-patterns | uasl/refactoring-patterns 153 | uasl/zen, uasl/software-design-philosophy | - | refactor · 49 | uasl/refactoring-patterns 24 | 54.8 |
| s1-nx-06-r2#1 | uasl/refactoring-patterns | uasl/refactoring-patterns 81 | uasl/zen, uasl/next-best-practices | - | refactor · 49 | uasl/refactoring-patterns 17 | 54.8 |
| s1-nx-07-r1#1 | uasl/tdd-workflow | uasl/tdd-workflow 13 | uasl/unit-testing, uasl/documentation-lookup | - | testing · 64 | uasl/tdd-workflow 2 | 68.0 |
| s1-nx-07-r2#1 | uasl/tdd-workflow | uasl/tdd-workflow 9 | uasl/unit-testing | - | testing · 64 | uasl/tdd-workflow 2 | 65.1 |
| s1-nx-08-r1#1 | uasl/unit-testing | uasl/unit-testing 1 | uasl/unit-testing, uasl/typescript-unit-testing | 적중 | testing · 64 | uasl/unit-testing 1 | 57.7 |
| s1-nx-08-r2#1 | uasl/unit-testing | uasl/unit-testing 3 | uasl/unit-testing, uasl/radar | 적중 | testing · 64 | uasl/unit-testing 1 | 50.6 |
| s1-nx-10-r1#1 | uasl/quill | uasl/quill 3 | uasl/quill | 적중 | docs · 47 | uasl/quill 1 | 74.3 |
| s1b-fa-landing-r1#1 | anthropics-skills/frontend-design | anthropics-skills/frontend-design 24 | anthropics-skills/frontend-design, uasl/copywriting | 적중 | landing-page · 35 | anthropics-skills/frontend-design 19 | 45.3 |
| s1b-fa-landing-r2#1 | anthropics-skills/frontend-design | anthropics-skills/frontend-design 13 | anthropics-skills/frontend-design, uasl/copywriting | 적중 | landing-page · 35 | anthropics-skills/frontend-design 12 | 54.7 |
| s1b-fa-service-r1#1 | uasl/caveman | uasl/caveman - | uasl/fastapi-templates, uasl/python-design-patterns, uasl/refactoring-patterns | - | refactor · 49 | uasl/caveman - | 46.4 |
| s1b-fa-service-r2#1 | uasl/caveman | uasl/caveman - | uasl/python-design-patterns, uasl/refactoring-patterns, uasl/fastapi-templates | - | refactor · 49 | uasl/caveman - | 53.5 |
| s1b-fa-tags-plan-r1#1 | uasl/writing-plans | uasl/writing-plans 93 | uasl/api-design, uasl/fastapi-endpoint | - | planning · 121 | uasl/writing-plans 18 | 47.9 |
| s1b-fa-tags-plan-r2#1 | uasl/writing-plans | uasl/writing-plans 29 | uasl/writing-plans, uasl/fastapi-endpoint | 적중 | planning · 121 | uasl/writing-plans 4 | 53.7 |
| s1b-fa-utils-tests-r1#1 | uasl/tdd | uasl/tdd 59 | uasl/python-testing-patterns, uasl/radar | - | testing · 64 | uasl/tdd 23 | 55.1 |
| s1b-fa-utils-tests-r2#1 | uasl/tdd | uasl/tdd 47 | uasl/python-testing-patterns, uasl/unit-testing | - | testing · 64 | uasl/tdd 19 | 50.0 |
| s1b-nx-landing-r1#1 | anthropics-skills/frontend-design | anthropics-skills/frontend-design 39 | anthropics-skills/frontend-design, uasl/copywriting, uasl/next-best-practices | 적중 | landing-page · 35 | anthropics-skills/frontend-design 15 | 60.0 |
| s1b-nx-landing-r2#1 | anthropics-skills/frontend-design | anthropics-skills/frontend-design 41 | anthropics-skills/frontend-design, uasl/copywriting | 적중 | landing-page · 35 | anthropics-skills/frontend-design 16 | 73.8 |

## 진행 방식과 공개 사항

- (b)의 선택, (c)의 스킬 태그·쿼리 용례는 이 세션이 아니라 **정답을 모르는 하위 에이전트**(같은 모델, Opus 5.5)가 했다. 이 세션은 정답(전문가 스킬)을 알고 있어서 직접 하면 결과가 정답 쪽으로 기운다. 하위 에이전트에게는 입력 파일만 줬다(정답·조건·실험 목적 없음, 다른 파일 열지 말 것). 입력: (b) 저장소 설명 + 사용자 태스크 원문 + 보낸 쿼리 + top-50(id·title·summary, 순위순), 4묶음. (c) 태그 정의 + 스킬별 id·title·summary·keywords, 4묶음; 쿼리 용례는 태그 정의 + 태스크 원문 + 쿼리.
- 판정자 대신 하위 에이전트를 쓴 것은 지시("네가")와 다르다.
- (b)는 정답이 없는 7개 쿼리에 대해서는 돌리지 않았다.
- 같은 쿼리의 run 2개는 쿼리 문장이 비슷해 독립 표본이 아니다(태스크 기준으로는 정답 있는 태스크 20개).
- 1단계·1b 보고서의 '중앙 턴'은 반올림 값이었다(1단계 A 14 → 실제 14.5, 1b A 20 → 19.5). numbers.md §11은 실제 값.
