# 6a단계 — 선택 규칙 수정 (오프라인) (report)

세션 실행은 없다. 모든 호출은 격리 `claude -p`(도구·MCP·사용자 설정 없음, 시스템 프롬프트 1h 캐시)이고, 외부 API 키는 쓰지 않았다. 스크립트는 `scripts/`, 해시는 `FROZEN.sha256`에 있다.

## 0. 설정

| 항목 | 값 |
|---|---|
| 라우터 | main `cc5d16c`의 `assets/router-skill/SKILL.md`(= 5단계 V1, 60줄) → `select-cands/S-0/SKILL.md` 그대로 |
| 검색 | 380태스크의 R-c 쿼리(`stage3/followup/rc-R-c-380.jsonl`) → skillfetch `cc5d16c` `search_skills(queries=…)` 출력 그대로(compact 50, profile 없음). top-50은 3단계 R-c 순위와 380/380 같다 |
| 선택 프롬프트 | 시스템 프롬프트 = 후보 SKILL.md 전문 + 중립 래퍼("`resolve_set`에 넘길 `auto_ids`, 부르지 않으면 빈 목록"). 사용자 프롬프트 = 요청 원문 + `queries` + 그 태스크의 search 결과. 10태스크/호출. 다른 태스크의 id를 고른 태스크는 한 태스크씩 다시 돌렸다(S-0 14, S-a 22, S-b 7, S-c 9) |
| 3단계와 다른 점 | 3단계 선택 래퍼에는 "none when no result fits"가 있었다. 이번 래퍼에는 없다. 그래서 S-0 수치는 3단계 표 2와 직접 비교하지 않는다 |
| oracle | **v4** = 3단계 v3 + 네 후보가 고른 스킬 중 풀 밖이던 126개(같은 2b 프롬프트, $1.08, 새 관련 67). 관련 쌍 1015 → 1082, 관련 없음 태스크 89 → 85 |
| 관련 없음 태스크 수 | 지시문의 95는 v2 기준이다(v2 95, v3 89, v4 85). 아래 none-정확도(관련 없음)는 v4의 85개 기준이다 |
| expect_none | 40개(사소한 작업). v4에서 그중 33개는 관련 없음이다 |

## 1. kind 라벨 (`kind.jsonl`)

index의 tier A/B canonical 1,489개 전부(3단계 카탈로그)에 라벨을 붙였다. 시스템 프롬프트는 정의와 카탈로그 전체(`gen/sys-kind.txt`)이고, 50개씩 카드(id, title, 전체 summary, tags)를 주었다. 30회, $7.3.

| kind | 개수 |
|---|---|
| domain | 345 |
| process | 251 |
| tooling | 893 |

oracle v3의 process 표시와 비교했다(kind = process ⇔ process 표시):

| 기준 | n | 일치율 | kappa | kind process · 표시 있음 | kind process · 표시 없음 | kind 다른 것 · 표시 있음 | kind 다른 것 · 표시 없음 |
|---|---|---|---|---|---|---|---|
| 채점된 (태스크, 스킬) 쌍 전체 | 16271 | 0.884 | 0.698 | 3262 | 501 | 1388 | 11120 |
| 관련 쌍(등급 ≥2) | 1015 | 0.832 | 0.659 | 362 | 57 | 114 | 482 |
| 스킬 단위(그 스킬 표시의 다수결) | 1359 | 0.931 | 0.789 | 233 | 16 | 78 | 1032 |

## 2. 후보 규칙

세 후보는 같은 구조 편집을 공유한다. 선택 단계 밖의 편집이다.
- `## Rules` 절을 없앴다.
- "Never load a skill that `resolve_set` excluded"는 6단계 "Respect `excluded`"와 같은 말이라 지웠다.
- "Do not search again mid-task unless the task changes"는 3단계 끝의 "Search once per task."로 옮겼다.
- 1단계(측정된 R-c 재진술)는 그대로다.
- 4단계 문구만 후보마다 다르다.

S-b와 S-c는 "pick 1–3"을 "pick up to 3"으로 바꿨다. 0개를 허용하는 새 문장과 어긋나지 않게 하려는 것이다.

