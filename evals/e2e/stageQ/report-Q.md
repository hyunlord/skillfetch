# Stage Q 보고 — 정성 평가 라운드 (Q1–Q6)

실행 2026-10-26. 설계와 실행 전 고정 항목은 `stageQ/DESIGN.md`(해시 `stageQ/FROZEN.sha256`)에 있다. Stage Q에는 release 게이트가 없다. 이 보고에는 숫자와 인용만 적는다. 비용은 구독 사용량을 API 단가로 환산한 값이다.

- **조건**: 켬 = 라우터 S-b′ + skillfetch MCP(index-staging-4, 서버 3fef3f8). 끔 = 라우터·MCP 없음. 환경은 E1(프로젝트 설정만)이다.
- **갤러리**(Q1): `stageQ/gallery/stageQ-gallery.html`

## 0. 실행 요약

| 항목 | 세션 | 요청 | 비고 |
|---|---:|---:|---|
| Q1 켬·끔 | 24 | 24 | 6 태스크 × 2 조건 × 2회 |
| Q2 S(한 세션, `--resume`) | 5 | 20 | |
| Q2 C(대조, 작업마다 새 세션) | 20 | 20 | |
| Q2 S-B | 0 | 0 | **조건 불충족으로 실행 안 함**(§2) |
| Q5 사소한 작업 + 이름 지정 | 16 | 16 | |
| Q6 (c) 본문 가져오기 차단 | 6 | 6 | |
| 파일럿 | 8 | 8 | 집계에 넣지 않음 |

- **API 단가 환산 합계 $48.87**(상한 $80). 내역:
  - 준비: R-c 쿼리 $0.10, Q4 사전 규칙 140개 $6.56
  - 사후 규칙 2개: $0.08
  - 파일럿: $4.63
  - 본 실행: $37.50(Q1 $13.19, Q2 $13.87, Q5 $6.93, Q6 $3.50)
- **판정**: Claude 블라인드 두 패스(p1, p2, 새 하위 에이전트)로 했다. Q1 24개, Q4 규칙 판정은 76개 항목 × 규칙 3개다.
  - Q1 GPT 패키지(`stageQ/judge-package/gpt/`, 24개)는 만들어 두었다. 설계상 선택이다.
- **실행 중 생긴 일**(DESIGN §11 실행 로그):
  - **파일럿 하네스 결함**: 체크가 있는 작업에서 `collect_diff` 이름 오류가 났다. run_s11과 같은 순서로 고쳤고, `--check-test`로 세 작업에서 체크가 도는 것을 확인했다.
  - **Q5 T5 사전 점검 중단**: 레포 `s10-t001`에 `s11-r` 브랜치가 없었다. 같은 방식으로 만든 뒤 남은 14개를 다시 돌렸다.
  - 한도 실패, 결과 없음, 남은 프로세스, index 해시 오류는 0건이다.

## 1. Q1 켜기/끄기

| 태스크 | 조건 | Claude 평균 | p1 | p2 | 체크 | 중앙 턴 | 중앙 벽시계(초) | 중앙 API 단가 환산 | 로드한 스킬 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| d1-landing | 끔 | 3.00 | 2.5 | 3.5 | 2/2 | 6 | 68 | $0.34 | – |
| d1-landing | 켬 | 5.00 | 5 | 5 | 2/2 | 25.5 | 159 | $0.94 | frontend-design ×2, copywriting ×2, next-best-practices |
| d4-email | 끔 | 4.50 | 4.5 | 4.5 | 2/2 | 17 | 91 | $0.47 | – |
| d4-email | 켬 | 4.00 | 4 | 4 | 2/2 | 18 | 104 | $0.65 | email-marketing ×2, frontend-design ×2(판본 2개) |
| s10-t016 | 끔 | 5.00 | 5 | 5 | 2/2 | 4.5 | 40 | $0.23 | – |
| s10-t016 | 켬 | 5.00 | 5 | 5 | 2/2 | 13.5 | 58 | $0.48 | m07-concurrency ×2, rust-testing, rust-patterns |
| s11-t266 | 끔 | 4.50 | 4.5 | 4.5 | 2/2 | 7.5 | 48 | $0.29 | – |
| s11-t266 | 켬 | 5.00 | 5 | 5 | 2/2 | 17.5 | 68 | $0.51 | domain-web ×2, m07-concurrency ×2 |
| s2-api | 끔 | 4.50 | 4.5 | 4.5 | 2/2 | 10 | 92 | $0.48 | – |
| s2-api | 켬 | 5.00 | 5 | 5 | 2/2 | 18.5 | 117 | $0.78 | fastapi-patterns ×2, api-design ×2 |
| s2-data | 끔 | 4.25 | 4 | 4.5 | 2/2 | 12.5 | 120 | $0.64 | – |
| s2-data | 켬 | 4.50 | 4.5 | 4.5 | 2/2 | 18 | 137 | $0.79 | data-analyst-engine ×2 |

