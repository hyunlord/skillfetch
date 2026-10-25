# skillfetch 3단계 — 검색·선택 품질 광범위 평가 (report)

태스크 380개, oracle 라벨, 검색(오프라인 Python), 선택(배치 프롬프트), e2e 40세션(실행 2회). 생성물은 모두 jsonl로 동결했고 해시는 `FROZEN.sha256`에 있다. 이후 단계는 동결본만 읽었다. 스크립트는 `scripts/`.

## 0. 설정

| 항목 | 값 |
|---|---|
| index | index-2026-10-22 (`built_at` 2026-10-22T06:15:43Z). 평가 대상은 search_skills가 돌려줄 수 있는 canonical tier A/B 1,489개 |
| skillfetch | 검색 `main@64f4bd8`(최신). 2b 풀은 `a671e6a`로 만들었는데, 원문 쿼리 top-50이 380/380 동일함을 확인했다(`index/search.py`·`bm25.py` 변경 없음) |
| 배치 프롬프트 | 격리한 `claude -p`(Opus 5.5): 도구 없음, MCP 없음, `--setting-sources project`(사용자 훅·플러그인·CLAUDE.md 미적용), 고정 부분은 system prompt(1h 캐시). 태스크 생성 14회, 제목 누출 재작성 1회, 2a 38회, 2b 380회, 2c 40회, 3-0 380회, Q2 19회, Q3 19회, 선택 19회 + 단독 재실행 31회 |
| 태스크 | `tasks.jsonl` 380개 = 층화 300(12×6×5 셀 중 300, 셀당 1; 작업종류당 25 · 스택당 50 · 표현당 60) + expect_none 40 + 방향 쌍 20쌍(40). 생성 후 1,707개 제목과 토큰을 대조해 20개를 재작성했다(이어 붙인 식별자의 부분까지 대조) |
| oracle | 2a 카탈로그(id · title · 10단어 요약; 요약 앞 상투구 제거 후 10단어 절단, 약 83k 토큰) 10태스크씩 → 2b 풀(2a ∪ BM25 원문 top-10 ∪ 무작위 2) 0–3점 + 프로세스 표시 → **3-0 보정**: Q2·Q3·MiniLM·RRF 각 top-10을 풀에 추가하고 새 후보만 같은 프롬프트로 채점(v1 라벨 불변). 관련 = 등급 ≥2 |
| 쿼리 | Q1 원문 · Q2 라우터 1단계 규칙 그대로의 1문장 재진술 · Q3 Q2를 도메인/작업방식/스택 3문장으로 나눠 각각 검색 후 RRF(k=60). 프로필 없음(오프라인) |
| MiniLM | all-MiniLM-L6-v2, sentence-transformers, CPU. 필드 title+description+summary+keywords+synthetic_queries. RRF는 BM25 전체 순위 + 임베딩 전체 순위 |
| 선택 | 라우터 SKILL.md(main 64f4bd8)의 'When' 절 + 4단계 원문 + "1–3개 또는 none", 입력은 Q2의 실제 search_skills 출력(compact 50개), 20태스크씩 |
| e2e | 실패 분류별 층화 40개(over_load 10, select_fail 10, restate_fail 10, search_fail 7, ok 3 — search_fail은 7개뿐). 1–2단계와 같은 하네스(`claude -p` stream-json, 같은 허용 도구, 사용자 전역 `~/.claude` 상속), `--max-turns 12`, 라우터와 `.mcp.json`은 skillfetch `64f4bd8` |

### 기록 사항

- **oracle을 만든 모델이 라우터와 같다(Opus 5.5).** 2c 일치율(±1 100%, kappa 0.873)은 같은 모델 안의 일관성이고, 정답성 검증은 아니다.
- **풀링 편향**: 원래 풀이 BM25 원문 쪽으로 치우쳐 있었다(3-0에서 관련 스킬 +354개, 63% 증가). 그래도 풀 밖의 스킬은 관련이 될 수 없으므로, 남은 편향은 Q1·Q2·Q3·MiniLM·RRF가 모두 놓친 스킬 쪽이다.
- **배치 선택의 교차 오염**: 20태스크를 한 번에 주니 모델이 다른 태스크의 목록에 있던 id를 고른 경우가 31건 나왔다. 그 31개 태스크는 한 태스크씩 다시 돌려 그 결과를 썼다(`redone_alone`).
- **e2e run 1(빈 레포)은 목적을 달성하지 못했다.** 40개 중 라우터 발화 7, search 5. 세션은 사용자 전역 RULES.md의 "git status 먼저" 규칙대로 레포를 먼저 보고, 코드가 없으니 멈췄다. 그래서 run 2를 했다. 태스크가 이름을 댄 파일·디렉터리와 스택별 소스 파일 1개를 빈 스텁으로 넣고, manifest·lockfile은 넣지 않았다(profile이 비게 두어 오프라인과 같은 조건). 두 run 모두 표 4에 있다.
- **방향 지시 표현의 편중**: 생성기가 "Plan before coding"을 많이 썼다(표현 샘플 40개 중 directive 8개 가운데 4개).

