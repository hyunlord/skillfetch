# 7a — 방향 반영 (#59), 오프라인 (report)

설계와 판정 기준은 `DESIGN.md`(실행 전 고정), 해시는 `FROZEN.sha256`에 있다. 세션 실행은 없고, 모두 격리 `claude -p`다.

## 결론

**진단에서 가장 큰 원인은 (c) 라벨 문제다. DESIGN §4에 따라 후보를 만들지 않고 여기서 멈춘다.**
- 방향대로 안 바뀐 14건 중 11건이 (c) 라벨 문제, 3건이 (b) 선택 문제, 0건이 (a) 검색 문제다.
- 현재 라벨로는 판정 기준 1(≥ 13/16)에 닿을 수 없다. 기준선과 S-b 6회 생성 모두에서 pair03·04·06·09·10은 한 번도 방향대로 바뀌지 않았다. 원인은 그 다섯 쌍의 라벨이 방향을 담지 않거나(04·06·09·10), 한쪽에서 방향에 맞는 스킬이 관련이 아니기 때문이다(03의 b쪽).
- 나머지 11쌍을 모두 맞혀도 11/16이다. 선택이나 검색 문구만 바꿔서는 13/16이 나오지 않는다.

## 1. 진단 — 6a S-b 3회 생성, 방향 쌍 16개 (DESIGN §1–2)

| 분류 | 쌍-회차 (48 중) | 쌍 (다수결) |
|---|---|---|
| 방향대로 바뀜 | 34 | 11 |
| (c) 라벨 문제 | 11 | 4 |
| (b) 선택 문제 | 3 | 1 |
| (a) 검색 문제 | 0 | 0 |

회차별 방향대로 바뀐 쌍: 12 / 11 / 11 (16 중).
"지시와 맞는지" 판정은 격리 1회 호출이고 비용은 $0.22다. 각 쪽에서만 관련인 스킬마다 판정했다(`diag-match.json`).

쌍별:

| 쌍 | 방향 a | 방향 b | 분류 (회차 1/2/3) | a쪽에서만 관련 (방향과 맞음?) | b쪽에서만 관련 (방향과 맞음?) |
|---|---|---|---|---|---|
| pair01 | test-first (TDD) | minimal diff | 바뀜 / 바뀜 / 바뀜 | integration-testing (아니오), python-testing-patterns (아니오), radar (아니오), tdd-workflow (예), tdd (예), test-driven-development (예) | verification-before-completion (아니오) |
| pair03 | accessibility first | visual polish first | (b) / (b) / (b) | accessibility-compliance (예), ui-audit (예) | backend-patterns (아니오) |
| pair04 | no new dependencies | use a well-known library | (c) / (c) / (c) | unit-testing (아니오) | 없음 |
| pair05 | plan before coding | just do it, small change | 바뀜 / 바뀜 / 바뀜 | coding-guidelines (아니오), grill-with-docs (예), tlc-spec-driven (예), writing-plans (예) | 없음 |
| pair06 | backward compatible | breaking change allowed | (c) / (c) / (c) | coding-guidelines (아니오), tdd (아니오), verification-before-completion (아니오) | ripple (아니오) |
| pair07 | test-first (TDD) | minimal diff | 바뀜 / 바뀜 / 바뀜 | python-testing-patterns (아니오), tdd-workflow (예), tdd (예), test-driven-development (예), unit-testing (아니오) | 없음 |
| pair08 | security first | performance first | 바뀜 / 바뀜 / 바뀜 | design-to-code (아니오), redesign-skill (아니오), secure-coding-practices (예), security-review (예), vibe-security (예) | design-optimize (예), interaction-design (아니오), stripe-best-practices (아니오), vercel-react-best-practices (예), web-performance-optimization (예) |
| pair09 | accessibility first | visual polish first | (c) / (c) / (c) | prose (아니오) | 없음 |
| pair10 | no new dependencies | use a well-known library | 바뀜 / (c) / (c) | 없음 | code-review (아니오), find-bugs (아니오), sentinel (아니오), top-100-web-vulnerabilities-reference (아니오) |
| pair11 | plan before coding | just do it, small change | 바뀜 / 바뀜 / 바뀜 | architecture-patterns (아니오), clean-architecture (아니오), domain-analysis (아니오), karpathy-guidelines (아니오), legacy-modernizer (아니오), request-refactor-plan (예), software-design-philosophy (아니오), writing-plans (예) | 없음 |
| pair13 | test-first (TDD) | minimal diff | 바뀜 / 바뀜 / 바뀜 | python-testing-patterns (아니오), radar (아니오), tdd-workflow (예), tdd (예), test-driven-development (예), unit-testing (아니오) | async-python-patterns (아니오) |
| pair14 | security first | performance first | 바뀜 / 바뀜 / 바뀜 | github-workflow-automation (아니오) | 없음 |
| pair15 | accessibility first | visual polish first | 바뀜 / 바뀜 / 바뀜 | accessibility-compliance (예) | 없음 |
| pair17 | plan before coding | just do it, small change | 바뀜 / 바뀜 / 바뀜 | coding-guidelines (아니오), documentation-lookup (아니오), grill-with-docs (예), product-capability (예), ripple (예), system-design (예), writing-plans (예) | 없음 |
| pair19 | test-first (TDD) | minimal diff | 바뀜 / 바뀜 / 바뀜 | python-testing-patterns (아니오), radar (아니오), tdd (예), test-driven-development (예), unit-testing (아니오) | release-it (아니오) |
| pair20 | security first | performance first | 바뀜 / 바뀜 / 바뀜 | auth-implementation-patterns (예), backend-patterns (아니오), security-review (예), vibe-security (예) | next-cache-components (예), nextjs-turbopack (아니오), perf-web-optimization (예), react-patterns (예), taste-skill (아니오) |