| 후보 | 줄 수 | 4단계 문구 |
|---|---|---|
| S-0 (main) | 60 | 4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is often not near the top. Each result has a `token_estimate`: when two fit equally, take the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default). |
| S-a | 57 | 4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is often not near the top. Each result has a `kind` (domain, process or tooling) and a `token_estimate`: when two fit equally, take the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default). |
| S-b | 59 | 4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best first: read all 50 and pick up to 3 that fit this task — the best fit is often not near the top. Do not pick a skill unless you can say in one sentence what its summary changes in this task; often none fits, and then you skip steps 6–7. Each result has a `kind` (domain, process or tooling) and a `token_estimate`: when two fit equally, take the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default). |
| S-c | 60 | 4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best first: read all 50 and pick up to 3 that fit this task — the best fit is often not near the top. Do not pick a skill unless you can say in one sentence what its summary changes in this task; often none fits, and then you skip steps 6–7. If the user said how to work (test first, minimal diff, plan first), include one process skill; if not, pick a process skill only when no domain skill fits. Each result has a `kind` (domain, process or tooling) and a `token_estimate`: when two fit equally, take the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default). |

S-a·S-b·S-c의 search 결과에는 각 항목의 `tier` 뒤에 `"kind"`가 들어간다. S-0의 결과는 서버 출력 그대로다.

## 3. 표 — 선택 지표 (oracle v4; 괄호는 v3)

| 지표 | S-0 | S-a | S-b | S-c |
|---|---|---|---|---|
| precision (고른 태스크; 관련 있는 태스크 n=288) | 0.85 (0.75) | 0.828 (0.725) | 0.906 (0.798) | 0.9 (0.793) |
| recall | 0.456 (0.422) | 0.462 (0.421) | 0.35 (0.325) | 0.357 (0.336) |
| hit (관련 1개 이상 고름) | 0.882 (0.831) | 0.889 (0.845) | 0.792 (0.729) | 0.816 (0.75) |
| none-정확도 — 관련 없음 태스크 (v4 85 / v3 89) | 0.553 (0.528) | 0.518 (0.494) | 0.894 (0.854) | 0.8 (0.764) |
| none-정확도 — expect_none 40 | 0.65 (0.65) | 0.675 (0.675) | 0.85 (0.85) | 0.75 (0.75) |
| 과잉 로드 태스크 (관련 없음인데 고름) | 38 (42) | 41 (45) | 9 (13) | 17 (21) |
| 잘못 로드 수 (등급 <2, 380 전체) | 117 (169) | 133 (192) | 43 (87) | 51 (92) |
| 관련 있는 태스크에서 none | 15 (15) | 12 (12) | 46 (46) | 33 (33) |
| 태스크당 평균 로드 수 | 1.368 (1.368) | 1.432 (1.432) | 0.958 (0.958) | 0.992 (0.992) |
| 방향 쌍: 세트가 바뀜 / 20 | 16 (16) | 14 (14) | 16 (16) | 13 (13) |
| 방향 쌍: 방향대로 바뀜 / 20 | 9 (7) | 9 (6) | 12 (8) | 10 (6) |
| directive 100개 중 process 스킬을 고른 태스크 (그중 관련) | 60 (47) | 61 (49) | 48 (45) | 57 (47) |
| directive 아닌 240개 중 process 스킬을 고른 태스크 | 117 | 118 | 96 | 83 |
| 고른 스킬의 kind (domain / process / tooling) | 244 / 243 / 33 | 258 / 249 / 37 | 165 / 176 / 23 | 194 / 161 / 22 |
| 비용 ($, 단독 재실행 포함) | 18.64 | 20.37 | 19.52 | 19.81 |

방향 쌍 기준의 상한: 20쌍 중 두 쪽의 oracle 관련 세트가 다른 쌍은 16개다(process 관련 세트가 다른 쌍 13). "방향대로 바뀜"은 세트가 바뀌고, 각 쪽에 더한 스킬이 그쪽에만 관련이어야 센다(3단계 `eval_selection.py` 정의). 그래서 15/20은 16개 중 15개를 맞혀야 한다.

## 판정 (기준: none-정확도 ≥ 0.85, hit 하락 ≤ 0.05, 방향 쌍 ≥ 15/20; v4)

| 후보 | none-정확도 (관련 없음 85) | none-정확도 (expect_none 40) | hit 하락 (S-0 대비) | 방향 쌍 | 통과 |
|---|---|---|---|---|---|
| S-a | 0.518 ✗ | 0.675 ✗ | -0.007 ✓ | 9/20 ✗ | 아니오 |
| S-b | 0.894 ✓ | 0.85 ✓ | +0.090 ✗ | 12/20 ✗ | 아니오 |
| S-c | 0.8 ✗ | 0.75 ✗ | +0.066 ✗ | 10/20 ✗ | 아니오 |

**세 기준을 모두 넘은 후보는 없다. 승자 없음.** none-정확도 기준만 넘은 것은 S-b다(관련 없음 0.894, expect_none 0.85). S-b의 hit 하락은 0.090, 방향 쌍은 12/20이다.