## 커버리지: 작업종류별로 index에 관련 스킬(등급≥2)이 있는 태스크

관련 스킬이 없는 일반 태스크는 'index에 해당 스킬이 없음' 결과이며, 검색 지표와 선택 precision/recall 계산에서 제외했다(선택의 과잉 로드·none 정확도에는 포함).

| 작업종류 | 태스크 | 관련 없음 (v1: 2b 풀) | 관련 없음 (v2: 3-0 확장 후) | 관련 스킬 평균 (v2) | 프로세스성 관련이 있는 태스크 (v2) |
|---|---|---|---|---|---|
| feature | 29 | 10 | 8 | 2.72 | 15 |
| bugfix | 29 | 9 | 4 | 2.66 | 20 |
| refactor | 27 | 1 | 0 | 3.85 | 27 |
| tests | 29 | 4 | 1 | 3.21 | 27 |
| docs | 27 | 7 | 4 | 1.96 | 22 |
| ci_infra | 29 | 2 | 2 | 2.72 | 6 |
| deploy | 29 | 13 | 9 | 1.86 | 15 |
| data | 27 | 11 | 7 | 1.52 | 10 |
| ml | 29 | 13 | 11 | 1.41 | 12 |
| security_review | 27 | 2 | 1 | 4.52 | 21 |
| performance | 29 | 10 | 8 | 2.31 | 18 |
| ui_design | 29 | 8 | 7 | 3.21 | 14 |
| **전체(일반)** | 340 | 90 | 62 | 2.66 | 207 |

expect_none 40개 중 관련 스킬이 붙은 태스크: v1 5, v2 7.

## 3-0 풀 보정 (Q2·Q3·MiniLM·RRF top-10 추가 채점)

추가 채점 9332개(태스크 380개), 그중 등급≥2 **354개** (등급 분포 0/1/2/3 = 7768/1210/332/22). 관련 쌍 561 → 915 (+63%); 처음으로 관련 스킬이 생긴 태스크 30개. 원래 풀(2a ∪ BM25 원문 top-10 ∪ 무작위 2)이 BM25 원문 쿼리 쪽으로 치우쳐 있었다는 근거다. 아래 모든 지표는 v2 라벨 기준.

| 추가 출처(top-10) | 새로 채점 | 그중 등급≥2 |
|---|---|---|
| bm25_q2 | 1908 | 129 |
| bm25_q3 | 2454 | 171 |
| emb_q1 | 3154 | 96 |
| emb_q2 | 3190 | 117 |
| rrf_q1 | 2070 | 111 |
| rrf_q2 | 2547 | 176 |

라벨 일치(2c, 40태스크 500쌍): 완전 94.2%, ±1 100.0%, 관련 여부 kappa 0.883.

## 표 1. 검색 recall@10 / @50

(i) 전체 관련 세트(등급≥2, n=278태스크) · (ii) 2a 출처 관련 스킬만(검색과 독립, n=209) · 프로세스성 관련 스킬만(n=207). 태스크별 recall의 평균. (i)과 (ii)의 차이가 @50에서 최대 0.07이라 (i)을 주 지표로 두었다. Q3 × MiniLM은 지시 범위 밖이라 계산하지 않았다.