- **판정자 일치**(p1–p2): 24개 중 같은 점수 21, 1점 이내 24.
- **디자인 AI 템플릿 체크 항목 수**(p1/p2):
  - d1-landing 끔은 m1 5/5, m2 5/5.
  - d1-landing 켬은 m1 0/0, m2 1/1.
  - d4-email은 네 결과 모두 0/0.
- **갤러리 "차이 정리"에서 옮긴 인용**:
  - d1-landing 끔 m1, p1: "#1 purple gradient headline text and gradient CTA panel, #3 everything centred"
  - d1-landing 켬 m1, p2: "No checklist items: left-aligned hero, rows instead of an icon grid, square buttons, no gradient or emoji."
  - d4-email 끔 m1, p2: "a security note to change the password and delete the mail". 켬 m2, p2: "no security reminder about the mailed password".
  - s11-t266 켬 m2, p2: "Its test proves the limit (blocked while the permit is held, permits returned)." 끔 m1, p1: "no test added for the limit or the offloading".
  - s2-api 끔 m2, p2: "the sqlite connection is opened without check_same_thread=False". 켬 m1, p2: "PATCH of a missing id with a taken url returns 409 instead of 404".
  - s2-data 켬 m1, p2: "the report breaks down orders, units and revenue by status, category, country, product and month". 끔 m1, p2: "gives revenue only (no orders/units)".
  - s10-t016 켬 m1, p2: "Same core change." 네 결과 모두 5점이다. 끔 2회만 README도 고쳤다.

## 2. Q2 잔존 (canary `cnry-q7`)

- **전제**(작업 1): S 5/5, C 5/5 실행에서 canary 파일을 읽었다(Read 또는 `cat`, `pinned_ids` 경로는 0). 작업 1의 R(마지막 줄 `cnry-q7`)은 10/10이다.
  - 작업 1에서 새 파일을 만든 실행은 0이다(기존 `web/` 파일만 수정). 그래서 작업 1의 F는 확인할 대상이 없다.

| 갈래 | 위치 | 전제 있는 실행 | F(첫 줄 표식 / 새 파일) | R | 그 밖의 출현 | canary 다시 읽음 |
|---|---|---:|---:|---:|---:|---:|
| S | 2 Rust | 5 | 0 / 5 | 0 | 1 (m5) | 0 |
| S | 3 README 오타 | 5 | 0 / 0 | 0 | 0 | 0 |
| S | 4 Python | 5 | 0 / 13 | 0 | 0 | 0 |
| C | 2 Rust | 5 | 0 / 5 | 0 | 0 | 0 |
| C | 3 README 오타 | 5 | 0 / 0 | 0 | 0 | 0 |
| C | 4 Python | 5 | 0 / 13 | 0 | 0 | 0 |
| S-B | – | – | – | – | – | 실행 안 함(조건 불충족) |

- **S-B 조건**(S 작업 2–4의 F 또는 R 표식): 0건이다. `stageQ-private/sb-condition.json`에 있다.
- **"그 밖의 출현" 1건**(S m5 작업 2 최종 답, 표식 아님): "I didn't apply the canary markers this time. You asked for that skill only for the landing-page task, so `duration.rs` has no `cnry-q7` line. If the convention should apply to all your work, tell me and I'll add it."
- 작업 1의 "그 밖의 출현" 3건(S m4, C m2, C m5)은 답에서 규칙을 설명한 문장이다. 예: C m5 "It says to mark new files with a `cnry-q7` comment, but this task only edited existing files, so no markers were added."