## 실패 사례 (S-b, 시드 `6a-cases`로 5개씩)

S-b의 과잉 로드는 9건이다. 9건 모두 process 스킬만 골랐고, 모두 등급 1이다(7건은 1개, 2건은 2개). S-0이 맞혔는데 S-b가 놓친 태스크는 28개이고, 그중 21개에서 S-b는 아무것도 고르지 않았다. 표기는 (스킬, kind, 등급, search 순위).

### 과잉 로드 5

**t048** (bugfix · normal) — S-b: uasl/debug-root-cause (process, 1, 35위); S-0: uasl/debug-root-cause (process, 1); 관련 없음

> In the Flutter fitness app, the workout timer keeps running correctly in the foreground but shows the wrong elapsed time after the app is backgrounded for a few minutes on iOS. `lib/workout/timer_controller.dart` just increments a counter in a `Timer.periodic`. Can you change it to derive elapsed time from a start timestamp so it survives backgrounding?

**t109** (docs · terminal) — S-b: uasl/quill (process, 1, 4위); S-0: uasl/quill (process, 1), uasl/coding-guidelines (process, 1); 관련 없음

> godoc comments for all exported funcs in pkg/ledger, golint is complaining

**t115** (docs · normal) — S-b: uasl/quill (process, 1, 47위); S-0: uasl/quill (process, 1); 관련 없음

> Our soil-moisture sensor firmware crate has about 20 unsafe blocks in src/hal/adc.rs and src/dma.rs with no justification, and clippy's undocumented_unsafe_blocks lint is about to be turned on in CI. Can you add a // SAFETY: comment above each one explaining why it's actually sound? Flag any you think aren't sound instead of making something up.

**t214** (ml · normal) — S-b: uasl/debug-root-cause (process, 1, 26위); S-0: uasl/debug-root-cause (process, 1), uasl/coding-guidelines (process, 1); 관련 없음

> The linfa k-means clustering we use in `src/segment.rs` to group game players by playstyle gives different clusters every run, which makes the weekly reports useless. Can you seed the RNG from config, add k-means++ init, and print a silhouette score so we can pick k properly?

**t263** (performance · terminal) — S-b: uasl/refactoring-patterns (process, 1, 46위); S-0: uasl/refactoring-patterns (process, 1); 관련 없음

> parse_order_book in feed/l2.rs clones every price level, make it zero-copy with borrowed &str

### 놓침 5 (S-0은 관련 스킬을 골랐고 S-b는 못 골랐다)

**t022** (feature · terminal) — S-b: 없음; S-0: uasl/ios-hig-design (domain, 2, 7위); 관련 1개: uasl/ios-hig-design (domain, 2, 7위)

> swiftui: add pull-to-refresh to OrdersListView, call OrdersViewModel.reload()

**t046** (bugfix · directive) — S-b: uasl/security-review (domain, 1, 14위); S-0: uasl/secure-coding-practices (domain, 2, 5위), uasl/error-handling-patterns (domain, 2, 1위); 관련 9개: uasl/secure-coding-practices (domain, 2, 5위), uasl/error-handling-patterns (domain, 2, 1위), uasl/code-security (domain, 2, 11위), uasl/integration-testing (process, 2, 20위), uasl/specter (domain, 2, 50위 밖) …

> Our inventory service throws `OptimisticLockException` storms during flash sales and then returns 409 to the warehouse scanners even when stock is available. The retry in `StockReservationService.reserve()` catches the wrong exception type because the JPA one gets wrapped in `ObjectOptimisticLockingFailureException`. Security first: while fixing the retry, make sure the error response stops leaking the entity class name and SQL state to the client.

**t178** (data · korean) — S-b: 없음; S-0: uasl/data-analyst-engine (domain, 2, 12위); 관련 1개: uasl/data-analyst-engine (domain, 2, 12위)

> lms/exports/quiz_attempts.csv에서 학생별 최고 점수랑 평균 응시 횟수를 과목별로 집계하는 스크립트를 scripts/aggregate_quiz.py로 만들어 주세요. 같은 attempt_id가 중복으로 들어온 행이 꽤 있어서 그거 먼저 걸러내야 하고, 결과는 pandas로 처리해서 parquet으로 저장하면 됩니다.

**t184** (data · terminal) — S-b: 없음; S-0: uasl/sql-optimization-patterns (domain, 2, 27위), uasl/supabase-postgres-best-practices (domain, 1, 20위); 관련 2개: uasl/postgresql-table-design (domain, 2, 1위), uasl/sql-optimization-patterns (domain, 2, 27위)