| 쿼리 | 방법 | (i) @10 | (i) @50 | (ii) @10 | (ii) @50 | 프로세스 @10 | 프로세스 @50 |
|---|---|---|---|---|---|---|---|
| Q1 원문 | BM25 | 0.387 | 0.683 | 0.396 | 0.639 | 0.324 | 0.632 |
| Q1 원문 | MiniLM | 0.305 | 0.514 | 0.283 | 0.489 | 0.267 | 0.465 |
| Q1 원문 | BM25+MiniLM RRF | 0.424 | 0.740 | 0.406 | 0.673 | 0.357 | 0.677 |
| Q2 재진술 | BM25 | 0.483 | 0.775 | 0.498 | 0.732 | 0.372 | 0.727 |
| Q2 재진술 | MiniLM | 0.317 | 0.531 | 0.351 | 0.494 | 0.234 | 0.449 |
| Q2 재진술 | BM25+MiniLM RRF | 0.473 | 0.801 | 0.435 | 0.745 | 0.374 | 0.734 |
| Q3 다중쿼리(3문장 RRF) | BM25 | 0.535 | 0.835 | 0.474 | 0.764 | 0.425 | 0.783 |

### 표 1-작업종류: (i) recall@50 (괄호 안 n)

| 작업종류 | n | Q1 BM25 | Q2 BM25 | Q3 BM25 | Q2 MiniLM | Q2 RRF |
|---|---|---|---|---|---|---|
| bugfix | 25 | 0.631 | 0.715 | 0.824 | 0.494 | 0.793 |
| ci_infra | 27 | 0.945 | 0.957 | 0.977 | 0.597 | 0.927 |
| data | 20 | 0.654 | 0.717 | 0.817 | 0.433 | 0.746 |
| deploy | 20 | 0.662 | 0.629 | 0.886 | 0.581 | 0.875 |
| docs | 23 | 0.845 | 0.842 | 0.925 | 0.601 | 0.865 |
| feature | 21 | 0.723 | 0.875 | 0.920 | 0.517 | 0.808 |
| ml | 18 | 0.744 | 0.672 | 0.830 | 0.330 | 0.659 |
| performance | 21 | 0.409 | 0.539 | 0.773 | 0.574 | 0.677 |
| refactor | 27 | 0.602 | 0.849 | 0.768 | 0.286 | 0.741 |
| security_review | 26 | 0.487 | 0.693 | 0.707 | 0.564 | 0.751 |
| tests | 28 | 0.743 | 0.945 | 0.880 | 0.740 | 0.976 |
| ui_design | 22 | 0.728 | 0.738 | 0.711 | 0.600 | 0.712 |

### 표 1-스택: (i) recall@50 (괄호 안 n)

| 스택 | n | Q1 BM25 | Q2 BM25 | Q3 BM25 | Q2 MiniLM | Q2 RRF |
|---|---|---|---|---|---|---|
| go | 45 | 0.599 | 0.706 | 0.776 | 0.467 | 0.733 |
| java_kotlin | 45 | 0.612 | 0.668 | 0.792 | 0.439 | 0.739 |
| mobile | 40 | 0.747 | 0.784 | 0.864 | 0.412 | 0.749 |
| python | 52 | 0.703 | 0.843 | 0.896 | 0.552 | 0.877 |
| rust | 41 | 0.615 | 0.775 | 0.780 | 0.577 | 0.808 |
| ts_react_next | 55 | 0.798 | 0.848 | 0.882 | 0.693 | 0.869 |

### 표 1-표현: (i) recall@50 (괄호 안 n)

| 표현 | n | Q1 BM25 | Q2 BM25 | Q3 BM25 | Q2 MiniLM | Q2 RRF |
|---|---|---|---|---|---|---|
| directive | 89 | 0.705 | 0.720 | 0.794 | 0.529 | 0.747 |
| korean | 47 | 0.543 | 0.814 | 0.825 | 0.582 | 0.800 |
| normal | 47 | 0.656 | 0.724 | 0.860 | 0.444 | 0.762 |
| spec | 59 | 0.765 | 0.790 | 0.823 | 0.517 | 0.830 |
| terminal | 36 | 0.715 | 0.901 | 0.938 | 0.609 | 0.940 |

MiniLM 비용: 모델 91.6 MB(HF 캐시), 임베딩 1489개 계산 7.59 s(CPU), 저장 2.29 MB(float32), 모델 로드 6.44 s, 쿼리당 6.1 ms(중앙; BM25 7.6 ms), 256토큰 넘어 잘린 문서 357.

## 표 2. 선택 (Q2 top-50 compact → 1–3개 또는 none, 라우터 4단계·skip 규칙 그대로)

