# 8단계 — Skillselion 비교 (본 실행)

이 비교의 벤치마크(380태스크), 라벨 절차(2b 채점 프롬프트), 라우터 문구(R-c 질의, S-b′ 선택)는 모두 skillfetch에 맞춰 만든 것이다. Skillselion은 이 태스크·라벨·문구에 맞춰 조정된 적이 없다. 아래는 지표별 숫자와 한계이며, 어느 쪽이 낫다는 결론은 내리지 않는다.

- 설계: `DESIGN.md` §0–2, §2-추가(본 실행 전에 기록). 해시는 `FROZEN.sha256`.
- 클라이언트: npm `skillselion-mcp@0.9.11` (gitHead `f0127de`). 서버 `serverInfo.version`은 `0.9.10`이다.
- SF: skillfetch `38dcb69`. R-c top-50(`stage6/gen/results-rc.json`)과 S-b′ 선택 3회(`stage6/select-S-bp*.jsonl`, 오프라인 배치)를 쓴다.
- 라벨: oracle v5-ss(`oracle-v5-ss.jsonl`)만 쓴다. v3·v4·v5 계열 라벨은 섞지 않았다. 예외로 56개 공백 태스크의 정의에만 v3를 쓴다(§2 정의 그대로).

## 실행

| 항목 | 값 |
|---|---|
| SS 호출 | 380태스크 × 5조건 = **1,900회**, 오류 0, 순차, 간격 ≥ 1 s, 76.0분 |
| 수요 신호 | `DO_NOT_TRACK=1`, `SK_NO_DEMAND=1` |
| GitHub 토큰 | fine-grained(`github_pat_`), 서버 자식 프로세스 env에만 넣음. 실행 뒤 `stage8/`와 `stage6/gen/raw/` 파일 4,606개에서 토큰 문자열 **0건** |
| kw 질의 생성 | 격리 `claude -p` 380회, $1.80 (`kw-queries.jsonl`) |
| 채점 | 격리 `claude -p` 380회, 후보 14,002개, 누락 0, $18.41 |
| GPT 교차 라벨용 내보내기 | `blind-ss-60.jsonl`: 60태스크(시드 `s8-gpt60`, 작업종류 비례·표현 순환), 2,270행. **GPT 라벨은 아직 없다** |
| 모델 비용 합계 | $20.21 |

- **kw 질의 단어 수**: 2단어 9, 3단어 182, 4단어 180, 5단어 5, 20단어 이상 4.
- **20단어 이상 4개는 질의 대신 거절 문장이 나온 경우다.** 모두 trivial·expect_none 태스크다. 규칙대로 고치지 않고 질의로 넘겼다.
  - t311: "I wouldn't load a skill for this; fixing a one-word typo in a log message is trivial and needs no recipe."
  - t317: "No skill needed. This is a one-character comparison fix (`>` → `<=`) in InventoryService.java, so I'd edit it directly rather than call the tool."
  - t327: "I wouldn't load a skill for this; it's a one-word typo fix. If forced to query: go cli help text"
  - t330: "I wouldn't load a skill for this. It's a one-line fix: add `import androidx.lifecycle.compose.collectAsStateWithLifecycle` to `WateringScreen.kt` and leave every other file alone."
  - 이 4개에서 SS-kw는 결과 5/12/12/2개를 돌려줬다. SS-load-kw는 4개 모두 무언가를 로드했다: `aeon-skill-repair`, `skill-creator`, `10x-cli-guide`, `kotlin-specialist`.

## 라벨 v5-ss

- **후보**: 태스크당 10–67개, 평균 36.8개.
  - 출처는 SS-q1 ∪ SS-q3 ∪ SS-kw 결과, 두 load 조건의 로드 스킬, SF R-c top-10, SF S-b′ 선택 3회다.
  - 카드는 id(`c01`… 불투명 라벨), title(이름), summary(220자 설명)뿐이다. 출처·선택 여부·tags는 넣지 않았다.