## 3. Q3 작업별 호출 (Q2 기록)

| 갈래 | 위치 | skillfetch 호출한 요청 | search_skills | 로드한 요청 | 로드한 스킬 | 앞 작업 id 재사용 | 로드 없이 앞 스킬 언급 | 중앙 턴 | 평균 API 단가 환산 |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| S | 1 | 0/5 | 0 | 0 | – | – | – | 7 | $0.205 |
| S | 2 | 0/5 | 0 | 0 | – | 0 | 0 | 5 | $0.362 |
| S | 3 | 0/5 | 0 | 0 | – | 0 | 0 | 4 | $0.411 |
| S | 4 | 0/5 | 0 | 0 | – | 0 | 0 | 7 | $0.561 |
| C | 1 | 0/5 | 0 | 0 | – | – | – | 7 | $0.201 |
| C | 2 | 5/5 | 5 | 5 | m06-error-handling ×5, rust-testing ×5, rust-patterns, coding-guidelines | 0 | 0 | 12 | $0.479 |
| C | 3 | 0/5 | 0 | 0 | – | 0 | 0 | 4 | $0.128 |
| C | 4 | 5/5 | 5 | 5 | python-testing ×5 | 0 | 0 | 14 | $0.425 |

- S(한 세션)에서는 20개 요청 모두 skillfetch 호출이 0이었다. 첫 요청(로컬 canary를 지정한 디자인 작업)에서도 라우터를 부르지 않았다.
- C에서는 새 세션의 작업 2(Rust)와 4(Python)가 5/5 라우터를 불렀다. 작업 1(로컬 스킬 지정)과 3(오타)은 0/5였다.
- **S의 0/20 해석**(2026-10-26 재발화 검증 뒤, 사용자 결정으로 기록): canary 없이 같은 4작업을 한 세션에 보낸 재발화 검증(`stageRF/`)에서는 지금 라우터가 작업 2·4에서 발화했다(`stageRF/report-RF.md`). 그래서 이 0/20은 "1번 작업에서 로컬 스킬을 이름으로 지정하면 그 세션 전체에서 라우터가 돌지 않는" 현상으로 기록한다. 이 경우를 확인하는 작업 2개는 Q1 확장(`DESIGN-Q1x.md` §2.1)에 넣었다.
- C 작업 2·4의 호출은 `profile_repo` 5, `search_skills` 5, `resolve_and_load` 4, `resolve_set` + `load_skills` 1이다(위치마다 같음).

## 4. Q4 로드된 스킬의 규칙 준수

- **규칙**: 사전 추출 140개 스킬과 사후 추출 2개(`coding-guidelines`, `frontend-a11y`; 실행 뒤, 결과물을 보기 전)다. 스킬마다 규칙 3개다.
- **항목**: 76개다. 켬 로드 53개(Q1 23, Q2 C 17, Q5 이름 지정 13), 끔 기준선 23개(같은 규칙 묶음을 짝이 되는 Q1 끔 실행에 적용)다.
- **준수율**은 지킴 / (지킴 + 어김)이다.

| 묶음 | p1 지킴 / 어김 / 해당 없음 | p1 준수율 | p2 지킴 / 어김 / 해당 없음 | p2 준수율 |
|---|---|---:|---|---:|
| 켬 전체 | 105 / 17 / 37 | 0.861 | 99 / 20 / 40 | 0.832 |
| Q1 켬 | 41 / 13 / 15 | 0.759 | 40 / 12 / 17 | 0.769 |
| Q1 끔 기준선 | 32 / 17 / 20 | 0.653 | 33 / 17 / 19 | 0.660 |
| Q2 켬(C 작업 2·4) | 36 / 0 / 15 | 1.000 | 32 / 4 / 15 | 0.889 |
| Q5 이름 지정 | 28 / 4 / 7 | 0.875 | 27 / 4 / 8 | 0.871 |