| 지표 | 값 |
|---|---|
| precision (선택 세트 중 등급≥2) | 0.807 (n=256) |
| recall (관련 세트 중 선택된 비율) | 0.423 (n=278) |
| 적중 (관련 1개 이상 선택) | 0.824 (n=278) |
| 태스크당 로드 수 | 1.142 |
| 잘못 로드(등급<2) | 113개, 104태스크 |
| 과잉 로드 (oracle 관련 없음인데 로드) | 30태스크 |
| none 정확도 — oracle 기준 (관련 없음 95태스크) | 0.684 |
| none 정확도 — expect_none 기준 (40태스크) | 0.700 |
| 방향 쌍: 세트가 바뀜 | 16/20 (oracle 세트가 다른 쌍 16) |
| 방향 쌍: 방향대로 바뀜 | 10/20 |

| 표현 | 태스크 | precision | recall | 적중 | 과잉 로드 | none 정확도(oracle) |
|---|---|---|---|---|---|---|
| directive | 108 | 0.805 | 0.382 | 0.831 | 6 | 0.647 |
| korean | 68 | 0.762 | 0.404 | 0.745 | 6 | 0.684 |
| normal | 68 | 0.762 | 0.408 | 0.702 | 9 | 0.571 |
| spec | 68 | 0.775 | 0.433 | 0.898 | 4 | 0.500 |
| terminal | 68 | 0.971 | 0.552 | 0.944 | 5 | 0.833 |

## 표 3. 실패 분류

ok = 관련 세트가 없고 아무것도 안 고름, 또는 관련 1개 이상 고름 · select_fail = 관련 스킬이 Q2 top-50에 있는데 안 고름 · restate_fail = Q2 top-50 밖, Q1 또는 Q3 top-50 안 · search_fail = 어느 쿼리로도 top-50 밖 · over_load = 관련 없음인데 로드.

| 층 | 그룹 | n | ok | select_fail | restate_fail | search_fail | over_load |
|---|---|---|---|---|---|---|---|
| 전체 | - | 380 | 298 | 25 | 20 | 7 | 30 |
| 작업종류 | bugfix | 29 | 19 | 2 | 2 | 2 | 4 |
| 작업종류 | ci_infra | 29 | 27 | 2 | 0 | 0 | 0 |
| 작업종류 | data | 27 | 21 | 1 | 3 | 0 | 2 |
| 작업종류 | deploy | 29 | 24 | 0 | 4 | 1 | 0 |
| 작업종류 | docs | 27 | 22 | 1 | 1 | 0 | 3 |
| 작업종류 | feature | 29 | 24 | 2 | 1 | 0 | 2 |
| 작업종류 | ml | 29 | 19 | 4 | 3 | 0 | 3 |
| 작업종류 | performance | 29 | 20 | 0 | 3 | 1 | 5 |
| 작업종류 | refactor | 27 | 25 | 1 | 0 | 1 | 0 |
| 작업종류 | security_review | 27 | 21 | 3 | 1 | 2 | 0 |
| 작업종류 | tests | 29 | 25 | 3 | 0 | 0 | 1 |
| 작업종류 | trivial | 40 | 29 | 3 | 0 | 0 | 8 |
| 작업종류 | ui_design | 29 | 22 | 3 | 2 | 0 | 2 |
| 스택 | go | 63 | 48 | 5 | 4 | 1 | 5 |
| 스택 | java_kotlin | 62 | 44 | 6 | 6 | 1 | 5 |
| 스택 | mobile | 62 | 44 | 4 | 4 | 1 | 9 |
| 스택 | python | 65 | 56 | 1 | 3 | 1 | 4 |
| 스택 | rust | 63 | 48 | 5 | 3 | 2 | 5 |
| 스택 | ts_react_next | 65 | 58 | 4 | 0 | 1 | 2 |
| 표현 | directive | 108 | 86 | 5 | 6 | 5 | 6 |
| 표현 | korean | 68 | 49 | 10 | 3 | 0 | 6 |
| 표현 | normal | 68 | 45 | 6 | 7 | 1 | 9 |
| 표현 | spec | 68 | 58 | 2 | 3 | 1 | 4 |
| 표현 | terminal | 68 | 60 | 2 | 1 | 0 | 5 |

### 분류별 대표 사례 3개

#### select_fail

