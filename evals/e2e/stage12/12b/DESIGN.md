# Stage 12b — 팀 공통 규칙 고정(org), Claude Code 기본(N), 전부 넣기(F) (설계, 실행 전 고정)

작성 2026-10-27. **설계만 한다. 세션은 사용자 확인 뒤에 띄운다.** 보고에는 숫자와 인용만 쓴다. 비용은 구독 사용량을 API 단가로 환산한 값이다. 아래 정의와 게이트는 결과를 보기 전에 고정한다. 바꿀 일이 생기면 날짜와 함께 §9에 따로 적는다. Stage 12의 공개 제약(Stage 12 DESIGN §9.1)은 12b에도 그대로 적용된다.

사용자 지시(원문):
> 1. Stage 12b 설계(실행은 내 확인 뒤): 레포 세션이 만드는 org 라우터 변형과 .skillfetch.yaml(Northwind 공통 규칙 4개: changelog, ui-tokens, structured-logging, endpoint-registry)을 nw 레포 두 곳에 넣고, R′(org 변형) × T1–T8·C1–C2 × 3회만 새로 돌린다. A와 O는 Stage 12 결과를 재사용한다. 게이트(실행 전 고정): R′ ≥ O − 15%p, R′ − R ≥ 15%p, 방해 스킬 로드 ≤ R + 2, 중앙 턴 ≤ R + 2. 같은 선택 분석(못 찾음/안 고름/안 지킴)을 다시 낸다. 세션 수와 환산 비용을 추정해서 보고한다.
>
> 2. Stage 12b에 조건 두 개를 추가한다(실행 전 고정):
>    - N(Claude Code 기본): Northwind 스킬 24개(방해 스킬 포함)를 레포 .claude/skills에 그대로 설치하고 라우터·MCP 없이 실행.
>    - F(전부 넣기): 24개 본문을 첫 사용자 메시지 앞에 load_skills 출력 형식으로 전부 넣고 실행.
>
>    R′, N, F × T1–T8·C1–C2 × 3회. A와 O는 Stage 12를 재사용한다. 보고: 조건별 규칙 통과율, 방해 스킬 규칙을 따른 횟수, 중앙 턴, 입력 토큰. N에서는 어떤 스킬을 불러왔는지(Skill 도구 호출)를 R′의 선택 분석과 같은 형식으로 센다. 세션 수와 환산 비용 추정을 보고하고 멈춘다.

## 0. 배경 숫자 (Stage 12 본 실행, T1–T8 규칙 체크 통과율)

| 조건 | 통과 | 비율 | 중앙 턴 | 입력 토큰 중앙값 | 평균 API 단가 환산 |
|---|---|---|---|---|---|
| A | 31/126 | 0.246 | 8 | 152,324 | $0.283 |
| R | 71/126 | 0.563 | 16 | 409,356 | $0.463 |
| O | 117/126 | 0.929 | 9 | 153,760 | $0.284 |

- 입력 토큰은 result 이벤트의 `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`다. A·O·R은 전체 세션이다.
- **R 실패 55개의 출처**: 못 찾음 32, 안 고름 14, 골랐는데 안 지킴 9
  - 못 찾음 32의 스킬: `nw-changelog` 14, `nw-ui-tokens` 9, `nw-structured-logging` 3, `nw-endpoint-registry` 3, `nw-web-i18n` 3(T8-R1)
  - 이 중 29개가 `.skillfetch.yaml`에 넣을 4개 스킬의 항목이다. T8-R1(`nw-web-i18n`) 3개는 4개 목록 밖이다.
- R의 방해 스킬 로드는 30세션 중 1회다(T3 m3 `nw-legacy-migrations`).
- 참고(게이트 아님): R의 T1–T8 실패 55개 중 4개 스킬의 항목은 34개다(못 찾음 29, 안 고름 5). 34개가 모두 통과하고 나머지가 R과 같다면 R′ = 105/126 = 0.833이다. 고정 스킬이 자동 선택 자리를 바꾸면 다른 항목도 달라질 수 있다.

## 1. 조건

