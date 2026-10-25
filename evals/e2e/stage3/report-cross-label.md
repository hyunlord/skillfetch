# GPT 교차 라벨 — 120태스크 (report)

`blind-pool-120.jsonl`의 4,486행에 대해, GPT가 돌려준 `gpt-grades-120.jsonl`과 Opus 라벨(3단계 oracle v2: 2b + 3-0)을 비교했다. `scripts/cross_label.py`, `scripts/table1_intersection.py`.

## 일치율

| 항목 | 값 |
|---|---|
| 돌아온 행 | 4486 |
| 완전 일치 | 0.689 |
| ±1 일치 | 0.975 |
| 등급 kappa (0–3) | 0.353 |
| 관련 여부(≥2) 일치 | 0.884 |
| 관련 여부 kappa | 0.482 |
| process 일치 | 0.919 |
| process kappa | 0.798 |
| 관련(≥2) 행 수 | Opus 308 · GPT 805 |

**관련 여부 kappa 0.482 < 0.6이므로 "두 모델 일치"로 보고하지 않는다.**

혼동행렬(Opus → GPT):

| Opus \ GPT | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | 2732 | 697 | 82 | 0 |
| 1 | 21 | 220 | 397 | 29 |
| 2 | 0 | 11 | 93 | 157 |
| 3 | 0 | 0 | 2 | 45 |

## 표 1 재계산 — 이 120태스크, 세 라벨 버전 (recall, 3단계 순위 그대로)

관련 쌍(expect_none 제외): Opus 301, GPT 794, 교집합 291. 교집합의 process는 둘 다 process로 표시한 것이다.

### Opus — n 전체 91 · 2a 67 · 프로세스 65

| 쿼리 | (i) @10 | (i) @50 | (ii) @10 | (ii) @50 | 프로세스 @10 | 프로세스 @50 |
|---|---|---|---|---|---|---|
| Q1 원문 BM25 | 0.409 | 0.683 | 0.388 | 0.582 | 0.298 | 0.594 |
| Q1 MiniLM | 0.296 | 0.497 | 0.229 | 0.438 | 0.249 | 0.466 |
| Q1 RRF | 0.448 | 0.738 | 0.376 | 0.607 | 0.375 | 0.69 |
| Q2 BM25 | 0.488 | 0.75 | 0.465 | 0.689 | 0.342 | 0.695 |
| Q2 MiniLM | 0.309 | 0.494 | 0.284 | 0.465 | 0.231 | 0.433 |
| Q2 RRF | 0.444 | 0.784 | 0.356 | 0.704 | 0.333 | 0.718 |
| Q3 BM25 | 0.568 | 0.84 | 0.465 | 0.739 | 0.433 | 0.772 |

### GPT — n 전체 105 · 2a 67 · 프로세스 98

| 쿼리 | (i) @10 | (i) @50 | (ii) @10 | (ii) @50 | 프로세스 @10 | 프로세스 @50 |
|---|---|---|---|---|---|---|
| Q1 원문 BM25 | 0.387 | 0.678 | 0.4 | 0.587 | 0.353 | 0.661 |
| Q1 MiniLM | 0.247 | 0.445 | 0.224 | 0.443 | 0.203 | 0.4 |
| Q1 RRF | 0.374 | 0.73 | 0.388 | 0.612 | 0.31 | 0.727 |
| Q2 BM25 | 0.435 | 0.751 | 0.475 | 0.687 | 0.381 | 0.717 |
| Q2 MiniLM | 0.237 | 0.453 | 0.279 | 0.47 | 0.174 | 0.366 |
| Q2 RRF | 0.376 | 0.788 | 0.361 | 0.701 | 0.27 | 0.73 |
| Q3 BM25 | 0.451 | 0.768 | 0.47 | 0.736 | 0.395 | 0.746 |

### 교집합 (둘 다 ≥2) — n 전체 90 · 2a 67 · 프로세스 59

| 쿼리 | (i) @10 | (i) @50 | (ii) @10 | (ii) @50 | 프로세스 @10 | 프로세스 @50 |
|---|---|---|---|---|---|---|
| Q1 원문 BM25 | 0.431 | 0.694 | 0.4 | 0.587 | 0.298 | 0.6 |
| Q1 MiniLM | 0.297 | 0.499 | 0.224 | 0.443 | 0.251 | 0.482 |
| Q1 RRF | 0.46 | 0.738 | 0.388 | 0.612 | 0.388 | 0.706 |
| Q2 BM25 | 0.495 | 0.754 | 0.475 | 0.687 | 0.363 | 0.718 |
| Q2 MiniLM | 0.312 | 0.499 | 0.279 | 0.47 | 0.244 | 0.454 |
| Q2 RRF | 0.46 | 0.775 | 0.361 | 0.701 | 0.344 | 0.729 |
| Q3 BM25 | 0.584 | 0.846 | 0.47 | 0.736 | 0.408 | 0.783 |