## 2. 사례 (원문 인용)

### pair09 — (c) 라벨

선택은 방향을 따랐다. 3회 모두 a쪽(접근성 우선)에서만 `accessibility-compliance`를 골랐다. 그런데 oracle에서 이 스킬은 a쪽(t357) 등급 1이고 b쪽 풀에는 없다. 그래서 "방향대로 바뀜"으로 세지 않는다. a쪽에서만 관련인 스킬은 `prose` 하나이고, 방향과 맞지 않는다.

> **t357** (a, accessibility first): Write the README for `cmd/fleetctl`, our Go CLI for managing the telematics units in our delivery vans. Cover install, auth, and the `units list`, `units reboot` and `firmware push` commands, with example output for each. Accessibility first: use properly ordered headings, alt text on every screenshot, and don't rely on color alone in the sample terminal output.

> **t358** (b, visual polish first): Write the README for `cmd/fleetctl`, our Go CLI for managing the telematics units in our delivery vans. Cover install, auth, and the `units list`, `units reboot` and `firmware push` commands, with example output for each. Make it look polished, with a header image, a command reference table, and collapsible sections for the longer examples.

### pair06 — (c) 라벨

b쪽(호환 깨도 됨)에서만 관련인 것은 `ripple`(변경 영향 분석)이고, a쪽(하위 호환)에서만 관련인 것은 `coding-guidelines`·`tdd`·`verification-before-completion`이다. 방향 판정에서는 넷 다 "아니오"였다. 선택은 3회 모두 a에 `coding-guidelines`·`debug-root-cause`, b에 `ripple`·`verification-loop`이었다.

> **t351** (a, backward compatible): In the ride-sharing iOS app, `TripHistoryView` shows duplicate trips after pull-to-refresh because `TripStore.merge(_:)` appends instead of upserting by `tripId`. Please fix it. Keep it backward compatible: the widget extension uses the `TripStore` public API, so don't change any signatures.

> **t352** (b, breaking change allowed): In the ride-sharing iOS app, `TripHistoryView` shows duplicate trips after pull-to-refresh because `TripStore.merge(_:)` appends instead of upserting by `tripId`. Please fix it. Breaking changes are fine here, so feel free to replace `merge(_:)` with an async `replaceAll(_:)` and update every call site, including the widget extension.

### pair04 — (c) 라벨

a쪽(새 의존성 금지)에서만 관련인 것은 `unit-testing`(a 등급 2, b 등급 1)뿐이다. 방향과 맞지 않는다. b쪽(잘 알려진 라이브러리)에서만 관련인 것은 없다. 선택은 3회 모두 양쪽 `property-based-testing`이었다(a 2, b 3).

> **t347** (a, no new dependencies): Add randomized tests for `parse_nmea_sentence` in `crates/gps-ingest/src/nmea.rs` covering bad checksums, truncated sentences and garbage bytes. Malformed input from our IoT trackers has caused panics in prod twice this month. Don't add any new dependencies; hand-roll a small random input generator inside the test module.