| 조건 | 레포 | 라우터·MCP | 첫 사용자 메시지 |
|---|---|---|---|
| A (재사용) | 시작 커밋 | 없음 | 태스크 프롬프트 |
| R (재사용) | `s12-r-<base>` = 시작 커밋 + S-b′ | skillfetch MCP(`index-nw`) | 태스크 프롬프트 |
| O (재사용) | 시작 커밋 | 없음 | 그 태스크의 필요 스킬 본문(`load_skills` 형식) + 프롬프트 |
| **R′** | `s12b-rp-<base>` = 시작 커밋 + org 라우터 변형 + `.skillfetch.yaml` | skillfetch MCP(`index-nw`) | 태스크 프롬프트 |
| **N** | `s12b-n-<base>` = 시작 커밋 + `.claude/skills/<name>/SKILL.md` 24개 | 없음 | 태스크 프롬프트 |
| **F** | 시작 커밋 | 없음 | 24개 본문 전부(`load_skills` 형식) + 프롬프트 |

### 1.1 R′ (org 변형)

레포 세션 회신 2026-10-27. 제품 기능 PR #97(브랜치 `feat/org-baseline`, head 2ee8f77, 미병합)에서 가져온 파일이다.

- **라우터** `router-org.md`, sha256 `3fbc33adac90304235a4407bfcd6420d468ad39b66090c4a7fee3b9eb74ecc27`:
  - PR의 `assets/router-skill/variants/org.md`와 바이트가 같다. Northwind 이름은 없다. 60줄이고, S-b′ 대비 4·5단계만 바뀌었다.
  - 4단계: 맞는 게 없어도 baseline id가 있으면 6–7단계를 건너뛰지 않는다. top 10 안의 `org: true` 결과에서 같은 한 문장 기준으로 **최대 3개를 더** 고를 수 있다. 예산은 8000 토큰 그대로다.
  - 5단계 끝에 "Pin the profile's `baseline` ids."를 더했다.
  - S-b′처럼 `resolve_set` → `load_skills`를 부른다.
- **`.skillfetch.yaml`**, sha256 `2b2ec10e61ee75ef9e129cfea0cbd16f8758b73c12b7234694be1cf76cd61f1e`:
  ```
  org: northwind
  baseline:
    - nw-changelog
    - nw-ui-tokens
    - nw-structured-logging
    - nw-endpoint-registry
  ```
  - index-nw에서 각각 canonical 기록 하나로 풀린다: northwind/nw-changelog@72d8f1872e37, nw-ui-tokens@005cc5740010, nw-structured-logging@161d6f75b1a4, nw-endpoint-registry@6c574e4601ff.
  - nw-orders·nw-web 두 레포에 같은 파일을 둔다. nw-web 태스크에 항목이 없는 스킬(structured-logging, endpoint-registry)도 그대로 둔다.
- **서버**: 라우터가 파일을 직접 읽지 않는다. `profile_repo`가 `.skillfetch.yaml`을 읽어 `org`와 `baseline`(풀린 id)을 돌려준다. profile에 `org`가 있으면 `search_skills`가 그 조직 결과에 `org: true`를 붙인다.
  - c55d561은 둘 다 못 한다. 그래서 R′는 **별도 서버 빌드 `feat/org-baseline@2ee8f77`**을 쓴다.
  - 위치는 `~/skillfetch-e2e-wt/s12b-server/2ee8f77`(커밋 고정)이고, index는 `index-nw` 그대로다.
  - 준비 때 이 빌드가 index-nw를 읽고, `profile_repo`가 baseline 4개를 돌려주는지 확인한다.
- **고정(baseline) 스킬은 3개 한도에 들지 않는다.** 우선순위는 고정이 먼저이고, 그다음 자동 선택 순서다. 8000 토큰을 넘으면 마지막 자동 선택부터 빠진다.
- **브랜치**: `s12b-rp-nw-a`, `s12b-rp-nw-b`다. 시작 커밋 위에 커밋 하나("chore: add project skill")이고, 바뀐 파일은 `.claude/skills/skillfetch-router/SKILL.md`(org 변형)와 `.skillfetch.yaml` 두 개다. 하네스 사전 점검이 이 두 파일과 해시를 확인한다.
- **R과 다른 점은 셋이다**: (1) 라우터 4·5단계, (2) yaml, (3) 서버 빌드. 서버 빌드가 다르므로 R′ − R에는 서버 변경분도 들어간다. 한계에 적는다.
- **방해 스킬과 `org: true`**: 방해 스킬 8개도 Northwind 소속이라 `org: true`가 붙는다. 4단계의 "org 결과 최대 3개 추가"로 방해 스킬이 로드될 수 있다. 게이트 3(방해 로드 ≤ R + 2)이 이것을 잰다.
- 이 변형은 사용자가 레포 세션에 요청한 제품 변형 그대로다. "고정만"(추가 org 선택 없음)을 따로 재려면 다른 변형과 사용자 결정이 필요하다(레포 세션 회신 3).