> downsample sensor_readings to 5-min averages per device_id, write into readings_5m

**t219** (ml · spec) — S-b: uasl/tdd (process, 1, 33위); S-0: uasl/unit-testing (process, 2, 26위); 관련 1개: uasl/unit-testing (process, 2, 26위)

> Goal: add a shipment delay classifier to the logistics backend (Kotlin, Spring Boot 3, Gradle).
> - New module `:delay-model` that loads an XGBoost4J model from S3 at startup (path from `delay.model.uri`)
> - `DelayPredictor.predict(shipment: Shipment): DelayRisk` returning LOW/MEDIUM/HIGH with probability
> - Feature extraction in `ShipmentFeatures.kt` must match the training notebook column order; add a unit test against `src/test/resources/golden_features.csv`
> - Hot-reload the model when a new version lands without restarting the pod
> - Micrometer timer `delay.predict.latency`
> Acceptance: `./gradlew :delay-model:test` passes and prediction stays under 5ms p95 in the JMH benchmark.

## 후보 전문

승자가 없으므로 전문은 파일로 둔다: `select-cands/S-a/SKILL.md`(57줄), `S-b`(59줄), `S-c`(60줄). 모두 60줄 제한 안이다. S-0 대비 diff:

<details><summary>S-a</summary>

```diff
@@ -38,11 +38,12 @@
 2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
    ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
 3. Call `profile_repo` with the repository root once per session (it reads manifest files
-   only) and pass the result as `profile` to `search_skills`.
-4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line
-   summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is
-   often not near the top. Each result has a `token_estimate`: when two fit equally, take
-   the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
+   only) and pass the result as `profile` to `search_skills`. Search once per task.
+4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best
+   first: read all 50 and pick 1–3 that fit this task — the best fit is often not near
+   the top. Each result has a `kind` (domain, process or tooling) and a `token_estimate`:
+   when two fit equally, take the smaller, and keep the set's total under `load_skills`'
+   budget (8000 tokens by default).
 5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
    take the id of the result whose title matches, and put it in `pinned_ids`. A local
    skill folder (one the user named, or a project skill that fits) is pinned as
@@ -54,7 +55,3 @@
 8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
    dropped for the token budget), continue without it and say so.
 
-## Rules
-
-- Never load a skill that `resolve_set` excluded.
-- Do not search again mid-task unless the task changes.
```
</details>

<details><summary>S-b</summary>

```diff
@@ -38,11 +38,14 @@
 2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
    ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
 3. Call `profile_repo` with the repository root once per session (it reads manifest files
-   only) and pass the result as `profile` to `search_skills`.
-4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line
-   summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is
-   often not near the top. Each result has a `token_estimate`: when two fit equally, take
-   the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
+   only) and pass the result as `profile` to `search_skills`. Search once per task.
+4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best
+   first: read all 50 and pick up to 3 that fit this task — the best fit is often not
+   near the top. Do not pick a skill unless you can say in one sentence what its summary
+   changes in this task; often none fits, and then you skip steps 6–7. Each result has a
+   `kind` (domain, process or tooling) and a `token_estimate`: when two fit equally, take
+   the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by
+   default).
 5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
    take the id of the result whose title matches, and put it in `pinned_ids`. A local
    skill folder (one the user named, or a project skill that fits) is pinned as
@@ -54,7 +57,3 @@
 8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
    dropped for the token budget), continue without it and say so.
 
-## Rules
-
-- Never load a skill that `resolve_set` excluded.
-- Do not search again mid-task unless the task changes.
```
</details>

<details><summary>S-c</summary>

