# 8단계 후속 — 공정 비교 보강, 짧은 쿼리 실험, 소스 후보

- 범위: 세션 실행 없음, Skillselion 호출 없음, 외부 API 호출 없음. 규칙은 `DESIGN.md` §4이고, 결과를 보기 전에 기록했다. §4-5 보충은 실행 중에 기록했다.
- 모델 작업: 라벨 확장 채점만 했다(격리 `claude -p` 380회, $29.37).
- 크리덴셜: 이번 작업은 크리덴셜 파일을 읽지 않았다. 동결본 `scripts/ss_client.py`의 `_gh_token()`은 아직 `<credentials file>`를 읽는다. 다음 SS 실행 전에 환경변수만 읽도록 바꿔야 한다(§4-0).

## 라벨 확장 v5-ss-b

v5-ss는 SF R-c를 top-10까지만 채점했다. 그래서 다음 합집합에서 v5-ss 풀에 없던 index 스킬 **25,020개**를 같은 카드·프롬프트로 블라인드 채점했다.

- SF R-c top-50
- kw 단독 top-50
- R-c+kw top-50

| 항목 | v5-ss | v5-ss-b |
|---|---:|---:|
| 새로 채점 (누락 0) | – | 25,020 |
| 그중 등급 ≥2 | – | 696 |
| 관련 있는 태스크 (expect_none 아님, 관련 ≥1) | 323 | 331 |
| index 스킬이 관련인 태스크 | 194 | 270 |

## 1. 공정 비교 보강

### 1a. index가 관련 스킬을 가진 194태스크 (v5-ss) — 최종 로드

| 조건 | 관련 로드 비율 (/194) | 로드한 태스크 | precision (태스크) | precision (스킬) | 로드한 스킬 |
|---|---:|---:|---:|---:|---:|
| SF S-b′ r1 | 0.876 (170) | 186 | 0.914 | 0.800 | 290 |
| SF S-b′ r2 | 0.887 (172) | 186 | 0.925 | 0.819 | 298 |
| SF S-b′ r3 | 0.887 (172) | 183 | 0.940 | 0.821 | 290 |
| **SF S-b′ 3회 평균** | **0.883** | 185 | **0.926** | **0.813** | 292.7 |
| **SS-load-short (kw)** | **0.634** (123) | 175 | **0.703** | **0.703** | 175 |
| SS-load-full | 0.216 (42) | 178 | 0.236 | 0.236 | 178 |

- precision(태스크)는 로드한 태스크 중 관련이 1개 이상인 비율이다. precision(스킬)은 로드한 스킬 중 관련인 비율이다. SS는 한 번에 1개만 로드하므로 두 값이 같다.
- **194의 출처**: v5-ss에서 채점된 index 스킬은 SF R-c top-10과 SF 선택이 거의 전부다(SS 결과가 index 스킬로 합쳐진 경우는 14회). 그래서 이 194는 SF 자기 후보에서 관련이 나온 태스크들이다.
- 참고로 v5-ss-b(SF top-50과 kw 검색까지 채점)의 index 관련 **270태스크**에서 같은 계산을 하면 다음과 같다.

| 조건 (v5-ss-b, n = 270) | 관련 로드 비율 | precision (태스크) | precision (스킬) |
|---|---:|---:|---:|
| SF S-b′ 3회 평균 | 0.635 (171.3) | 0.749 | 0.688 |
| SS-load-short (kw) | 0.615 (166) | 0.680 | 0.680 |
| SS-load-full | 0.207 (56) | 0.229 | 0.229 |

### 1b. SF hit@25·@50

v5-ss-b 기준이다. 결과 수는 SF 50개, SS 최대 25개이고, SS 결과는 모두 채점됐다.

| 분모 | n | SF @10 | SF @25 | SF @50 | SS-q1 @10/@25 | SS-q3 @10/@25 | SS-kw @10/@25 |
|---|---:|---:|---:|---:|---|---|---|
| 관련 있는 태스크 전체 | 331 | 0.453 | **0.656** | 0.767 | 0.423 / 0.444 | 0.541 / 0.559 | 0.828 / **0.837** |
| index 스킬이 관련인 태스크 | 270 | 0.556 | **0.804** | 0.941 | 0.400 / 0.426 | 0.522 / 0.544 | 0.837 / **0.844** |