### 1.2 N (Claude Code 기본)

- 24개 SKILL.md(`stage12-private/northwind-skills/`, FROZEN 해시)를 바이트 그대로 `.claude/skills/<name>/SKILL.md`에 넣는다.
- 브랜치는 `s12b-n-nw-a`, `s12b-n-nw-b`다. 시작 커밋 위 커밋 하나("chore: add project skills")다. 라우터와 MCP는 없다(`mcp-none.json`).
- E1(`--setting-sources project`)은 프로젝트 스킬을 읽는다. Claude Code가 스킬 이름·설명을 모델에 보여 주고, 모델이 Skill 도구로 본문을 불러온다.
- dry run에서 stream-json `init` 이벤트의 스킬 목록에 24개가 다 있는지 확인한다.

### 1.3 F (전부 넣기)

- 24개 본문을 `load_skills` 출력 형식(`## <n>. <title> (<id>)` + 빈 줄 + 본문, 구간 사이 빈 줄)으로 이어 붙여 첫 사용자 메시지 앞에 넣는다. 위치와 형식은 O와 같다.
- **충돌 해소를 거치지 않는다.** `resolve_set`은 방해 스킬을 뺄 수 있는데, F는 "전부"이므로 본문을 index-nw 순서(id 오름차순)대로 모두 넣는다.
  - 본문 바이트는 `load_skills`가 돌려주는 것과 같게 만든다: `read_skill` → body_lines, 제목은 index title.
  - 같은 프롬프트를 모든 태스크에 쓴다(약 4,600 토큰).
- 라우터와 MCP는 없다. 레포는 시작 커밋이다.

### 1.4 공통

- 하네스: `stage12/scripts/run_12.py`(Stage 11 하네스 래퍼, 체크 전 스냅샷 커밋)에 조건 R′·N·F를 더한다. A·R·O의 동작은 바꾸지 않는다.
- 체크: Stage 12에서 고정한 `stage12-private/checks/`를 그대로 쓴다(해시는 Stage 12 DESIGN §11).
- 출력: `stage12-private/runs/<cond>/`이고, 조건 이름은 `Rp`, `N`, `F`다.

## 2. 태스크와 반복

- Stage 12의 10개 태스크(T1–T8 추론 불가, C1–C2 대조), 프롬프트 그대로다.
- **본 실행**: R′·N·F × 10 × 3회 = **90세션**이다. 순서는 반복마다 seed "s12b"로 섞고 4병렬이다.
- **파일럿**: T1·T7 × R′·N·F × 1 = **6세션**이다(집계 밖).

## 3. 게이트 (실행 전 고정, R′만)

T1–T8 규칙 체크 통과율로 본다. A·R·O는 Stage 12 본 실행 값이다.

1. **R′ ≥ O − 15%p**: O 0.929이므로 R′ ≥ 0.779
2. **R′ − R ≥ 15%p**: R 0.563이므로 R′ ≥ 0.713
3. **방해 스킬 로드 ≤ R + 2**: 30세션에서 방해 스킬을 로드한 횟수. R은 1이므로 ≤ 3
4. **중앙 턴 ≤ R + 2**: R은 16이므로 ≤ 18

- 모두 맞으면 "가설에 맞는 결과"로 보고한다. 하나라도 어긋나면 어긋난 항목과 숫자를 그대로 보고한다.
- N과 F는 게이트 없이 숫자만 보고한다.

## 4. 보고 항목

조건 R′·N·F를 새로 재고, A·R·O는 Stage 12 값과 한 표로 낸다.