- **index id로 합친 SS 결과**: 14회. 같은 저장소·이름에 SKILL.md sha256까지 같은 경우다. 같은 저장소·이름인데 본문이 다른 경우는 0회였다.
- **등급 ≥2**: 2,212개 (태스크, 스킬) 쌍. 우리 index 스킬 380쌍, SS 쪽 스킬 1,832쌍이다.
- **분모**:
  - 관련 있는 태스크 **323**: expect_none이 아니고 v5-ss 관련이 1개 이상.
  - 관련 없는 태스크 **57**: expect_none 40 + v5-ss 관련 0 17.
  - 관련 있는 323 중 관련 스킬이 **SS 쪽에만 있는 태스크가 129**이고, index 스킬이 하나 이상 관련인 태스크가 194다.

## hit@k (관련 있는 태스크 323)

| 조건 | 질의 | @1 | @5 | @10 | 결과 수 중앙값 |
|---|---|---:|---:|---:|---:|
| SF | R-c 4질의 (top-50) | 0.201 (65) | 0.381 (123) | 0.464 (150) | 50 |
| SS-q1 | 태스크 원문 | 0.235 (76) | 0.409 (132) | 0.433 (140) | 10 |
| SS-q3 | R-c 첫 질의 | 0.303 (98) | 0.508 (164) | 0.554 (179) | 10 |
| SS-kw | kw 질의 (2–6단어) | 0.638 (206) | 0.814 (263) | 0.848 (274) | 9 |

보조 분할(§2 고정 지표 밖, `metrics-8-slices.json`):

| 분할 | n | SF @1/@5/@10 | SS-q1 | SS-q3 | SS-kw |
|---|---:|---|---|---|---|
| index 스킬이 관련인 태스크 | 194 | 0.335 / 0.634 / 0.773 | 0.211 / 0.376 / 0.397 | 0.273 / 0.485 / 0.531 | 0.660 / 0.814 / 0.845 |
| 관련 스킬이 SS 쪽에만 있음 | 129 | 0 / 0 / 0 | 0.271 / 0.457 / 0.488 | 0.349 / 0.543 / 0.589 | 0.605 / 0.814 / 0.853 |

top-10 안의 등급 ≥2 개수(380태스크 평균): SF 0.703, SS-q1 1.055, SS-q3 1.334, SS-kw 3.061.

## 최종 로드

| 조건 | 관련 적중 / 관련 태스크 323 | 관련 적중 / 로드한 관련 태스크 | 관련 없는 57에서 1개 이상 로드 | 그중 expect_none 40 |
|---|---|---|---|---|
| SF S-b′ r1 | 0.526 (170) | 0.691 (170/246) | 0.211 (12) | 7 |
| SF S-b′ r2 | 0.533 (172) | 0.688 (172/250) | 0.228 (13) | 8 |
| SF S-b′ r3 | 0.533 (172) | 0.694 (172/248) | 0.193 (11) | 6 |
| SF S-b′ 평균 | 0.531 | 0.691 | 0.211 | 7 |
| SS-load-kw | 0.616 (199) | 0.677 (199/294) | 0.789 (45) | 37 |
| SS-load-full | 0.226 (73) | 0.247 (73/296) | 0.754 (43) | 31 |

- **로드 스킬의 v5-ss 등급(0/1/2/3)**: SS-load-kw 56/75/103/105, SS-load-full 197/65/37/40.
- **보조 분할, 관련 적중률**:
  - index 스킬이 관련인 194: SF r1–r3 0.876/0.887/0.887, SS-load-kw 0.634, SS-load-full 0.216.
  - SS 쪽에만 관련 129: SF 0/0/0, SS-load-kw 0.589, SS-load-full 0.240.