Q1 태스크별 준수율, 켬 / 끔 기준선:

| 태스크 | p1 | p2 |
|---|---|---|
| d1-landing | 0.583 / 0.333 | 0.667 / 0.333 |
| d4-email | 0.700 / 0.600 | 0.700 / 0.600 |
| s10-t016 | 0.889 / 0.800 | 0.857 / 0.833 |
| s11-t266 | 0.778 / 0.750 | 0.778 / 0.750 |
| s2-api | 0.833 / 0.833 | 0.833 / 0.833 |
| s2-data | 1.000 / 1.000 | 1.000 / 1.000 |

- **패스 간 일치**: 규칙 판정 228개 중 같음 217이다. 다른 11개는 kept↔broken 7(p1 kept·p2 broken 5, p1 broken·p2 kept 2), kept↔n/a 4다.
- **다른 판정 11개 중 4개**는 같은 규칙이다(`m06-error-handling` 규칙 2, Q2 C 작업 2의 m2·m3·m4·m5). p1은 kept, p2는 broken이다. p2 인용: `impl std::error::Error for ParseDurationError {}`.
- **같은 패턴 3개**: `m07-concurrency` 규칙 2(Q1 s10-t016 켬 m1·m2, Q5 이름 지정 s10-t016 m2)에서 p1은 kept, p2는 n/a다. 인용: `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {`.

## 5. Q5 건너뛰기와 이름 지정 (켬)

| 작업 | 건너뜀(로드 호출 0) | skillfetch 호출 | 턴 | API 단가 환산 |
|---|---:|---:|---|---|
| T1 s10-t016 주소 7000→7100 | 2/2 | 0 | 6, 6 | $0.154, $0.153 |
| T2 s2-api 버전 0.1.0→0.1.1 | 2/2 | 0 | 4, 4 | $0.136, $0.140 |
| T3 s11-t160 `:8081`→`:8082` | 2/2 | 0 | 8, 7 | $0.168, $0.165 |
| T4 nextjs 페이지 제목 | 2/2 | 0 | 5, 4 | $0.148, $0.141 |
| T5 s10-t001 상수 이름 변경 | 2/2 | 0 | 4, 6 | $0.148, $0.168 |

| 이름 지정 작업 | 지정한 이름이 `pinned_ids`에 | 로드 | 함께 로드 | 체크 | 턴 | API 단가 환산 |
|---|---|---|---|---|---|---|
| s10-t016 + rust-testing | 2/2 (`rust-testing@68e797f602f9`) | 2/2 | rust-patterns, m07-concurrency | 2/2 | 20, 17 | $0.69, $0.58 |
| d1-landing + frontend-design | 2/2 (`anthropics-skills/frontend-design@0a5ff23f1022`) | 2/2 | frontend-a11y ×2, next-best-practices | 2/2 | 31, 29 | $1.25, $1.13 |
| s2-api + fastapi-patterns | 2/2 (`fastapi-patterns@419da9966f07`) | 2/2 | api-design ×2 | 2/2 | 21, 27 | $0.84, $0.92 |

- 이름 지정 6회 모두 `search_skills`를 두 번 불렀다(한 번은 지정한 이름으로).

## 6. Q6 사용자 경험

**(a) 시간과 턴**(Q1, 중앙값, 끔 → 켬)

| 태스크 | 벽시계(초) | 턴 | 입력 토큰 | API 단가 환산 | 첫 skillfetch 호출 턴(켬) |
|---|---|---|---|---|---|
| d1-landing | 68 → 159 | 6 → 25.5 | 163k → 969k | $0.34 → $0.94 | 4, 4 |
| d4-email | 91 → 104 | 17 → 18 | 424k → 680k | $0.47 → $0.65 | 4, 4 |
| s10-t016 | 40 → 58 | 4.5 → 13.5 | 127k → 422k | $0.23 → $0.48 | 4, 4 |
| s11-t266 | 48 → 68 | 7.5 → 17.5 | 151k → 439k | $0.29 → $0.51 | 4, 4 |
| s2-api | 92 → 117 | 10 → 18.5 | 230k → 559k | $0.48 → $0.78 | 4, 4 |
| s2-data | 120 → 137 | 12.5 → 18 | 399k → 595k | $0.64 → $0.79 | 4, 4 |