- **규칙 체크 통과율**: T1–T8, C1–C2 따로. 판정 불가는 분모에서 빼고 따로 센다.
- **방해 스킬 규칙을 따른 횟수**: 세션의 추가 줄에서 방해 규칙 8개의 표식을 센다. 아래 탐지식은 실행 전에 고정하고, 픽스처(규칙을 따른 예·안 따른 예)로 확인한다. 같은 탐지식을 Stage 12 A·R·O에도 적용해 같은 표로 낸다.

  | 스킬 | 표식(추가 줄, `tests/` 제외, `lib/` 포함) |
  |---|---|
  | `nw-payments-errors` | 응답 키 `"err_code"` 또는 `'err_code'` |
  | `nw-data-logging` | `logger.info(json.dumps(` 또는 `logging.info(json.dumps(` |
  | `nw-legacy-migrations` | 새 파일 `migrations/<YYYY>_<MM>_<DD>_<desc>.py` |
  | `nw-mobile-strings` | 새 파일 `strings.xml` |
  | `nw-marketing-analytics` | `gtag('event'` / `gtag("event"` |
  | `nw-payments-ids` | `pay_` 접두사 + `uuid4` (같은 줄 또는 같은 식) |
  | `nw-infra-runbooks` | 새 파일 `runbooks/RB-<NNN>-*.md` |
  | `nw-ml-experiments` | 새 파일 `experiments/<model>-<dataset>-<YYYYMMDD>/…` 또는 `mlflow` import |

  - 세션마다 따른 방해 규칙 수와, 따른 세션 수를 낸다.
  - 방해 규칙을 따른 항목이 같은 영역의 플랫폼 규칙 항목(예: payments-errors ↔ error-responses)을 실패시켰는지도 함께 적는다.
- **중앙 턴**, **입력 토큰**(위 정의, 중앙값과 평균), **평균 API 단가 환산**, 기능 체크.
- **선택 분석**: Stage 12 `stage12/scripts/selection_12.py`와 같은 형식이다.
  - **R′**: 필요 스킬마다 고정(org)으로 로드 / 검색으로 로드 / top 50에 있었는데 안 고름 / top 50에 없음. 실패한 규칙 항목은 안 고름 / 못 찾음 / 골랐는데 안 지킴으로 나누고, 고정으로 로드됐는데 실패한 항목은 따로 센다.
  - **N**: Skill 도구로 부른 스킬(`input.skill`)과 **파일로 읽은 스킬**을 로드로 센다(2026-10-27 파일럿 뒤 정의 확장, 본 실행 전). 파일로 읽은 스킬은 Read/Grep/Glob 경로가 `.claude/skills/<name>/`이거나, `.claude/skills`·`SKILL.md`를 담은 Bash 명령에 나온 이름이다. 두 경로는 따로도 센다. 24개가 모두 목록에 보이므로 "못 찾음"은 없다. 필요 스킬마다 로드 / 안 고름이고, 실패 항목은 안 고름 / 골랐는데 안 지킴이다. 방해 스킬 로드 수와 필요 없는 플랫폼 스킬 로드 수도 낸다.
  - **F**: 모든 스킬이 들어가므로 선택 분석은 없다. 실패 항목은 "넣었는데 안 지킴"이다.
- **T8 체크 거짓 음성(2026-10-27 사용자 지시)**:
  - **원인 정정**: 판정자는 "`lib/`를 안 봐서"라고 적었지만 원인이 아니었다. T8-F1은 `lib/`를 포함한 모든 추가 코드를 본다.
    - 실패한 6세션(Stage 12 A ×3, R ×3)의 API 호출은 모두 `fetchApi<Order[]>('/orders')`, `fetchApi<void>(…/cancel…)`처럼 TypeScript 타입 인자가 붙은 형태다.
    - 체크 정규식 `\bfetchApi\s*\(`는 타입 인자를 허용하지 않는다. O는 `fetchApi(…/cancel…)`(타입 인자 없음)가 있어서 통과했다.
    - T8 규칙 항목은 `_lib._web_added`가 `lib/`를 뺀다. 이것은 사용자가 지적한 대로다.
  - **게이트는 고정된 체크로 계산한다.** 결과마다 T1–T7 줄(T8 제외)을 같이 낸다.
  - **참고 줄** `stage12-private/checks-ref/`는 고정 체크와 두 곳이 다르다:
    - (1) `_lib.WEB_SKIP`에서 `"lib/"`를 뺐다(추가 줄만 보므로 기존 lib 파일은 여전히 안 본다).
    - (2) T8-F1이 `fetchApi<T>(…)`처럼 타입 인자가 붙은 호출도 센다.
  - **재는 방법**: 저장된 결과물의 T8을 모든 조건(Stage 12 A·R·O, 12b R′·N·F)에서 다시 잰다. 세션 diff를 새 clone에 적용 + 커밋하고(`stage12/scripts/recheck_ref_12.py`), 결과는 meta를 바꾸지 않고 `runs/<cond>/T8-<tag>.check-ref/`에 둔다.
  - **검증(실행 전)**: T8 all은 모두 통과, T8 none은 규칙 항목 모두 실패·기능 통과다. 픽스처(취소 호출을 새 `lib/orders.ts`의 `fetchApi<void>(…)`로 옮김)는 참고 체크에서 F1 통과, 고정 체크에서 F1 실패다.
  - **Stage 12 결과(참고 체크)**: T8 규칙 항목은 A 9/15, R 9/15, O 15/15로 고정 체크와 같다. T8-F1은 A 3/3, R 3/3, O 3/3이다(고정 체크 A 0/3, R 0/3, O 3/3).