## 불일치 상위 10태스크 (|등급 차| 합)

| 태스크 | 작업종류 · 표현 | |차| 합 | Opus 관련 | GPT 관련 | 교집합 | GPT만 관련(일부) | 태스크(앞 120자) |
|---|---|---|---|---|---|---|---|
| t174 | deploy · spec | 28 | 5 | 11 | 5 | claude-native-code-review, guardian, insecure-defaults, launch, tdd-workflow | Goal: over-the-air releases for the React Native hotel check-in app using EAS Update. - Configure `eas.json` channels: ` |
| t083 | tests · korean | 27 | 2 | 17 | 2 | webapp-testing, chrome-devtools, design-harden, echo, judge | Playwright로 결제 페이지 e2e 테스트 추가해줘. `/checkout`에서 쿠폰 적용하고 카드 결제 실패했을 때 에러 토스트 뜨는지, 재시도하면 주문 완료 페이지로 가는지 확인하면 돼. Stripe는 tes |
| t115 | docs · normal | 26 | 0 | 6 | 0 | caveman-review, claude-native-code-review, quill, sentinel, spec-miner | Our soil-moisture sensor firmware crate has about 20 unsafe blocks in src/hal/adc.rs and src/dma.rs with no justificatio |
| t219 | ml · spec | 25 | 1 | 13 | 1 | acceptance-testing, chaos-testing, codenavi, coding-standards, contract-testing | Goal: add a shipment delay classifier to the logistics backend (Kotlin, Spring Boot 3, Gradle). - New module `:delay-mod |
| t236 | security_review · spec | 25 | 8 | 20 | 8 | acceptance-testing, attest, builder, contract-testing, deliberation-debate-red-teaming | Harden JWT validation in our matchmaking gRPC service. File: internal/auth/interceptor.go (unary + streaming interceptor |
| t256 | performance · spec | 25 | 9 | 19 | 9 | browser-automation, documentation-lookup, navigator, next-best-practices, radar | Fix input lag on the fleet tracking admin page (`app/fleet/vehicles/page.tsx`). - `VehicleTable` renders ~2,000 rows at  |
| t240 | security_review · normal | 24 | 3 | 11 | 3 | code-security, debug-root-cause, debugging-strategies, defense-in-depth, insecure-defaults | Our axum wallet service keeps private keys in a struct that derives Debug, and I'm pretty sure one ended up in tracing o |
| t270 | performance · spec | 23 | 4 | 17 | 4 | bolt, coding-guidelines, contract-testing, debug-root-cause, debugging-strategies | Fix consumer lag on the ad-impression topic. The Kotlin consumer in `impressions-ingest` is falling ~2M messages behind  |
| t282 | ui_design · korean | 23 | 0 | 13 | 0 | accessibility-compliance, frontend-design, frontend-patterns, react-patterns, redesign-skill | `src/features/tutor/LessonCalendar.tsx` 주간 뷰에서 수업이 겹치면 카드가 서로 덮어버려요. 겹치는 일정은 Google Calendar처럼 옆으로 나란히 배치되게 바꿔주고, 각 카드 위 |
| t217 | ml · terminal | 23 | 0 | 12 | 0 | ai-expertise-engine, caveman-review, clean-architecture, code-review-excellence, evaluation-rubrics | djl pytorch model for review sentiment in ReviewScoringService, replace regex rules |

10개 모두 Opus만 관련으로 본 스킬이 0개다(Opus 관련 ⊆ GPT 관련).

GPT `reason` 예시(원문 그대로):
- 등급 0: "replicate-automation의 주제는 Django 예약 모델·뷰의 반복 일정 생성과 휴무일 제외와 무관하다."
- 등급 1: "Swift ViewModel의 누락된 Combine import 추가로 빌드 복구에 비해 forecast-premortem의 절차는 과하고 추가 실익이 작다."
- 등급 2: "verification-loop: 빌드·타입·lint·테스트·diff를 함께 확인하는 검증 절차; 운송사 Parquet의 열·시간대 정규화와 중복 제거·멱등 파티션 적재 작업의 수행·검증을 돕지만 세부 적용은 별도로 맞춰야 한다."
