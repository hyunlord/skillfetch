# 9단계 — 스테이징 index 평가 (중간 보고: 새 후보 채점 전)

- 설계: `DESIGN.md` §0–§9(실행 전 고정; §9 선행 조건 수정은 실행 전에 기록)
- 스테이징: `~/github/skillfetch/data/index-staging`(빌드 2026-10-24T11:32:16Z)
- release: `~/.skillfetch/index`(= 레포 `data/index`, 6개 파일 모두 같음)
- 세션 실행 없음. 모델 비용은 S-b′ 선택 1회 **$19.79**다. 예상 $6–19의 상한을 조금 넘었다.
- **§5 새 후보 채점은 예상 $16.09(13,705개)로 $10을 넘어 실행하지 않았다.** 그래서 아래 §4 지표 중 새 레코드가 관련한 값은 잠정이다(미채점 = 무관).

## 1. 선행 조건 (§9) — 통과

| 파일 | release 줄 | 스테이징 줄 | release 줄 중 스테이징에 없음 | release id인데 바이트가 다름 | 새 줄 |
|---|---:|---:|---:|---:|---:|
| skills.jsonl | 1,724 | 2,713 | 0 | 0 | 989 |
| rejected.jsonl | 107 | 141 | 0 | 0 | 34 |

- **constraints.jsonl**:
  - release 스킬 1,692개의 제약 29,880줄은 `fan_out`을 빼면 모두 같다.
  - `fan_out`이 바뀐 제약은 8개로, 모두 false → true다.
  - 새 스킬 제약은 9,900줄이다.
- **조건 밖 파일**(보고만):
  - manifest: 바뀐 키는 sources(5개 추가; release 소스 2개는 그대로), files, counts, licenses, license_sources, redistributable, judged_pairs, built_at.
  - dupgroups: 1 → 5. release 그룹은 그대로다.
  - **pairs.jsonl: release 2,005줄, 스테이징에는 파일이 없다.** pairs는 `resolve_set`의 충돌 판정에만 쓰이고, 검색·오프라인 선택은 읽지 않는다(§9 근거).
- **새 레코드 989개**:
  - 저장소별: affaan-m/ECC 800, dpearson2699/swift-ios-skills 86, ahmed3elshaer/everything-claude-code-mobile 46, actionbook/rust-skills 35, rshankras/claude-code-apple-skills 22
  - tier: B 948, C 41. C는 기본 검색 범위 밖이다.
  - non-canonical: 4
- **ECC 800개의 구성**: 고유 이름은 299개다. 경로별로는 다음과 같다.
  - `skills/` 169
  - `pi/core/skills/` 128
  - 번역 사본: `docs/ja-JP/skills/` 220, `docs/zh-CN/skills/` 177, `docs/es/skills/` 38, `docs/tr/skills/` 38, `docs/zh-TW/skills/` 16, `docs/ko-KR/skills/` 14
  - 번역 사본과 `pi/core` 사본은 본문 해시가 달라 각각 canonical 레코드다.

## 2. 회귀 판정 (§2) — **기각**

고정 라벨·고정 분모다. 새 레코드는 관련으로 치지 않는다.

| 라벨 | n | hit@50 기준 → 스테이징 | Δ | recall@50 기준 → 스테이징 | Δ |
|---|---:|---|---:|---|---:|
| oracle v3 | 284 | 0.930 → 0.813 | **−0.116** | 0.808 → 0.520 | **−0.288** |
| v5-ss-b (index) | 270 | 0.941 → 0.730 | **−0.211** | 0.822 → 0.409 | **−0.413** |

- 네 값 모두 0.01을 넘게 떨어졌다. 기준선은 Stage 8 값과 같은 것을 먼저 확인했다.
- **스테이징 R-c top-50의 구성**:
  - 새 레코드가 태스크당 평균 36.0개(중앙 37)를 차지한다. top-10에서는 평균 7.8개다.
  - 새 레코드 자리 13,696개 중 affaan-m-ecc가 10,634개다.
  - ECC 자리를 경로별로 보면 `pi/core/skills` 2,676, `docs/ja-JP` 1,975, `docs/zh-CN` 1,927, `skills/` 1,455, `docs/tr` 945, `docs/es` 888, `docs/ko-KR` 384, `docs/zh-TW` 384다.

## 3. 라벨 이전 (§3)

592행 중 **57행 이전**(해시 19, 이름 38). 새 id 50개로, 14행이 같은 새 id를 나눠 가졌다.