- **규칙집 판정(보고용, 2026-10-27 사용자 지시)**:
  - **재료**: Stage 12 판정과 같다(diff, 기능 체크, 가린 최종 답, `_context/`). 여기에 판정자에게 "이 팀의 규칙"으로 **Northwind 플랫폼 규칙 16개의 요약**(Stage 12 DESIGN §1.2 표의 "규칙(요지)" 열, 방해 스킬 8개 제외)을 `RULES.md`로 준다.
  - **루브릭** `rubric-s12-rules.md` = `rubric-s12.md`에 다음을 더한 것이다:
    - "팀 규칙(`RULES.md`)을 지키기 위한 변경은 요청 범위 초과로 보지 않는다."
    - "요청하지 않았는데 기존 동작(기존 엔드포인트 응답, 기존 함수의 동작)을 바꾼 것은 점수와 별도로 `기존 동작 변경` 열에 예/아니오로 표시한다."
    - "사내 관례 채점 금지" 문장은 "팀 규칙 준수 여부는 숨은 체크가 따로 잰다. 점수는 종합 품질로 매기되, 팀 규칙을 따른 변경을 감점 사유로 쓰지 않는다"로 바꾼다.
  - **대상**: Stage 12 본 실행 90개 + 12b 본 실행 90개 = 180개다. 태스크마다 한 세트(A·R·O·R′·N·F × 3 = 18개)이고, 판정자마다 새 무작위 코드를 쓴다. Claude 하위 에이전트 p1·p2이고, 판정자는 기존 판정자와 다른 새 에이전트다.
  - **보고**: 조건별 총점·기준 평균과 `기존 동작 변경` 예 수를, 기존 판정(규칙집 없음, Stage 12 90개만)과 나란히 낸다. 12b 결과물의 규칙집 없는 판정은 하지 않는다(사용자 지시 범위 밖).
  - 판정은 API 단가 환산에 넣지 않는다(Claude 하위 에이전트).

## 5. 세션과 비용 추정 (API 단가 환산)

| 항목 | 계산 | 추정 |
|---|---|---:|
| 파일럿 | 6세션 × 약 $0.37(R′·N·F 평균 추정) | $2.2 |
| R′ | 30 × 약 $0.48(Stage 12 R $0.463 + 고정 스킬 4개 본문 약 0.8k 토큰 × 턴) | $14.4 |
| N | 30 × 약 $0.32(A $0.283 + 스킬 목록 약 1k 토큰과 Skill 호출로 받은 본문) | $9.6 |
| F | 30 × 약 $0.31(O $0.284 + 본문 약 4.6k 토큰, 매 호출 캐시 읽기) | $9.3 |
| 다시 돌림 여유 10% | | $3.6 |
| **합계** | **96세션** | **약 $39** |

- **상한 제안: $50.** 큐는 Stage 12 큐(`run_queue_12.py`)와 같은 규칙으로 멈춘다. 즉 쓴 것 + 진행 중 + 남은 세션 × 추정 > 상한이면 띄우기 전에 멈추고 보고한다.
- 시간: 4병렬로 본 실행 약 1시간(체크 포함 약 1.5시간).
- 레포 세션의 org 변형 작업은 모델 호출 없음이다.

## 6. 준비 (사용자 확인 뒤)

