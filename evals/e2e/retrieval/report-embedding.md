# 임베딩 오프라인 평가 (세션 아님, 런타임 코드 변경 없음)

34쿼리(`retrieval-eval.jsonl`), 정답 = 전문가 스킬 id. 스크립트 `scripts/eval_embed.py`, `scripts/report_embed.py`.

| 방법 | top-3 | top-10 | top-50 |
|---|---|---|---|
| (a) BM25 (현행 순위) | 7/34 = 0.21 | 17/34 = 0.50 | 24/34 = 0.71 |
| (i) 임베딩 단독 | 11/34 = 0.32 | 16/34 = 0.47 | 20/34 = 0.59 |
| (ii) BM25 + 임베딩 RRF (k=60) | 9/34 = 0.26 | 16/34 = 0.47 | 25/34 = 0.74 |
| (b) BM25 top-50 → 1~3개 선택 | 18/34 = 0.53 | - | - |
| (ii) RRF top-50 → 1~3개 선택 | 18/34 = 0.53 | - | - |

선택 행의 top-3 = 하위 에이전트(정답 비공개, 같은 프롬프트·형식)가 고른 1~3개에 정답 포함.

## 비용

| 항목 | 값 |
|---|---|
| 모델 | `sentence-transformers/all-MiniLM-L6-v2`, 파라미터 22,713,216, 차원 384, max_seq_length 256 |
| 모델 크기 (HF 캐시) | 91.6 MB |
| 임베딩 저장 (float32, 1489×384) | 2.29 MB |
| 인덱싱 시간 (1489개 인코딩, CPU 14코어, batch 64) | 5.09 s |
| 모델 로드 (import 포함) | 3.68 s |
| 쿼리 지연 (인코딩 + 코사인 1489개) | 중앙 4.6 ms, 최대 6.0 ms |
| 256 토큰 넘어 잘린 문서 | 208/1489 |
| 런타임 의존성 | sentence-transformers + torch (스크래치 venv에 설치; skillfetch 의존성 아님) |

## 쿼리별 정답 순위