```diff
@@ -38,11 +38,15 @@
 2. If no `mcp__skillfetch__*` tool is listed yet, the server is starting: load them with
    ToolSearch (query `+skillfetch`), and search again if it says it is connecting.
 3. Call `profile_repo` with the repository root once per session (it reads manifest files
-   only) and pass the result as `profile` to `search_skills`.
-4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line
-   summaries, best first: read all 50 and pick 1–3 that fit this task — the best fit is
-   often not near the top. Each result has a `token_estimate`: when two fit equally, take
-   the smaller, and keep the set's total under `load_skills`' budget (8000 tokens by default).
+   only) and pass the result as `profile` to `search_skills`. Search once per task.
+4. Call `search_skills` with (a)–(d) as `queries`. It returns 50 one-line summaries, best
+   first: read all 50 and pick up to 3 that fit this task — the best fit is often not
+   near the top. Do not pick a skill unless you can say in one sentence what its summary
+   changes in this task; often none fits, and then you skip steps 6–7. If the user said
+   how to work (test first, minimal diff, plan first), include one process skill; if not,
+   pick a process skill only when no domain skill fits. Each result has a `kind` (domain,
+   process or tooling) and a `token_estimate`: when two fit equally, take the smaller,
+   and keep the set's total under `load_skills`' budget (8000 tokens by default).
 5. If the user named a skill ("use the pdf skill"), call `search_skills` with that name,
    take the id of the result whose title matches, and put it in `pinned_ids`. A local
    skill folder (one the user named, or a project skill that fits) is pinned as
@@ -54,7 +58,3 @@
 8. Do the work. If `load_skills` lists a skill in `errors` (hash mismatch, fetch error,
    dropped for the token budget), continue without it and say so.
 
-## Rules
-
-- Never load a skill that `resolve_set` excluded.
-- Do not search again mid-task unless the task changes.
```
</details>

## 레포 세션용: compact 결과에 kind를 넣는 데 필요한 변경

S-a·S-b·S-c 문구는 결과의 `kind` 필드를 전제한다. 어느 후보를 쓰든 다음이 먼저 필요하다.

1. **`skills.jsonl` 필드.** `kind`를 추가한다. 값은 `"domain" | "process" | "tooling"`, 없으면 `null`.
   - `docs/design/index-format.md` §3 레코드 예시에 `"kind": "process"`를 넣고, 정의 세 줄을 쓴다(`stage6/gen/sys-kind.txt`의 정의 문단).
2. **값 채우기 — 둘 중 하나.**
   - (a) 오버레이: `stage6/kind.jsonl`(1,489행, `{id, kind}`, id는 `source/name@hash`)을 레포 데이터 파일로 넣는다(예: `data/kind.jsonl`). `ingest/build.py`에서 레코드에 병합한다. id가 바뀐 스킬은 같은 `canonical_id`의 라벨을 쓰고, 없으면 `null`이다.
   - (b) extract 필드: `ingest/prompts/extract.md`와 `extract.py`의 `response_schema()`에 `kind`(enum)를 추가한다. prompt fingerprint가 바뀌므로 전체 재추출(Claude API)이 따른다.
   - 이 평가는 (a)의 라벨로 쟀다.
3. **`src/skillfetch/index/search.py` `search()`.**
   - compact 분기(`else:`)의 dict에서 `"tier"` 다음에 `"kind": record.get("kind")`를 넣는다. verbose 분기에도 같은 위치에 넣는다.
   - 모듈 docstring과 index-format §4의 "id, title, one-line summary, tier, token_estimate" 목록에 kind를 더한다.
   - 크기: 쿼리 하나의 compact 결과가 평균 13,026자에서 kind 포함 약 13,976자가 된다(+950자, 이 380태스크 기준). "쿼리당 4k 토큰" 예산 안이다.
4. **테스트.**
   - compact·verbose 결과에 `kind` 키가 있는지(값이 `null`이어도).
   - 픽스처 index 레코드에 kind가 있을 때 그대로 나오는지.
   - 오버레이 병합(a)의 id·canonical_id 대응.
5. **라우터 SKILL.md.** 이 보고서의 판정으로는 바꿀 후보가 없다. kind 필드만 먼저 넣으면 S-0 문구에서는 필드가 설명 없이 보이게 된다. 문구 변경은 다음 규칙 후보가 기준을 넘은 뒤에 한다.

## 비용 (API 환산)

| 항목 | $ |
|---|---|
| kind 라벨 (30회) | 7.3 |
| 선택 S-0 | 18.64 |
| 선택 S-a | 20.37 |
| 선택 S-b | 19.52 |
| 선택 S-c | 19.81 |
| v4 채점 (111회) | 1.08 |
| 합 | 86.72 |

## 알려진 한계

- 후보마다 1회만 생성했다. 같은 후보를 다시 돌릴 때의 변동은 재지 않았다.
- 선택 모델, oracle, kind 라벨러가 모두 Opus 5.5다. 3단계 GPT 교차 라벨의 관련 여부 kappa는 0.482였다.
- v4는 후보들이 고른 스킬만 추가 채점했다. 그래서 고르지 않은 쪽(none)의 정확도에는 유리할 수도, 불리할 수도 있다. 관련 없음 태스크는 89개에서 85개로 줄었다.
- 배치(10태스크/호출) 선택이라 세션 안의 선택과 조건이 같지 않다. 5단계 e2e는 오프라인 선택과 세션 선택이 다르다는 것을 이미 보였다.