1. org 라우터 변형·`.skillfetch.yaml` 받기(완료, §1.1) → 서버 빌드 `feat/org-baseline@2ee8f77` 워크트리를 만든다. 사용자가 PR을 바꾸면 커밋을 다시 고정한다.
2. 브랜치 `s12b-rp-*`, `s12b-n-*`(plumbing)를 만든다. F 프롬프트를 만들어 해시를 고정한다.
3. `run_12.py`에 R′·N·F를 더하고, 사전 점검(바뀐 파일 목록)과 job 목록을 만든다.
4. 방해 규칙 탐지식·픽스처를 고정한다. 확장한 선택 분석 스크립트(고정 로드 구분, N의 Skill 호출)를 Stage 12 R 세션에서 돌려 Stage 12 숫자와 같은지 확인한다.
5. dry run: R′·N·F × T1·T7·C1.
   - N: `init`에 24개 스킬이 있는지 확인한다.
   - F: 첫 메시지에 24개 구간이 있는지 확인한다.
   - R′: 라우터 파일과 yaml이 있는지 확인한다.
6. 파일럿 6세션. 유효성 점검(게이트 아님)은 둘이다. 어긋나면 본 실행 전에 멈추고 보고한다.
   - R′ 두 세션 모두 `resolve_and_load`의 `included`에 org 스킬 4개가 있다.
   - N 두 세션의 init 스킬 목록에 24개가 있다.
7. 본 실행 90세션 → 지표·선택 분석·방해 규칙 → `report-12b.md`

## 7. 한계 (미리 적어 둠)