| 이전 안 됨 | 행 | 내용 |
|---|---:|---|
| repo_not_ingested | 477 | 상위 30개 중 25개 저장소가 스테이징에 없다 |
| ambiguous | 41 | 모두 affaan-m/ECC. 같은 이름이 `pi/core`·`docs/<언어>` 사본으로 여럿 있고 모두 canonical이다(예: `clickhouse-io` 5개: ko-KR, pi/core, zh-CN, ja-JP, zh-TW) |
| not_found | 12 | rshankras 11, dpearson2699 1 |
| rejected | 5 | actionbook `rust-refactor-helper` 2행(scan_failed, `hidden.invisible-chars`), ECC `orch-add-feature`(lint `link-outside-skill`), `react-testing` 2행(lint `link-outside-skill`) |

- **rshankras not_found**: 스테이징은 이 저장소에서 `skills/<분야>/SKILL.md` 22개(app-store, testing, swiftui 등)만 넣었다. 매핑 행이 가리키는 하위 스킬(예: `accessibility-generator`, `test-generator`)은 레코드가 없다.

## 4. 지표 (§4) — 잠정

새 후보 채점 전이다. 스테이징 top-50의 13,705개(태스크, 스킬)가 미채점이고, 무관으로 처리했다.

| 지표 | 기준 index | 스테이징 | 확정 여부 |
|---|---:|---:|---|
| index 관련 태스크 (/331) | 270 | **289** | 이전된 라벨만으로 센 하한 |
| 공백 56 중 index 관련 | 17 | **28 (회복 11)** | 하한 |
| R-c hit@10 (각자 분모) | 0.556 (n=270) | 0.412 (n=289) | 잠정 |
| R-c hit@50 (각자 분모) | 0.941 | 0.785 | 잠정 |
| R-c recall@50 (각자 분모) | 0.822 | 0.466 | 잠정 |
| R-c hit@10 / @50 (기준 270 고정) | 0.556 / 0.941 | 0.374 / 0.770 | 잠정 |

S-b′ 선택 1회(스테이징) 대 기준 index 3회(r1–r3):

| | 기준 r1–r3 | 스테이징 r1 | 확정 여부 |
|---|---|---|---|
| none(선택 없음) 태스크 | 117–122 | 96 | 확정 |
| 선택한 스킬 / 그중 새 레코드 | – | 434 / 300 | 확정 |
| **expect_none 40에서 로드** | 6–8 | **2** | 확정 (expect_none은 라벨과 무관) |
| 관련 로드 비율 | 0.630–0.637 | 0.381 | 잠정, 하한 (미채점 선택 267개) |
| precision (태스크 / 스킬) | 0.742–0.758 / 0.680–0.698 | 0.442 / 0.325 | 잠정, 하한 |
| 불필요 로드 (맞는 것 없는 태스크) | 0.264–0.300 (n=110) | 0.385 (n=91) | 잠정 |
| 그 밖의 맞는 것 없는 태스크에서 로드 | 22–26/70 | 33/51 | 잠정 |
| 고정 집합(스테이징 기준 맞는 것 없는 91)에서 로드 | 20–26/91 | 35/91 | 잠정 |
| 관련 태스크에서 등급 ≤1만 로드 | 55–59 | 139 | 잠정 |

- **잠정의 방향**: "맞는 것 없는 태스크"는 새 레코드를 채점하지 않은 상태로 정한 것이다.
  - 새 레코드 중 관련 있는 것이 채점되면, 그 태스크는 맞는 것 없는 쪽에서 빠진다.
  - 거기서 고른 새 레코드도 관련으로 바뀔 수 있다.
  - 그래서 불필요 로드는 줄 수 있고, 관련 로드와 precision은 늘 수 있다.
- **expect_none 40의 로드**(2/40)는 라벨과 무관하게 확정이다.

## 5. 남은 일 (결정 필요)

§5 채점은 **예상 $16.09**(13,705개 × $0.00117)로 $10을 넘어 보류했다. 선택지는 다음과 같다.

| 선택지 | 대상 | 예상 | 확정되는 지표 |
|---|---|---|---|
| (a) 설계대로 전부 | top-50 ∪ 선택 13,705개, 380회 | $16.09 | §4 전부 |
| (b) 선택만 | 미채점 선택 267개, 198회 | 후보 단가로 $0.31. 호출당 고정비가 있어 실제로는 그보다 크다 | 선택 지표의 관련 로드·precision. 단, "맞는 것 없는 태스크" 판정은 top-50 미채점이라 여전히 잠정 |
| (c) 채점 안 함 | – | $0 | 회귀 기각·전제·이전·expect_none 로드만 확정 |

## 파일

- 전제: `precheck.json`
- 검색: `results-rc-staging.json`, `dry/results-rc-baseline.json`
- 회귀: `regress.json`
- 이전: `migration.json`, `oracle-v5-ss-b-s9.jsonl`
- 선택: `select-S-bp-staging.jsonl`(캐시 `stage6/gen/raw/s9-select-S-bp-staging-*`)
- 지표: `metrics-9.json`