- **§2의 전제 정정**: §2는 "SS-load는 항상 1개"라고 적었다. 실제로는 `load_skill`이 41/380회 아무것도 로드하지 않았다(두 load 조건 각각). 그때의 응답은 "No skill on Skillselion clearly matches … loading one likely won't help — proceed with your own approach"였다.

사례(시드 `s8-quotes` 무작위, 원문 앞부분):
- SS-load-full, 관련 태스크에서 등급 0 로드는 167건이다.
  - t113 "Add usage docs for our pkg/geofence package (point-in-polygon checks for delivery zones), but write them as Ex…" → `asc-cli-usage`
  - t349 "Add a nightly retraining job to the `fraud-scoring` Spring Boot service. It should retrain the XGBoost model…" → `skillopt-sleep`
- SS-load-kw, 관련 태스크에서 등급 0 로드는 40건이다.
  - t031 "Fix duplicate orders on checkout in the Next.js storefront…" (kw "idempotency key api") → `api-key-manager`
  - t056 "Goal: unify the three HTTP helpers in our newsroom CMS…" (kw "typed fetch api client") → `fetch`
- SS-load-kw, expect_none 태스크에서 로드한 경우는 37건이다.
  - t326 "rename prop isOpen -> open on Modal in src/ui/Modal.tsx" (kw "react prop rename refactor") → `react-refactor` (등급 1)
  - t313 "Change the device heartbeat timeout for the IoT hub…" (kw "config constant update") → `force-update` (등급 0)
- SS-load-kw가 관련 스킬을 로드했는데 SF S-b′ 3회가 모두 놓친 태스크는 81건이다.
  - t118 "javadoc for PaymentReconciliationService, reviewer flagged missing @throws on reconcileBatch" → `java-docs` (등급 3)
  - t162 "goreleaser로 `inventory-cli` 바이너리 릴리스할 때 macOS arm64랑 linux amd64만 빌드하고 Homebrew tap에도…" → `add-goreleaser-homebrew` (등급 3)

## 빈 결과 (380태스크, 조건별)

| 조건 | 빈 결과 태스크 | 관련 있는 / 관련 없는 |
|---|---:|---|
| SF R-c top-50 결과 0 | 0 | – |
| SF S-b′ 선택 none (r1/r2/r3) | 122 / 117 / 121 | – |
| SS-q1 | 19 | 14 / 5 |
| SS-q3 | 7 | 6 / 1 |
| SS-kw | 18 | 12 / 6 |
| SS-load-kw (로드 없음) | 41 | 29 / 12 |
| SS-load-full (로드 없음) | 41 | 27 / 14 |

오류(`error`/`isError`)는 모든 조건에서 0이다.

## index 밖 관련 스킬

- **SS 쪽에서 등급 ≥2를 받은 고유 스킬: 1,284개.**
  - **index 밖: 1,241개.** (저장소, 이름) 대응이 없고, 이름이 같은 우리 스킬과 SKILL.md 해시도 다른 경우다.
  - 판정 불가: 43개. 이름이 같은 우리 스킬은 있는데, SS 쪽 SKILL.md를 raw GitHub 경로 후보에서 찾지 못했다.
  - (태스크, 스킬) 쌍으로는 1,778개다.
- **관련 있는 태스크 323 중 index 밖 관련 스킬이 있는 태스크: 310.**
- **56개 공백 태스크**: v3 oracle에서 관련 0이고 expect_none이 아니며 trivial도 아닌 태스크다.
  - index 밖 관련 스킬이 있는 태스크는 **45/56**, 고유 스킬은 179개다.
  - v5-ss에서 관련이 하나라도 있는 태스크는 46/56이고, 그중 index 스킬이 관련인 태스크는 1/56이다.
  - 45개의 작업종류: deploy 9, ml 8, feature 6, performance 6, data 5, docs 3, ci_infra 2, ui_design 2, bugfix 2, tests 1, security_review 1.