- **t012** (feature, go, korean)
  - 태스크: matchmaking 서버(internal/matchmaker)에 region 필터 추가해줘. FindMatchRequest proto에 preferred_regions 필드 넣고, 30초 지나도 매칭 안 되면 인접 region까지 범위 넓히는 로직도 같이 부탁해.
  - Q2: Add region filtering to the Go matchmaking server in `internal/matchmaker` via a new `preferred_regions` field on the `FindMatchRequest` proto, widening the search to adjacent regions when no match is found after 30 seconds.
  - 선택: none
  - oracle 관련(등급≥2)과 순위: `uasl/unit-testing` Q1 #>50, Q2 #48, Q3 #7

- **t019** (feature, java_kotlin, normal)
  - 태스크: Teachers want timed quizzes. Can you add an optional timeLimitMinutes to the Quiz entity in our Spring Boot service, record when an attempt starts, and have QuizAttemptService reject submissions that arrive after the limit plus a 30-second grace period?
  - Q2: Add an optional `timeLimitMinutes` to the Spring Boot `Quiz` entity, record attempt start times, and make `QuizAttemptService` reject submissions after the time limit plus a 30-second grace period.
  - 선택: `uasl/builder`
  - oracle 관련(등급≥2)과 순위: `uasl/integration-testing` Q1 #1, Q2 #1, Q3 #9

- **t037** (bugfix, go, korean)
  - 태스크: `pkg/scheduler/slots.go`에서 병원 예약 가능 시간 계산할 때 `time.Truncate`를 써서 KST 기준으로 하루 경계가 9시간 밀리고 있어요. 그래서 오전 9시 전 슬롯이 전날로 잡히는데, location 기준으로 날짜 자르도록 고쳐주고 테이블 테스트도 추가해 주세요.
  - Q2: Fix the Go hospital appointment slot calculation in `pkg/scheduler/slots.go` to cut day boundaries by the KST location instead of `time.Truncate` so pre-9 AM slots no longer fall on the previous day, and add table-driven tests.
  - 선택: `uasl/debug-root-cause`, `uasl/unit-testing`
  - oracle 관련(등급≥2)과 순위: `uasl/radar` Q1 #>50, Q2 #12, Q3 #>50; `uasl/tdd` Q1 #>50, Q2 #2, Q3 #35; `uasl/test-driven-development` Q1 #>50, Q2 #10, Q3 #31

#### restate_fail

- **t013** (feature, go, directive)
  - 태스크: Add ETag and If-None-Match support to the product catalog endpoints in internal/catalog/handler.go so the mobile app stops re-downloading unchanged listings. Don't add any new dependencies; compute the ETag from the product's updated_at and version columns with the standard library, and return 304 with no body when it matches.
  - Q2: Add ETag and If-None-Match support to the Go product catalog handlers in `internal/catalog/handler.go`, computing the ETag with the standard library from `updated_at` and `version` and returning 304 with no body on a match.
  - 선택: none
  - oracle 관련(등급≥2)과 순위: `uasl/api-design` Q1 #>50, Q2 #>50, Q3 #25

- **t026** (bugfix, python, normal)
  - 태스크: Patients are getting their refill reminder SMS twice on the Sunday clocks change. The Celery beat job in `reminders/tasks.py::send_due_refill_reminders` compares naive datetimes against `Prescription.next_refill_at`, which is stored in UTC. Can you fix the comparison so each reminder fires exactly once across DST transitions?
  - Q2: Fix the naive-versus-UTC datetime comparison in the Celery beat job `send_due_refill_reminders` in `reminders/tasks.py` against `Prescription.next_refill_at` so each refill reminder SMS fires exactly once across DST transitions.
  - 선택: none
  - oracle 관련(등급≥2)과 순위: `uasl/debug-root-cause` Q1 #>50, Q2 #>50, Q3 #21; `uasl/python-testing-patterns` Q1 #>50, Q2 #>50, Q3 #45

- **t040** (bugfix, rust, normal)
  - 태스크: Our IoT firmware update server deadlocks under load. In `src/updates/registry.rs`, `assign_rollout` holds the `devices` tokio `Mutex` across an `.await` on the S3 presign call, and `heartbeat` takes the locks in the opposite order. Can you restructure it so we never hold a lock across an await and the lock order is consistent?
  - Q2: Restructure `assign_rollout` and `heartbeat` in the Rust IoT firmware update server's `src/updates/registry.rs` so no tokio `Mutex` is held across the S3 presign `.await` and locks are always acquired in a consistent order, eliminating the deadlock under load.
  - 선택: none
  - oracle 관련(등급≥2)과 순위: `uasl/specter` Q1 #1, Q2 #>50, Q3 #2

#### search_fail