v5-ss 하한(미채점 = 무관, n = 323)은 SF @10/@25/@50 0.464 / 0.536 / 0.601, SS-kw @10/@25 0.848 / 0.858이다.

### 1c. 후보 균형 민감도

v5-ss를 그대로 쓰고, SS 검색 후보를 조건마다 상위 10개로 자른 경우다. 로드 스킬과 SF 후보는 그대로 두었고 다시 채점하지 않았다.

| | 전체 풀 | 상위 10 풀 |
|---|---:|---:|
| 태스크당 후보 평균 | 36.8 | 30.7 |
| 관련 쌍 (index / SS) | 380 / 1,832 | 380 / 1,584 |
| 관련 있는 태스크 | 323 | 320 |
| 그중 SS 쪽에만 관련 | 129 | 126 |

| 표 1 | 전체 풀 @1 / @5 / @10 | 상위 10 풀 @1 / @5 / @10 |
|---|---|---|
| SF | 0.201 / 0.381 / 0.464 | 0.203 / 0.384 / 0.469 |
| SS-q1 | 0.235 / 0.409 / 0.433 | 0.237 / 0.412 / 0.438 |
| SS-q3 | 0.303 / 0.508 / 0.554 | 0.306 / 0.512 / 0.559 |
| SS-kw | 0.638 / 0.814 / 0.848 | 0.644 / 0.822 / 0.856 |

SS 검색 결과 수의 중앙값은 9–10개다(`metrics-8.json`). 상위 10으로 잘라도 빠지는 후보는 태스크당 평균 6.1개다.

## 2. 짧은 쿼리 실험 (우리 search_skills, 오프라인)

- 호출은 skillfetch `38dcb69` `search_skills(None, queries=…)`, k = 50, profile 없음이다.
- (a)는 `[kw]`다. (b)는 R-c 4개 + kw로 5질의다.
- `search_skills`는 질의를 4개까지만 받아서(`MAX_QUERIES = 4`), (b)는 session 내부의 `searcher.search_many`를 같은 인자로 직접 불렀다.
- 같은 경로의 R-c 결과는 `search_skills`의 R-c 결과와 380/380 같고, `stage6/gen/results-rc.json`과도 380/380 같다.

| 라벨 | n | 조건 | hit@10 | hit@50 | recall@50 | top-50 중 미채점 |
|---|---:|---|---:|---:|---:|---:|
| oracle v3 | 284 | R-c | 0.754 | 0.930 | 0.808 | 0.486 |
| | | (a) kw | 0.630 | 0.782 | 0.569 | 0.724 |
| | | (b) R-c+kw | 0.771 | 0.937 | 0.823 | 0.496 |
| v5-ss-b (index 스킬) | 270 | R-c | 0.556 | 0.941 | 0.822 | 0 |
| | | (a) kw | 0.578 | 0.800 | 0.594 | 0 |
| | | (b) R-c+kw | 0.622 | 0.944 | 0.852 | 0 |

- **v3 라벨**: kw 단독 top-50의 72.4%가 v3 풀 밖이고 무관으로 처리된다. v3의 kw 숫자는 그만큼 하한이다.
- **v5-ss-b**: 세 조건의 top-50이 모두 채점되어 있다.
- **kw 단독 결과가 0개인 태스크**: t040, t162.
  - t040은 v3·v5-ss-b 모두에서 index 관련 태스크라 위 분모에 들어간다.
  - t162는 v5-ss-b 관련이 SS 쪽에만 있어(index 관련 0, v3 관련 0) 위 분모 밖이다.
- **거절 문장 4태스크**(t311, t317, t327, t330): 모두 trivial·expect_none이라 위 분모에 들어가지 않는다.
  - kw 단독은 4개 모두 결과를 냈다. top-5는 다음과 같다.
    - t311: writing-revision, system-design, docx, cosmos-vulnerability-scanner, storybrand-messaging
    - t317: control-d-automation, design-an-interface, canon, caveman-review, video-editing
    - t327: printing-press-polish, printing-press-catalog, docx, printing-press-output-review, gws-best-practices
    - t330: pdf, motion-canvas, gsap-frameworks, gws-best-practices, five-agent-security-review
  - 4개 모두 R-c+kw의 top-10이 R-c와 다르다.