| qid | 정답 | BM25 | 임베딩 | RRF | (b) 선택 | RRF 선택 |
|---|---|---|---|---|---|---|
| s1-fa-01-r1#1 | uasl/api-design | 7 | 1 | 3 | 적중 | 적중 |
| s1-fa-02-r1#1 | uasl/postgresql-table-design | 685 | 357 | 596 | uasl/fastapi-endpoint, uasl/fastapi-templates | uasl/schema, uasl/fastapi-endpoint |
| s1-fa-02-r2#1 | uasl/postgresql-table-design | 495 | 278 | 396 | uasl/fastapi-templates | uasl/schema, uasl/fastapi-endpoint |
| s1-fa-03-r1#1 | uasl/shadcn | 74 | 165 | 92 | uasl/frontend-patterns | uasl/frontend-patterns, uasl/shadcn-ui |
| s1-fa-03-r2#1 | uasl/shadcn | 64 | 179 | 87 | uasl/frontend-patterns | uasl/frontend-patterns, uasl/shadcn-ui |
| s1-fa-05-r1#1 | uasl/python-design-patterns | 10 | 184 | 8 | 적중 | 적중 |
| s1-fa-06-r1#1 | uasl/integration-testing | 6 | 252 | 15 | uasl/python-testing-patterns, uasl/radar | uasl/python-testing-patterns, uasl/radar |
| s1-fa-06-r2#1 | uasl/integration-testing | 5 | 5 | 4 | 적중 | uasl/python-testing-patterns, uasl/radar |
| s1-fa-07-r1#1 | uasl/python-testing-patterns | 7 | 3 | 4 | 적중 | 적중 |
| s1-fa-07-r2#1 | uasl/python-testing-patterns | 7 | 2 | 4 | 적중 | 적중 |
| s1-fa-08-r1#1 | uasl/defense-in-depth, uasl/api-design | 5 | 1 | 3 | uasl/fastapi-endpoint | 적중 |
| s1-fa-08-r2#1 | uasl/defense-in-depth, uasl/api-design | 8 | 3 | 3 | uasl/debug-root-cause, uasl/python-testing-patterns | uasl/debug-root-cause, uasl/test-driven-development, uasl/python-testing-patterns |
| s1-fa-10-r1#1 | uasl/quill | 7 | 440 | 12 | 적중 | 적중 |
| s1-nx-02-r1#1 | uasl/backend-patterns, uasl/api-design | 1 | 1 | 1 | 적중 | 적중 |
| s1-nx-02-r2#1 | uasl/backend-patterns, uasl/api-design | 1 | 1 | 1 | 적중 | 적중 |
| s1-nx-04-r1#1 | uasl/responsive-design | 1 | 3 | 2 | 적중 | 적중 |
| s1-nx-04-r2#1 | uasl/responsive-design | 1 | 3 | 2 | 적중 | 적중 |
| s1-nx-06-r1#1 | uasl/refactoring-patterns | 153 | 479 | 228 | uasl/zen, uasl/software-design-philosophy | uasl/next-best-practices, uasl/backend-patterns |
| s1-nx-06-r2#1 | uasl/refactoring-patterns | 81 | 623 | 150 | uasl/zen, uasl/next-best-practices | uasl/zen, uasl/next-best-practices |
| s1-nx-07-r1#1 | uasl/tdd-workflow | 13 | 3 | 3 | uasl/unit-testing, uasl/documentation-lookup | uasl/unit-testing, uasl/documentation-lookup |
| s1-nx-07-r2#1 | uasl/tdd-workflow | 9 | 3 | 3 | uasl/unit-testing | uasl/unit-testing, uasl/documentation-lookup |
| s1-nx-08-r1#1 | uasl/unit-testing | 1 | 23 | 9 | 적중 | 적중 |
| s1-nx-08-r2#1 | uasl/unit-testing | 3 | 273 | 24 | 적중 | 적중 |
| s1-nx-10-r1#1 | uasl/quill | 3 | 18 | 9 | 적중 | 적중 |
| s1b-fa-landing-r1#1 | anthropics-skills/frontend-design | 24 | 7 | 11 | 적중 | 적중 |
| s1b-fa-landing-r2#1 | anthropics-skills/frontend-design | 13 | 4 | 7 | 적중 | 적중 |
| s1b-fa-service-r1#1 | uasl/caveman | - | 1020 | 1072 | uasl/fastapi-templates, uasl/python-design-patterns, uasl/refactoring-patterns | uasl/python-design-patterns, uasl/fastapi-templates, uasl/refactoring-patterns |
| s1b-fa-service-r2#1 | uasl/caveman | - | 1137 | 1186 | uasl/python-design-patterns, uasl/refactoring-patterns, uasl/fastapi-templates | uasl/fastapi-templates, uasl/python-design-patterns, uasl/refactoring-patterns |
| s1b-fa-tags-plan-r1#1 | uasl/writing-plans | 93 | 425 | 150 | uasl/api-design, uasl/fastapi-endpoint | uasl/schema, uasl/api-design, uasl/frontend-patterns |
| s1b-fa-tags-plan-r2#1 | uasl/writing-plans | 29 | 108 | 32 | 적중 | 적중 |
| s1b-fa-utils-tests-r1#1 | uasl/tdd | 59 | 28 | 22 | uasl/python-testing-patterns, uasl/radar | uasl/python-testing-patterns, uasl/radar |
| s1b-fa-utils-tests-r2#1 | uasl/tdd | 47 | 14 | 14 | uasl/python-testing-patterns, uasl/unit-testing | uasl/python-testing-patterns, uasl/unit-testing |
| s1b-nx-landing-r1#1 | anthropics-skills/frontend-design | 39 | 6 | 14 | 적중 | 적중 |
| s1b-nx-landing-r2#1 | anthropics-skills/frontend-design | 41 | 5 | 14 | 적중 | 적중 |

## 기록 사항

- 문서 텍스트 = title + description + summary + synthetic_queries (줄바꿈으로 연결). 임베딩은 프로필 부스트 없음; RRF의 BM25 쪽은 search_skills 순위(프로필 부스트 포함) 그대로. BM25 히트가 없는 스킬은 임베딩 순위만 기여.
- 모델은 Hugging Face에서 한 번 내려받음(외부 API 호출 아님). 측정은 이 Mac의 CPU.
- RRF 선택은 (b)와 같은 지시문·같은 입력 형식(태스크 원문, 쿼리, 50개 id·title·전체 summary)으로 새 하위 에이전트 4개가 수행.