- **t033** (bugfix, ts_react_next, directive)
  - 태스크: In the CMS editor, pasting from Google Docs into `components/editor/RichTextField.tsx` strips all links, because our sanitize step in `lib/sanitizeHtml.ts` drops `<a>` tags whose href has a `google.com/url?q=` wrapper. Keep the diff minimal: just unwrap the redirect to the real URL and allow it through the existing allowlist, no new packages, and don't touch the toolbar code.
  - Q2: Minimally fix `lib/sanitizeHtml.ts` so links pasted from Google Docs into `components/editor/RichTextField.tsx` have their `google.com/url?q=` redirect unwrapped to the real URL and pass the existing allowlist, without new packages or toolbar changes.
  - 선택: `uasl/coding-guidelines`
  - oracle 관련(등급≥2)과 순위: `uasl/secure-coding-practices` Q1 #>50, Q2 #>50, Q3 #>50

- **t038** (bugfix, go, directive)
  - 태스크: The fleet tracking API returns a 500 on `GET /vehicles/{id}/route` when a vehicle has zero GPS points, because `internal/route/simplify.go` indexes `points[0]` unconditionally. Fix it and keep it backward compatible: an empty route should come back as `{"points": []}` with 200, the same shape existing clients already parse, not a 404 or null.
  - Q2: Fix the Go fleet tracking API's 500 on `GET /vehicles/{id}/route` for vehicles with zero GPS points by guarding the unconditional `points[0]` index in `internal/route/simplify.go` and returning 200 with `{"points": []}`.
  - 선택: `uasl/api-design`, `uasl/coding-guidelines`
  - oracle 관련(등급≥2)과 순위: `uasl/error-handling-patterns` Q1 #>50, Q2 #>50, Q3 #>50

- **t073** (refactor, mobile, normal)
  - 태스크: Our banking app's `TransferViewModel` calls Retrofit and the Room DAO directly and handles the caching itself. Could you move that into a `TransferRepository` injected with Hilt, so the ViewModel only deals with UI state and the Compose screen stays the same?
  - Q2: Move the Retrofit calls, Room DAO access and caching out of the Android banking app's `TransferViewModel` into a Hilt-injected `TransferRepository`, so the ViewModel only handles UI state and the Compose screen stays unchanged.
  - 선택: none
  - oracle 관련(등급≥2)과 순위: `uasl/clean-architecture` Q1 #>50, Q2 #>50, Q3 #>50; `uasl/refactoring-patterns` Q1 #>50, Q2 #>50, Q3 #>50

#### over_load

- **t002** (feature, python, normal)
  - 태스크: Front desk staff at the clinics keep asking for recurring appointments, like every Tuesday at 10 for six weeks. Can you add a recurrence option to the Appointment model in scheduling/models.py and have AppointmentCreateView generate the individual slots? It should skip any date where the provider already has a ProviderTimeOff entry.
  - Q2: Add a recurrence option to the Django `Appointment` model in `scheduling/models.py` and make `AppointmentCreateView` generate the individual appointment slots, skipping dates where the provider has a `ProviderTimeOff` entry.
  - 선택: `uasl/builder`
  - oracle 관련(등급≥2)과 순위: -

- **t023** (feature, mobile, normal)
  - 태스크: In the Flutter fitness app, people log workouts in basement gyms with no signal and lose everything. Can you make workout logging work offline by saving sets to the local Drift database first and syncing them to /api/workouts when connectivity comes back?
  - Q2: Make workout logging in the Flutter fitness app work offline by saving sets to the local Drift database first and syncing them to `/api/workouts` when connectivity returns.
  - 선택: `uasl/schema`
  - oracle 관련(등급≥2)과 순위: -

- **t041** (bugfix, rust, korean)
  - 태스크: 주문 매칭 엔진 `src/book/order_book.rs`에서 같은 가격에 들어온 주문이 시간 순서대로 체결이 안 되고 가끔 뒤에 온 주문이 먼저 체결돼요. `BinaryHeap`에 timestamp만 넣고 있어서 동일 timestamp일 때 순서가 보장 안 되는 것 같은데, sequence number 기준으로 FIFO 보장되게 고쳐주세요.
  - Q2: Fix the Rust order matching engine in `src/book/order_book.rs` so orders at the same price fill in strict FIFO order by sequence number rather than by timestamp alone in the `BinaryHeap`.
  - 선택: `uasl/karpathy-guidelines`, `uasl/property-based-testing`
  - oracle 관련(등급≥2)과 순위: -