- **가장 많은 태스크에서 관련으로 나온 index 밖 스킬**:
  - `rust-testing`: affaan-m/ecc 8, affaan-m/everything-claude-code 7, pproenca/dot-skills 5
  - `multi-stage-dockerfile` (github/awesome-copilot) 6
  - `github-actions-creator` (davila7/claude-code-templates) 6
  - `celery-expert`, `java-spring-boot`, `pytest`, `nextjs-core`, `database-migration` 각 5

## 검증 (로드된 본문 전부, skillfetch `38dcb69` lint · injection scan · scripts · 라이선스)

| 범위 | 로드 | lint 오류 | scan 실패 | scan 경고 | 스크립트 포함 | 번들 파일 있음 | 재배포 가능(허용 라이선스) | 라이선스 unknown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SS-load-kw | 339 | 25 | 8 | 165 | 44 | 198 | 274 | 59 |
| SS-load-full | 339 | 26 | 10 | 164 | 57 | 178 | 275 | 63 |
| 고유 본문 | 518 | 38 | 13 | 246 | 74 | 284 | 422 | 90 |

- **고유 본문의 라이선스**:
  - 종류: MIT 343, Apache-2.0 67, Unlicense 5, BSD-3-Clause 5, MPL-2.0 1, CC0-1.0 1, proprietary 4, AGPL-3.0 1, GPL-3.0 1, unknown 90.
  - 출처: 저장소 루트 LICENSE 341, frontmatter 89, 스킬 폴더 LICENSE 14, 없음 74.
- **scan 실패 규칙(고유 본문)**: exfil.secret-env 11, hidden.invisible-chars 9, privilege.run-as-root 2, privilege.dangerous-flag 2, exfil.ssh-keys 1.
- **lint 오류 규칙**: link-outside-skill 96, broken-link 18, frontmatter-invalid 2, frontmatter-missing 1.

scan 실패 원문(파일:줄):
- `pluginagentmarketplace/custom-plugin-docker#docker-registry` SKILL.md:75 — `echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin` (exfil.secret-env)
- `shaivpidadi/freeride#freeride` SKILL.md:28 — "**OPENROUTER_API_KEY is set.** Check with `echo $OPENROUTER_API_KEY`." (exfil.secret-env)
- `zhanghandong/rust-skills#rust-refactor-helper` SKILL.md:153 외 7줄 — `<U+200B>```rust` (hidden.invisible-chars, 코드 펜스 앞의 zero-width space)
- `martinholovsky/claude-skills-generator#tauri` references/security-examples.md:96 — `"scope": ["$HOME/*"]  // In 1.4.0, this allowed access to ~/.ssh/*` (exfil.ssh-keys)
- `ancoleman/ai-design-components#writing-dockerfiles` SKILL.md:441 — "- Run as root in production" (privilege.run-as-root)
- `price-win/pricewin-skills-hub#pricewin-hotel-deal-finder` SECURITY.md:82 — "**Chromium sandbox stays ON.** `--no-sandbox` is *not* passed by default." (privilege.dangerous-flag)
- `auth0/agent-skills#go-jwt-middleware` SKILL.md:395 — "NEVER add `echo $TEST_TOKEN`, `printf $TEST_TOKEN`, or any command that would print the raw token value" (exfil.secret-env)

위 인용 중 auth0("NEVER add …"), pricewin("sandbox stays ON"), writing-dockerfiles("## Anti-Patterns to Avoid" → "❌ Never:" 목록 안)는 금지·경고 문맥의 문장이 규칙에 걸린 것이다. 규칙은 문맥을 구분하지 않는다.

## 지연 (클라이언트 쪽 도구 호출 시간, 초)

| 조건 | n | 중앙값 | p95 | 최대 |
|---|---:|---:|---:|---:|
| SS-q1 | 380 | 1.133 | 1.971 | 3.011 |
| SS-q3 | 380 | 1.224 | 1.951 | 2.567 |
| SS-kw | 380 | 1.107 | 1.687 | 2.046 |
| SS-load-kw | 380 | 1.507 | 2.255 | 18.713 |
| SS-load-full | 380 | 1.498 | 2.367 | 8.727 |