> **t348** (b, use a well-known library): Add randomized tests for `parse_nmea_sentence` in `crates/gps-ingest/src/nmea.rs` covering bad checksums, truncated sentences and garbage bytes. Malformed input from our IoT trackers has caused panics in prod twice this month. Use `proptest` for the generators rather than rolling our own.

### pair03 — (b) 선택 — b쪽은 라벨 공백

a쪽(접근성 우선)은 3회 모두 방향 목표 `accessibility-compliance`(top-50 13위)를 골랐다. b쪽(시각 완성도 우선)은 3회 모두 `web-design`을 골랐는데, 이 스킬은 b쪽(t346) 등급 1이다. b쪽에서만 관련인 것은 `backend-patterns`이고 방향과 맞지 않는다. 규칙상 (b)로 분류되지만, 고른 쪽만 보면 b쪽도 방향을 따랐다.

> **t345** (a, accessibility first): The `/clinics/{id}/availability` handler in `internal/web/availability.go` renders the weekly appointment grid server-side. It takes 1.8s at p95 because it re-queries the `slots` table once per day. Batch it into a single query and cache the rendered page per clinic for 30s. Accessibility first: keep the grid's table headers, the `aria-label`s on slot buttons and the keyboard tab order exactly intact while you optimize.

> **t346** (b, visual polish first): The `/clinics/{id}/availability` handler in `internal/web/availability.go` renders the weekly appointment grid server-side. It takes 1.8s at p95 because it re-queries the `slots` table once per day. Batch it into a single query and cache the rendered page per clinic for 30s. Visual polish first: keep the colored slot states pixel-identical and add a subtle loading skeleton so the page doesn't look broken on a cache miss.

## 3. 기준선 S-b′ (`38dcb69`) 3회 — DESIGN §3의 비교 기준

1회는 6b B-0의 생성이고, 2·3회는 새로 생성했다($18.40, $6.05). 새 풀 밖 선택 3개를 채점했다(관련 0, $0.03; 라벨 v5). 관련 없음 85, 관련 있는 태스크 288.

| 회차 | none-정확도 (85) | hit (288) | 불필요 로드 | 방향대로 바뀐 쌍 (16 중) | 바뀐 쌍 |
|---|---|---|---|---|---|
| 1 | 0.847 | 0.795 | 44 | 11 | 01, 05, 07, 08, 11, 13, 14, 15, 17, 19, 20 |
| 2 | 0.835 | 0.806 | 51 | 10 | 01, 05, 07, 08, 11, 13, 15, 17, 19, 20 |
| 3 | 0.847 | 0.781 | 53 | 10 | 01, 05, 07, 08, 11, 13, 15, 17, 19, 20 |
| 평균 | 0.843 | 0.794 | 49.333 | 10.333 | |

## 4. 다음 단계에 필요한 것 (이 단계 범위 밖)

- pair03·04·06·09·10의 두 쪽 태스크 라벨을 방향 기준으로 다시 매겨야 한다. 예를 들어 "그 쪽의 방향 지시를 다루는 스킬"을 별도 등급으로 매긴다. 그 뒤에 이 진단을 다시 돌린다.
- 라벨을 고친 뒤의 기준(≥ 13/16)은 이번 DESIGN의 정의를 그대로 쓸 수 있다.
- 다만 지금 선택이 이미 방향에 맞게 고르는 사례가 있다(pair09의 `accessibility-compliance`, pair03 b쪽의 `web-design`). 그래서 라벨만 고쳐도 기준선의 수치가 오를 수 있다.

## 비용

방향 일치 판정 $0.22, 기준선 2·3회 생성 $24.45, v5 채점 $0.03. 후보 생성은 하지 않았다.

## 7a-relabel 결과 (DESIGN "7a-relabel")

방향 루브릭(`rubric-direction.md`)으로 방향 쌍 40태스크를 블라인드로 다시 채점했다. 1611행, 풀 밖 선택 0개, 비용 $3.58. 이 40태스크의 관련 쌍은 164개에서 128개가 됐고, 등급이 바뀐 행은 136개다. 블라인드 파일은 `blind-direction-40.jsonl`(GPT용), 라벨은 `oracle-v5-direction.jsonl`이다.