- `.skillfetch.yaml`의 4개는 Stage 12 결과(못 찾음 목록)를 보고 골랐다. R′는 "어떤 규칙이 팀 공통인지 아는 경우"를 잰다.
- 4개 목록에 `nw-web-i18n`이 없다. T8-R1(Stage 12 R 못 찾음 3개)은 R′에서도 검색에 달려 있다.
- N은 Claude Code의 스킬 노출 방식(이름·설명 목록 + Skill 도구)에 달려 있다. Claude Code 버전을 기록한다.
- F는 방해 스킬 본문도 다 넣는다. 충돌 규칙을 같이 받는 경우다.
- A·O·R은 Stage 12 값을 재사용한다. 시점이 다르다(같은 하네스·index·체크). R′만 서버 빌드가 다르다(feat/org-baseline@2ee8f77, 미병합 PR #97). N·F는 서버를 쓰지 않는다.

## 8. 공개

- Stage 12 DESIGN §9.1과 같다. Northwind 스킬 본문, 레포, 태스크·규칙 항목, `.skillfetch.yaml`, F 프롬프트는 실험이 끝날 때까지 공개하지 않는다(`stage12-private/`).
- org 라우터 변형은 Northwind 이름을 담지 않는다. 출시·sync·sources.yaml에 넣지 않는다.

## 9. 기록

- 2026-10-27 설계 작성. org 변형은 레포 세션에 요청했다(모델 호출 없음, `<repo-session-work>/stage12b/`).
- 2026-10-27 레포 세션 회신 반영(§1.1): 라우터 sha `3fbc33ad…cc27`, yaml sha `2b2ec10e…1f1e`. R′는 서버 빌드 `feat/org-baseline@2ee8f77`이 필요하다. 고정 스킬은 3개 한도 밖이고, top 10 org 결과에서 최대 3개를 더 고를 수 있다.
- 2026-10-27 사용자 승인(상한 $50). R′는 PR #97 제품 변형(2ee8f77) 그대로 쓴다. 고정 전용 변형은 결과가 애매할 때만 따로 묻는다.
- 2026-10-27 실행 전 추가(사용자 지시): §4에 T8 참고 체크와 규칙집 판정을 넣었다.
- 2026-10-27 실행 전 고정:
  - 방해 규칙 탐지(`stage12/scripts/distractor_12.py`)는 `lib/`의 추가 줄도 본다(T8과 같은 빈틈을 피함). 자체 시험 14/14이고, Stage 12 A·R·O 90세션에서 따른 방해 규칙은 0이다.
  - T8 참고 체크의 원인을 정정했다(타입 인자 호출).
- 2026-10-27 실행 준비(모델 세션 없음):
  - **서버**: `~/skillfetch-e2e-wt/s12b-server/2ee8f77`(detached worktree, 2ee8f77c30ad…). 임시 clone에서 `profile_repo`가 `org: northwind`, baseline 4개를 돌려주고 `baseline_unresolved`는 없다. `search_skills`가 Northwind 결과에 `org: true`를 붙인다. 워크트리 상태는 깨끗하다.
  - **브랜치**:
    - nw-orders `s12b-rp-nw-a` b055c5d / `s12b-rp-nw-b` e13e0c0, `s12b-n-nw-a` 6cfb1a2 / `s12b-n-nw-b` d2dc72c
    - nw-web `s12b-rp-nw-a` 6c93fe1 / `s12b-rp-nw-b` 448c18c, `s12b-n-nw-a` 639f8c9 / `s12b-n-nw-b` 95f1934
    - R′는 라우터 + `.skillfetch.yaml` 두 파일, N은 SKILL.md 24개를 더한다.
  - **F 프롬프트** `stage12-private/f-prompt/F.md`: 24구간, 약 5,040 토큰, sha256 f709d2d0…29a9. O 프롬프트와 겹치는 32구간이 바이트 단위로 같다.
  - **하네스** `run_12.py`에 Rp·N·F를 더했다. A·R·O 경로는 그대로다. 이 때문에 Stage 12 `FROZEN.sha256`의 `run_12.py` 줄은 이제 맞지 않는다(Stage 12 실행 때 해시 bf96f031…는 Stage 12 DESIGN §11에 있다). 새 해시는 `FROZEN-12b.sha256`에 있다.
  - **큐** `run_queue_12b.py`: 상한 $50, Rp·N·F 세션만 센다. job 목록은 `jobs12b-{pilot,main}.txt`(seed "s12b")다.
  - **dry run 9개**(T1·T7·C1 × Rp·N·F)에서 clone, 라우터, MCP, 첫 메시지가 맞다.
  - **분석 스크립트**: `distractor_12.py`, `selection_12b.py`, `tokens_12.py`, `recheck_ref_12.py`, `checks-ref/`. `selection_12b.py`를 Stage 12 R에 돌리면 Stage 12 숫자와 같다(실패 14/32/9, 방해 1).
  - `stage12-private/FROZEN-12b.sha256` 70개, 모두 OK다.
- 2026-10-27 파일럿 6세션(API 단가 환산 $2.76):

  | 조건 | T1 규칙 | T7 규칙 | 기능 | 턴 | 로드 |
  |---|---|---|---|---|---|
  | R′ | 8/8 | 5/5 | 3/3, 2/2 | 18, 19 | 고정 4개 둘 다. T1에 방해 `nw-legacy-migrations` 1 |
  | N | 8/8 | 5/5 | 2/3, 2/2 | 12, 10 | Skill 도구 호출 0. Bash `cat .claude/skills/<name>/SKILL.md`로 T1 11개, T7 8개 |
  | F | 8/8 | 5/5 | 2/3, 2/2 | 6, 12 | – |

  - 유효성 점검: R′ 두 세션 모두 `included`에 org 4개가 있다. N 두 세션의 init `skills`·`slash_commands`에 Northwind 24개가 있다. 둘 다 맞다.
  - N은 Skill 도구를 쓰지 않고 SKILL.md를 파일로 읽었다. 그래서 위와 같이 N 로드 정의를 넓혔다(`selection_12b.py`). Stage 12 R 숫자는 그대로 재현된다.
- 2026-10-27 본 실행 90/90 완료(API 단가 환산 합계 $40.94). 게이트 4개 모두 맞음(`stage12b/report-12b.md`).
- 2026-10-27 실행 뒤 분석 스크립트 수정: `selection_12b.py`가 `nw-$s` 반복(접두사 없는 이름 목록)을 세게 했다. N T1 m3이 0 → 12개가 되었다. 새 해시는 170528afa341…이고, `FROZEN-12b.sha256`의 이 줄만 바뀐다. 체크·하네스·job 목록은 그대로다.
- 2026-10-27 규칙집 판정 완료(새 판정자 6명, 180개 × 2). 판정자 일치는 같은 점수 151/180, 1점 이내 180/180이다. `기존 동작 변경`은 T4 3/18이고 나머지는 18/18이다.
- 2026-10-27 실험 단계 종료(사용자, Stage 12 DESIGN §11 같은 날 기록). 12b 자료는 Stage 12와 함께 공개 정리했다. 이 문서는 공개본에서 `stage12/12b/`로 간다.