**(b) 보이는지**(켬에서 스킬을 로드한 요청 28개, 가리기 전 최종 답)

| 묶음 | 요청 | 로드한 스킬 이름이 답에 나옴 | "skill"/"스킬"이라는 말 |
|---|---:|---:|---:|
| Q1 | 12 | 6 | 6 |
| Q2 C | 10 | 4 | 7 |
| Q5 이름 지정 | 6 | 6 | 6 |
| 합 | 28 | 16 | 19 |

- 인용: Q1 s2-api 켬 m1 "작업할 때 skillfetch에서 받은 `fastapi-patterns`와 `api-design` 스킬을 참고했습니다." Q5 s10-t016 m1 "**Tests (red-green-refactor, per the rust-testing skill)**"

**(c) 본문을 가져오지 못할 때**(차단 서버, 6세션)

| 태스크 | 결과 | 시간 초과 | 체크 | 턴(Q1 켬 중앙) | 벽시계 초(Q1 켬 중앙) | 로드 시도 | 로드 오류 |
|---|---|---|---|---|---|---|---|
| s10-t016 m1 / m2 | success / success | 0 | 2/2 | 16, 11 (13.5) | 57, 48 (58) | 1, 1 | 2, 2 |
| s2-api m1 / m2 | success / success | 0 | 2/2 | 17, 19 (18.5) | 122, 113 (117) | 1, 1 | 2, 2 |
| s2-data m1 / m2 | success / success | 0 | 2/2 | 17, 19 (18) | 118, 143 (137) | 1, 1 | 1, 2 |

- 오류 문구(서버): "SKILL.md: fetch failed (URLError: <urlopen error [Errno 61] Connection refused>)".
- 다시 시도(같은 로드 반복)는 0회다.
- 최종 답에서 실패를 알린 실행은 6개 중 5개다(s2-data m1은 언급 없음). 인용:
  - s10-t016 m1: "작업 전에 참고하려던 skill 2개(Rust 동시성, tokio 테스트)는 서버 연결이 거부되어 불러오지 못했고, 그 skill 없이 진행했습니다."
  - s2-api m2: "참고로 skillfetch 스킬은 서버 연결이 거부돼(connection refused) 하나도 불러오지 못해서, 스킬 없이 작업했습니다."
  - s2-data m2: "참고로 작업 전에 skillfetch로 데이터 분석·검증 스킬 2개를 불러오려 했지만 서버 연결이 거부돼서 스킬 없이 진행했습니다."

## 7. 한계

- 태스크마다 2회(Q1, Q5), 5회(Q2)다.
- Q4 규칙은 스킬 본문에서 자동으로 뽑아서, 태스크와 맞지 않는 규칙은 n/a로 판정됐다(켬 159개 중 p1 37, p2 40).
- Q1 GPT 판정은 하지 않았다(선택). 패키지는 준비돼 있다.
- Q2 작업 1이 새 파일을 만들지 않아, F 규칙은 작업 1에서 지켜지는지 확인할 수 없었다(작업 2·4의 새 파일 36개에는 표식 0).

## 8. 파일

- **공개**: `stageQ/`
  - `DESIGN.md`, `requests.md`, `tasks-q5-named.jsonl`, `router-variants/`, `prompts/`
  - `scripts/`: `run_q.py`, `run_queue_q.py`, `extract_q.py`, `redact_q.py`, `build_blind_q.py`, `build_q4.py`, `q4_pre.py`, `q4_post.py`, `unblind_q.py`, `unblind_q4.py`, `metrics_q.py`
  - `judge-package/`, `gallery/`, 이 보고서
- **비공개**: `stageQ-private/`
  - 세션 기록, `requests-m1-m2-m3-m4-m5.jsonl`, `metrics-q.json`
  - 판정 원문과 점수, 키, 가린 답, Q4 규칙 원문, canary