- **새 분모**: 17쌍. 두 쪽 관련 세트가 같아져 빠진 쌍은 pair02, pair12, pair18이고, 새로 들어온 쌍은 pair16이다.
- **기준선 S-b′ 3회**: 방향대로 바뀐 쌍 13 / 12 / 12, 평균 12.333/17 = 0.725. 기준 비율은 13/16 = 0.8125다. **기준에 못 미친다.** none-정확도 0.843, hit 0.791.
- 참고로 6a S-b 3회는 14 / 12 / 13이고, 평균 13.0/17 = 0.765다.
- **다시 돌린 진단(S-b′ 3회, 새 라벨)**: 방향대로 바뀜 37건, (c) 라벨 14건, (b) 선택 0건, (a) 검색 0건. 쌍 다수결로는 바뀜 12, (c) 5이다. 방향 일치는 다시 판정했다($0.19).

| 쌍 | 방향 a | 방향 b | 새 라벨에서 a쪽에서만 관련 | b쪽에서만 관련 | 방향을 다루는 스킬 |
|---|---|---|---|---|---|
| pair04 | no new dependencies | use a well-known library | 없음 | radar | 없음 |
| pair06 | backward compatible | breaking change allowed | coding-guidelines, debug-root-cause | ripple | 없음 |
| pair10 | no new dependencies | use a well-known library | 없음 | code-review | 없음 |
| pair14 | security first | performance first | github-workflow-automation | 없음 | 없음 |
| pair16 | no new dependencies | use a well-known library | 없음 | integration-testing | 없음 |

- 재라벨로 pair03·09(접근성 우선 / 시각 완성도 우선)는 "바뀜"이 됐다.
  - pair09는 a쪽 `accessibility-compliance`가 관련이 됐다.
  - pair03은 b쪽 `web-design`이 관련이 됐다.
- 남은 다섯 쌍은 방향 루브릭으로 다시 매겨도 그 방향을 다루는 스킬이 풀에 하나도 없다.
  - pair04·10·16: 새 의존성 금지 / 잘 알려진 라이브러리
  - pair06: 하위 호환 / 호환 깨도 됨
  - pair14: 보안 우선 / 성능 우선
- 이 다섯 쌍의 각 쪽 풀은 3단계 풀링(2a 카탈로그 선택, BM25, 여러 쿼리의 top-10)과 6a·7a의 모든 선택이다. 그래서 index에 그런 스킬이 없을 가능성이 크다. 다만 풀링 밖의 index 스킬은 확인하지 않았다.

**판정**: 기준선이 기준에 못 미친다. 남은 실패는 모두 (c)이고 (a)·(b)는 0이다.
- 원래 §4는 "라벨 문제가 가장 크면 후보를 만들기 전에 보고하고 멈춘다"이다. 그에 따라 검색·선택 문구 후보는 만들지 않았다.
- 남은 다섯 쌍은 문구로 바꿀 수 있는 선택이 없다. 방향을 다루는 스킬이 풀에 없기 때문이다.
- 다음 단계 후보는 두 가지다.
  - (1) 이 방향들(의존성 정책, 호환성, 보안 대 성능)을 다루는 스킬이 index에 있는지 전체 index에서 찾는다.
  - (2) 분모를 "방향을 다루는 스킬이 풀에 있는 쌍"으로 바꾼 기준을 새로 정한다. 이는 판정 기준 변경이므로 승인이 필요하다.
- GPT 교차 라벨은 `blind-direction-40.jsonl`이 오면 κ를 계산한다(DESIGN "7a-relabel" 5).

## 7a-pool 결과 (DESIGN "7a-pool")

**판정: 기준선 S-b′가 기준을 넘는다(라벨 수정 + 풀 완성만으로 충족). DESIGN에 따라 후보를 만들지 않고 멈춘다.** 라우터 지표 분모(두 쪽 모두 방향 커버된 쌍) 기준으로 방향대로 바뀐 비율이 Opus 라벨에서 1.0(6/6), 교집합 라벨에서 1.0(3/3)이다. 기준은 0.8125다. none·hit은 기준선 자신과의 비교라 하락 0이다.

### 풀 완성

방향 문장 12종 각각의 BM25 top-50을 쌍의 두 태스크 풀에 더했다. 결과 수는 12종 중 10종이 50개이고, "backward compatible" 11개, "minimal diff" 18개다. 새 후보 2976개를 블라인드로 채점했고(40태스크, $6.31), 그중 등급 ≥2가 49개다. 라벨은 `oracle-v5-direction-b.jsonl`이다.