SF는 이번에 재지 않았다. 3단계 기록으로는 BM25 쿼리당 7.6 ms(중앙)다. 오프라인 Python이라 네트워크 왕복이 없다.

## 한계

- **후보 구성의 비대칭**:
  - 태스크당 SS 쪽 후보는 검색 3조건 결과 최대 25개씩과 로드 2개다. SF 쪽은 R-c top-10과 선택이다.
  - 그래서 v5-ss의 관련 쌍이 SS 쪽 1,832, index 380으로 SS에 치우친다. hit@k는 각자 top-10 안이 모두 채점됐으므로 k ≤ 10에서 양쪽 다 계산 가능하다.
  - 다만 "관련 있는 태스크" 분모의 129개는 SS 쪽 후보로만 생긴 것이다.
- **카드 설명의 출처 차이**: SS 설명은 Skillselion이 쓴 요약(클라이언트가 220자로 자름)이다. SF 설명은 SKILL.md frontmatter `description`을 220자로 자른 것이다. 같은 형식이지만 쓴 주체가 다르다.
- **채점 프롬프트**: 2b 프롬프트 원문은 "id, title, full summary and tags"를 본다고 적혀 있다. 이번 카드에는 tags가 없고 summary가 220자 설명이다.
- **라벨러가 하나다**: Opus 격리 호출 1회씩이다. GPT 60태스크 교차 라벨은 내보내기만 했고 결과가 없다. 7a에서 관련 여부 κ는 0.538이었다.
- **SF 선택은 오프라인 배치다** (`select_cands.py`, 6b와 같은 래퍼). 실제 세션의 라우터가 아니다. SS 쪽은 실제 MCP 도구 출력이다.
- **이름 같은 스킬의 중복**: index 밖 집계는 SS id 단위다. 같은 저장소가 이름만 바뀐 것으로 보이는 경우(affaan-m/ecc와 affaan-m/everything-claude-code의 `rust-testing`)도 따로 센다. 본문 해시로 묶지 않았다.
- **카탈로그 시점**: Skillselion 카탈로그와 순위는 계속 바뀐다. 이 숫자는 2026-10-24 13:46–15:02 KST의 응답이다. SF index는 고정본이다.
- **scan 규칙**: skillfetch scan 규칙(버전 5)은 우리 index 수집용으로 만든 것이다. 문맥(금지문·예시)을 구분하지 않으며, 위 인용에도 그런 경우가 있다.
- **토큰 권한**: fine-grained 토큰의 권한은 API로 조회되지 않아 읽기 전용인지 직접 확인하지 못했다. 클라이언트는 GET에만 썼다.

## 파일

- 원자료: `raw/main.jsonl`(1,900행), `raw/main-server.json`, `raw/tools-list.json`
- 로드 본문: `raw/load/<조건>/<태스크>/` (30 MB)
- 가져온 SKILL.md와 라이선스 캐시: `raw/skillmd-fetch/`, `raw/repo-license/`
- kw 질의: `sys-kw.txt`, `kw-queries.jsonl`, `kw-summary.json`
- 후보와 라벨: `cands.json`, `ss-map.json`, `cands-summary.json`, `grade-labels.json`, `oracle-v5-ss.jsonl`, `grade-summary.json`, `blind-ss-60.jsonl`
- 지표: `metrics-8.json`, `metrics-8-slices.json`, `validate-loads.json`, `validate-summary.json`
- 스크립트: `scripts/ss_client.py`, `ss_parse.py`, `gen_kw.py`, `main_run.py`, `build_cands.py`, `grade_ss.py`, `validate_loads.py`, `metrics_8.py`, `metrics_8_slices.py`