## 3. 소스 후보

`source-candidates.md`(상위 30)와 `source-candidates.json`(전체)이다.

- **저장소 수**: index 밖 관련 스킬 1,241개는 현재 GitHub 저장소 기준으로 **353개 저장소**에 속한다.
- **공백 56 커버**: 상위 30개가 36/56을 커버한다. 저장소 353개 전체로는 45/56이다.
- **이름만 바뀐 사본**: 옛 저장소명 id와 현재 저장소가 다른 경우로, 43개 저장소에 있다.
  - 예: affaan-m/everything-claude-code → affaan-m/ECC (관련 스킬 35개, id 59개)
  - zhanghandong/rust-skills → actionbook/rust-skills
  - jeremylongshore/claude-code-plugins-plus-skills → jeremylongshore/tons-of-skills-marketplace
- **사본 의심**(같은 owner, 이름 겹침 ≥ 3, Jaccard ≥ 0.5): 0개.
- **라이선스**(353개 저장소): 미확인 211, MIT 79, 루트 LICENSE 없음 32, Apache-2.0 20, unknown 3, BSD-3-Clause 2, proprietary 2, GPL-3.0 2, Unlicense 1, AGPL-3.0 1.
  - "미확인"은 본 실행에서 로드되지 않아 루트 LICENSE를 받지 않은 저장소다. 이번에는 네트워크를 쓰지 않았다.
  - 상위 30개 중 미확인은 0이다. 30개 모두 본 실행에서 로드된 적이 있는 저장소다.
- **상위 5개**(관련 스킬 수 기준):

| 저장소 | 관련 스킬 | 공백 56 | 라이선스 |
|---|---:|---:|---|
| claude-dev-suite/claude-dev-suite | 40 | 2 | MIT |
| bobmatnyc/claude-mpm-skills | 38 | 2 | MIT |
| affaan-m/ECC | 35 | 9 | MIT |
| aj-geddes/useful-ai-prompts | 29 | 4 | MIT |
| CharlesWiltgen/Axiom | 23 | 5 | MIT |

## 4. GPT 60

`blind-ss-60.jsonl`(60태스크, 2,270행)은 바꾸지 않았다.

- `scripts/gpt_kappa_8.py`가 준비되어 있다. `gpt-ss-60.jsonl`(task_id, candidate_id, grade, process; 블라인드 행 전부)이 오면 다음을 계산한다.
  - 완전 일치, ±1, 관련 여부 κ, process κ
  - Opus와 교집합 기준 60태스크의 표 1과 최종 로드
- 파일이 없거나 행이 빠지면 실행을 거부한다. 지금은 "gpt-ss-60.jsonl not found"로 멈춘다.

## 한계

- **v5-ss-b 채점 맥락**: 확장 채점은 새 후보만 따로 묶어 태스크마다 1회 채점했다. 기존 v5-ss 후보와 한 목록에서 채점하지 않았다.
- **1a의 분모 출처**: 194는 SF 자기 후보에서 관련이 나온 태스크라 SF 쪽에 유리하게 정해진 분모다. 270(v5-ss-b)도 index 스킬은 SF 검색(R-c, kw, R-c+kw)이 찾은 것만 채점됐다.
- **1c**: 등급을 전체 풀 맥락에서 매긴 값 그대로 쓴다.
- **2의 (b)**: 제품의 `search_skills` 경로로는 부를 수 없는 5질의 조건이다.
- **3의 라이선스**: 저장소 루트 파일 기준이다. 스킬 폴더나 frontmatter 라이선스는 반영하지 않았다.
- **3의 사본 판정**: Skillselion 검색 출력의 `repo:` 줄과 id 저장소명 차이에만 기댄다. 본문 해시로 확인하지 않았다.

## 파일

- 라벨: `oracle-v5-ss-b.jsonl`, `grade-labels-b.json`, `grade-b-summary.json`
- 검색과 지표: `search-kw.json`, `followup-8.json`
- 소스 후보: `source-candidates.md`, `source-candidates.json`
- 스크립트: `scripts/search_kw.py`, `grade_ss_b.py`, `followup_8.py`, `source_candidates.py`, `gpt_kappa_8.py`