### 기준선 S-b′ 3회 (방향 일치 판정: 등급 ≥2 스킬 전부, 격리 1회)

| 라벨 | 라우터 분모 (두 쪽 커버) | 회차별 바뀜 | 평균 비율 (분모) | 관련 세트가 다른 쌍 전체 | 평균 비율 (전체) | 방향 커버리지 공백 | none (관련 없음) | hit |
|---|---|---|---|---|---|---|---|---|
| Opus (v5-direction-b) | 6 (03, 05, 08, 11, 17, 20) | 6 / 6 / 6 | 6.0 / 6 = 1.0 | 19 | 12.333 / 19 = 0.649 | 13 | 0.841 | 0.788 |
| 교집합 (Opus ∩ GPT) | 3 (03, 08, 20) | 3 / 3 / 3 | 3.0 / 3 = 1.0 | 16 | 12.333 / 16 = 0.771 | 13 | 0.843 | 0.787 |

- 진단(라우터 분모 안): Opus 라벨에서 S-b′ 18건 모두 "바뀜"이다. 교집합 라벨에서는 9건 모두 "바뀜"이다. 6a S-b는 Opus 분모에서 5.67/6이다(b 선택 1건).
- **방향 커버리지 공백(Opus, 13쌍)**: pair01, pair02, pair04, pair06, pair07, pair09, pair10, pair12, pair13, pair14, pair15, pair16, pair19. 한쪽 방향을 다루는 등급 ≥2 스킬이 풀을 넓힌 뒤에도 없는 쌍이다. 쪽별로는 아래와 같다.

| 쌍 | 방향 a | a 커버 스킬 | 방향 b | b 커버 스킬 |
|---|---|---|---|---|
| pair01 | test-first (TDD) | tdd-workflow, tdd, test-driven-development | minimal diff | 없음 |
| pair02 | security first | code-security, pipe | performance first | 없음 |
| pair04 | no new dependencies | 없음 | use a well-known library | 없음 |
| pair06 | backward compatible | 없음 | breaking change allowed | 없음 |
| pair07 | test-first (TDD) | tdd-workflow, tdd, test-driven-development | minimal diff | 없음 |
| pair09 | accessibility first | accessibility-compliance | visual polish first | 없음 |
| pair10 | no new dependencies | 없음 | use a well-known library | 없음 |
| pair12 | backward compatible | 없음 | breaking change allowed | 없음 |
| pair13 | test-first (TDD) | tdd-workflow, tdd, test-driven-development | minimal diff | 없음 |
| pair14 | security first | code-security, pipe | performance first | 없음 |
| pair15 | accessibility first | accessibility-compliance, ui-audit | visual polish first | 없음 |
| pair16 | no new dependencies | 없음 | use a well-known library | 없음 |
| pair19 | test-first (TDD) | tdd-workflow, tdd, test-driven-development | minimal diff | 없음 |

### GPT 교차 라벨 (`gpt-direction-40.jsonl`, 풀 확장 전 1,611행)

| 항목 | 값 |
|---|---|
| 완전 일치 | 0.68 |
| ±1 | 0.98 |
| 등급 κ | 0.388 |
| 관련 여부 κ | 0.538 |
| process κ | 0.723 |
| 관련(≥2) 행 | Opus 128 · GPT 303 · 둘 다 127 |

관련 여부 κ 0.538 < 0.6이므로 교집합 기준 결과를 위 표에 함께 냈다.
- 교집합 라벨은 풀 확장분(Opus만 채점, GPT 없음)을 확인되지 않은 것으로 둔다. 그래서 확장으로 생긴 커버가 빠지고 분모가 3쌍이 된다.
- GPT는 Opus가 관련으로 본 128행 중 127행을 관련으로 봤다. 대신 Opus가 1로 본 행의 대부분을 2 이상으로 올렸다(1→2: 143, 1→3: 13).

### 한계

- 라우터 분모가 작다(Opus 6쌍, 교집합 3쌍). 20쌍 중 13쌍이 방향 커버리지 공백이다. 공백은 "minimal diff"·"just do it"·"visual polish"·"performance first"·의존성 정책·호환성 쪽에 몰려 있다. 이 쌍에서 라우터가 방향을 따를 수 있는지는 이 평가로 알 수 없다.
- 분모 밖 쌍까지 포함한 비율(Opus 0.649, 교집합 0.771)은 기준 0.8125보다 낮다.