## 표 4. e2e 40세션 vs 오프라인 선택

같은 40태스크를 실제 Claude Code 세션(skillfetch MCP + 라우터 main 64f4bd8, --max-turns 12)으로 돌려 실제 load_skills 결과를 오프라인 선택(표 2)과 비교. 작업 결과물은 채점하지 않았다. run 1은 라우터·.mcp.json만 있는 빈 레포, run 2는 태스크가 이름을 댄 파일·디렉터리와 스택별 소스 파일 1개를 빈 스텁으로 만든 레포(manifest·lockfile 없음 → profile_repo 결과는 빈 프로필, 오프라인과 같음). 세션이 search를 안 하면 로드 세트는 빈 집합으로 비교했다.

| 지표 | run 1: 빈 레포 | run 2: 스텁 레포 |
|---|---|---|
| 라우터 발화 | 7/40 | 12/40 |
| search 호출 | 5/40 | 12/40 |
| 1개 이상 로드 | 3/40 | 9/40 |
| 로드 세트 완전 일치 (40 기준) | 13/40 | 11/40 |
| 평균 Jaccard (40 기준) | 0.35 | 0.296 |
| none/로드 여부 일치 | 15/40 | 15/40 |
| 관련 적중 여부 일치 | 38/40 | 33/40 |
| 실패 분류 일치 | 18/40 | 17/40 |
| search한 세션 | 5 | 12 |
| 그중 세트 완전 일치 | 2/5 | 2/12 |
| 그중 평균 Jaccard | 0.6 | 0.236 |
| 그중 분류 일치 | 3/5 | 4/12 |
| 그중 search 결과 top-50 vs 오프라인 Q2 top-50 Jaccard | 0.426 | 0.448 |
| search 안 한 세션의 첫 도구 | Bash 23, Read 5, Grep 3, Skill(skillfetch-router) 2, Skill(<E2 plugin>:autopilot) 1, Glob 1 | Bash 17, Read 3, Glob 3, Grep 3, Skill(<E2 plugin>:autopilot) 1, Skill(skillfetch-router) 1 |

run 2: 스텁 레포, 오프라인 분류별:

| 오프라인 분류 | n | 세트 완전 일치 | 분류 일치 | 평균 Jaccard |
|---|---|---|---|---|
| over_load | 10 | 1 | 3 | 0.15 |
| select_fail | 10 | 4 | 0 | 0.433 |
| restate_fail | 10 | 5 | 8 | 0.5 |
| search_fail | 7 | 1 | 6 | 0.143 |
| ok | 3 | 0 | 0 | 0.0 |

run 2: 스텁 레포, 세션별:

