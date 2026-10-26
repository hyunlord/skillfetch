# 재발화 검증 (설계, 실행 전 고정)

작성 2026-10-26. 사용자 지시는 이렇다:
> 재발화 검증(레포 세션이 만든 변형 (a)(b) 사용): Stage Q2의 S 방식(한 세션 4작업, canary 없이)을 지금 라우터 / (a) / (b) × 5회. 작업마다 라우터 발화, 로드한 스킬, 앞 작업 스킬 언급을 기록한다. 판정 기준(실행 전 고정): 사소하지 않은 작업 2·4번 발화율, 사소한 작업 3번 미발화율. 끝나면 보고하고, 이긴 변형으로 Q2 잔존 측정을 한 번 더 돌린다(canary 포함, 5회).

보고는 숫자와 인용만 쓴다. 비용은 API 단가 환산이다. 계기는 Stage Q Q3에서 S(한 세션) 20개 요청이 모두 skillfetch 호출 0이었던 것이다.

## 1. 갈래

| 갈래 | 레포 `sq-mono` 브랜치 | 라우터 | 그 밖 |
|---|---|---|---|
| cur | `sq-r` | 출시 라우터 S-b′, sha256 `3efef1e0…f040` | – |
| a | `sq-rfa` | `assets/router-skill/variants/refire.md`, sha256 `e3402ffb…f9d9aa` | – |
| b | `sq-rfb` | refire.md(a와 같음) | 레포 루트 `CLAUDE.md` = `variants/refire-CLAUDE.md`, sha256 `f62aa422…44f4c` |

- **변형 출처**: skillfetch 브랜치 `feat/router-refire-variants`, 커밋 1b8decf(레포 세션, 병합 전). 사본은 `stageRF/routers/`에 있다.
- **(a)의 차이**: 출시 라우터의 설명과 본문 첫 줄에 "Run it/this again each time a new task arrives in the same conversation; do not reuse the skill choice from an earlier task."만 더했다.
- **(b)의 CLAUDE.md**: Stage 5 V2 한 줄에 같은 재실행 문구를 더한 것이다.
- **커밋**: 브랜치마다 `sq-a` 위에 커밋 하나("chore: add project skill")이고, plumbing으로 만들었다. 사전 점검은 바뀐 파일이 정확히 라우터(+ b는 `CLAUDE.md`)인지 확인한다.
- **서버·index·환경**: Q2와 같다. 서버 3fef3f8, index-staging-4, E1(`--setting-sources project --strict-mcp-config`).

## 2. 실행

- **요청 4개**: Q2 원문(`stageQ/requests.md`) 그대로 쓰되, 작업 1에서 마지막 문장 " For this task, use my local skill at `{CANARY_PATH}`."만 뺀다. canary는 없다.
- **방식**: 한 세션이다. 작업 1은 `claude -p`, 2–4는 `--resume`이다(Q2 S와 같음). 하네스는 `stageQ/scripts/run_q.py`의 job `rf:<cur|a|b>`이고, 출력은 `stageRF-private/`이다.
- **파일럿**: rf:a, rf:b 각 1회(태그 p1, 집계 밖).
- **본 실행**: 3 갈래 × 5회(m1–m5) = 15세션(요청 60개)이다. 순서는 seed "rf"로 섞고 4병렬이다.
- **잔존 재측정**: 이긴 갈래가 있으면 job `rfc:<갈래>`로 5세션을 더 돌린다(Q2 S와 같이 canary 포함, m1–m5). 결과는 Stage Q의 Q2 S·C와 한 표로 낸다.

## 3. 기록과 판정 기준 (실행 전 고정)

- **요청마다 기록**:
  - 라우터 발화: Skill 도구로 `skillfetch-router`를 불렀거나 skillfetch MCP를 한 번이라도 호출함
  - skillfetch 호출(이름별), 로드한 스킬
  - 앞 작업 스킬 언급: 앞 작업에서 로드한 스킬 이름이 이 요청의 최종 답이나 diff에 나오는데, 이 요청에서는 로드하지 않음
  - 턴, API 단가 환산
- **기준**:
  - 사소하지 않은 작업 2(Rust)·4(Python) 발화율: 갈래마다 10개 요청 중
  - 사소한 작업 3(README 오타) 미발화율: 갈래마다 5개 중
  - 작업 1 발화는 보고만 한다.
- **이긴 변형**: a, b 중 2·4 발화 수가 더 많은 쪽이다. 단, 다음 두 조건을 모두 맞아야 한다.
  - 3 미발화 ≥ 4/5
  - 2·4 발화 수가 cur보다 많음
  - 동률이면 3 미발화가 더 많은 쪽, 그다음 세션당 평균 API 단가 환산이 더 낮은 쪽이다.
  - 맞는 갈래가 없으면 "이긴 변형 없음"으로 보고하고 잔존 재측정은 돌리지 않는다.
- 계산은 `stageRF/scripts/metrics_rf.py`가 한다.

## 4. 비용 (API 단가 환산)

- **세션당 약 $1.8**: Q2 S 실측 평균 $1.54에 라우터 호출이 늘어나는 몫을 더했다.
- **추정**:
  - 본 실행 15 × $1.8 = $27.0
  - 잔존 재측정 5 × $1.8 = $9.0
  - 파일럿 2 × $1.8 = $3.6
  - 여유 10% $4.0
  - **합계 약 $44**
- **상한 $50**: 큐는 "쓴 것 + 남은 세션 × 추정 > $50"이면 띄우기 전에 멈추고 보고한다.

## 5. 기록

- 2026-10-26: 변형 받음(sha256 일치 확인), 브랜치 `sq-rfa` 329b9a5, `sq-rfb` 83e2c7f, `run_q.py`에 `rf`/`rfc` job과 `SQ_PRIV` 추가, dry-run 4종(rf:cur, rf:a, rf:b, rfc:a) 통과.
- 2026-10-26: 변형은 skillfetch PR #94(브랜치 `feat/router-refire-variants`, head e5bc2a5, 열림·병합 전)에 들어갔다. head의 `refire.md`·`refire-CLAUDE.md` sha256은 위 고정값과 같다(e3402ffb…, f62aa422…).

## 6. 계획 변경 (2026-10-26, 사용자 결정)

- 파일럿 2회와 본 실행 4회(cur m3·m5, a m4, b m1)를 마친 시점이다. 세션당 API 단가 환산이 약 $3.1(추정 $1.8)이었고, 큐가 상한 $50 투영으로 멈췄다. 쓴 것은 $18.93이다.
  - 비용이 커진 이유: canary가 없으니 cur도 작업 1·2·4에서 라우터를 불렀다. 세션 안의 입력 토큰이 쌓였다(작업 4 입력 52–63만 토큰, Q2 S는 29만).
- 사용자 결정(원문): "지금 라우터만 3세션 더 돌려 n=5로 맞추고(약 $9), 변형 (a)(b)는 여기서 멈춘다. canary 재실행도 하지 않는다. 보고할 것: 지금 라우터의 2·4번 작업 발화율(5회), 3번(사소한 작업) 미발화율. 그리고 Stage Q2의 0/20은 "1번 작업에서 로컬 스킬을 이름으로 지정하면 그 세션 전체에서 라우터가 안 도는" 현상으로 기록하고, Q1 확장에 그 경우를 확인하는 작업 2개(로컬 스킬 지정 → 다음 작업)를 추가한다. 그다음 Q1 확장으로 넘어간다."
- 그래서 §3의 "이긴 변형" 판정과 잔존 재측정은 하지 않는다. a·b는 각 1회 결과를 기록으로만 보고한다.