| 태스크 | 오프라인 분류 | e2e 분류 | 오프라인 선택 | e2e 로드 | e2e 쿼리 |
|---|---|---|---|---|---|
| t012 | select_fail | not_in_results | none | uasl/builder, uasl/codenavi | Add a preferred_regions field to the FindMatchRequest protobuf message and implement region filtering with expansion to  |
| t013 | restate_fail | ok | none | uasl/api-design | Add ETag and If-None-Match conditional GET support returning 304 Not Modified to the Go net/http product catalog handler |
| t023 | over_load | over_load | uasl/schema | uasl/schema, uasl/tdd-workflow | Add offline-first workout logging to a Flutter app by persisting sets in a local Drift (SQLite) database and syncing pen |
| t033 | search_fail | not_in_results | uasl/coding-guidelines | none | - |
| t037 | select_fail | ok | uasl/debug-root-cause, uasl/unit-testing | uasl/debug-root-cause, uasl/tdd | Fix a Go timezone bug in pkg/scheduler/slots.go where time.Truncate cuts days in UTC instead of the Asia/Seoul location, |
| t038 | search_fail | not_in_results | uasl/api-design, uasl/coding-guidelines | none | - |
| t073 | search_fail | ok | none | uasl/coding-guidelines, uasl/refactoring-patterns | Refactor an Android Kotlin TransferViewModel that calls Retrofit and a Room DAO directly into a Hilt-injected TransferRe |
| t090 | ok | not_in_results | uasl/unit-testing | none | - |
| t091 | select_fail | not_in_results | uasl/unit-testing | none | - |
| t098 | over_load | ok | uasl/unit-testing | none | - |
| t100 | select_fail | ok | uasl/typescript-unit-testing | uasl/unit-testing, uasl/vercel-react-native-skills | Write Jest tests with @testing-library/react-native for a React Native useOfflineSync hook, mocking NetInfo to verify re |
| t101 | over_load | ok | uasl/clean-code | none | - |
| t115 | over_load | ok | uasl/quill | none | - |
| t118 | restate_fail | not_in_results | none | none | - |
| t128 | select_fail | not_in_results | none | none | Configure tox.ini with py310/py311/py312 envs and GitLab CI .gitlab-ci.yml parallel:matrix to test a Python library acro |
| t147 | ok | select_fail | uasl/github-actions-templates | none | Set up fastlane match for iOS code signing certificates and provisioning profiles in a CI pipeline running on a macOS ru |
| t153 | restate_fail | not_in_results | none | none | - |
| t161 | restate_fail | not_in_results | uasl/error-handling-patterns | none | - |
| t167 | search_fail | not_in_results | uasl/it-infrastructure-sysadmin-engine | none | Write a hardened systemd service unit (non-root DynamicUser/dedicated user, ProtectSystem=strict, NoNewPrivileges, LoadC |
| t169 | restate_fail | not_in_results | none | none | - |
| t173 | restate_fail | not_in_results | none | none | - |
| t179 | over_load | over_load | uasl/stream | uasl/documentation-lookup | Write a Python polars data job in analytics/jobs/dedupe_events.py that deduplicates analytics event rows keeping the ear |
| t219 | restate_fail | select_fail | none | uasl/tdd | Add a Kotlin Spring Boot 3 Gradle module :delay-model that loads an XGBoost4J shipment delay classifier from S3 with hot |
| t224 | restate_fail | not_in_results | none | none | - |
| t229 | search_fail | not_in_results | none | none | - |
| t231 | select_fail | not_in_results | uasl/security-review | none | - |
| t243 | select_fail | not_in_results | none | none | - |
| t246 | search_fail | not_in_results | uasl/top-100-web-vulnerabilities-reference | none | - |
| t248 | restate_fail | not_in_results | uasl/insecure-defaults | none | - |
| t265 | search_fail | not_in_results | uasl/bolt | none | - |
| t288 | over_load | over_load | uasl/anvil | uasl/anvil | Make the selected row bold and add a vertical scrollbar on the right in a Rust ratatui terminal log viewer in src/main.r |
| t295 | restate_fail | not_in_results | uasl/interaction-design | none | - |
| t304 | select_fail | not_in_results | none | none | - |
| t320 | select_fail | not_in_results | none | none | - |
| t323 | over_load | ok | uasl/coding-guidelines, uasl/verification-loop | none | - |
| t333 | over_load | ok | uasl/coding-guidelines, uasl/verification-before-completion | none | - |
| t335 | over_load | ok | uasl/verification-loop | none | - |
| t357 | select_fail | not_in_results | uasl/accessibility-compliance, uasl/quill | none | - |
| t366 | ok | not_in_results | uasl/fastapi-endpoint | none | - |
| t376 | over_load | ok | uasl/scout | none | - |

## 결론 (숫자만)

관련 세트가 있는 일반 태스크 278개 중 실패는 select_fail 25, restate_fail 20, search_fail 7; 관련 없는 95태스크 중 과잉 로드 30 (none 정확도 oracle 기준 0.684, expect_none 기준 0.700). 선택은 precision 0.807, recall 0.423, 적중 0.824. 검색 recall@50(i): Q1 0.683 → Q2 0.775 → Q3 0.835; 다중쿼리 효과(Q3−Q2) @50 +0.060, 프로세스 층 +0.056. MiniLM(BM25+MiniLM RRF − BM25) @50: Q2 +0.026, Q1 +0.057, 프로세스 층(Q2) +0.007 → **효과 없음 확정** (기준 +0.10). 병목 순서(태스크 수): 선택 55 (select_fail 25 + over_load 30) > 재진술 20 > 검색 7. e2e(run 2, 스텁 레포) 40세션: search까지 간 세션 12/40, 그 12개에서 로드 세트 완전 일치 2/12, 평균 Jaccard 0.236, 세션 search 결과 top-50과 오프라인 Q2 top-50의 Jaccard 0.448; 40개 전체 기준 세트 일치 11/40, 분류 일치 17/40 — 오프라인 선택이 실제 세션의 로드를 재현한다는 근거로는 성립하지 않는다.

