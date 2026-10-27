# Stage 12 — 사내 규칙 스킬(Northwind) 보고

실행 2026-10-27. 설계는 `stage12/DESIGN.md`(기록 §11), 고정 파일은 `stage12-private/FROZEN.sha256`(99개)다. 이 보고에는 숫자와 인용만 적는다. 비용은 구독 사용량을 API 단가로 환산한 값이다. Northwind 스킬 본문, 레포, 태스크·규칙 항목, 판정 패키지는 실험이 끝날 때까지 `stage12-private/`에 두고 공개하지 않는다(DESIGN §9.1).

- **조건**(E1, 서버 c55d561):
  - A: 라우터·MCP 없음
  - R: 출시 라우터 S-b′ + skillfetch MCP(`index-nw` = staging-4 2,785개 + Northwind 24개)
  - O: 그 태스크의 필요 스킬 본문을 첫 사용자 메시지 앞에 `load_skills` 형식으로 넣음
- **태스크**: T1–T8은 레포에서 규칙을 추론할 수 없는 태스크, C1–C2는 대조 태스크다. 10개 × 3조건 × 3회 = 90세션이고, 파일럿은 6세션이다.
- **주 지표**: 숨은 체크의 규칙 항목 통과율이다. 판정 불가는 분모에서 뺀다.

## 1. 게이트 (DESIGN §5, T1–T8 규칙 체크 통과율)

| 조건 | 통과 | 비율 |
|---|---|---|
| A | 31/126 | 0.246 |
| R | 71/126 | 0.563 |
| O | 117/126 | 0.929 |

1. **R − A ≥ 30%p**: 31.7%p. 맞음
2. **R ≥ O − 15%p**: R 56.3%, O − 15 = 77.9%. **어긋남**(21.6%p 모자람)

대조 C1–C2는 A·R·O 모두 24/27(0.889)이다. C1-R6은 9세션 모두 판정 불가였다(세션이 고객 데이터를 만들지 않음).

### 1.1 태스크별 규칙 항목 통과

| 태스크 | A | R | O |
|---|---|---|---|
| T1 환불 엔드포인트 | 2/24 | 14/24 | 24/24 |
| T2 주문 목록(필터·페이지) | 3/18 | 9/18 | 18/18 |
| T3 refund_reason 컬럼 | 3/15 | 12/15 | 15/15 |
| T4 결제 대기 시간 설정 | 8/15 | 12/15 | 15/15 |
| T5 할인 로직 전환 | 3/15 | 6/15 | 8/15 |
| T6 pricing 테스트 | 0/9 | 3/9 | 7/9 |
| T7 주문 내역 페이지 | 3/15 | 6/15 | 15/15 |
| T8 취소 버튼·모달 | 9/15 | 9/15 | 15/15 |
| C1 고객 조회 API | 12/15 | 12/15 | 12/15 |
| C2 설정 페이지 | 12/12 | 12/12 | 12/12 |

### 1.2 보조 지표 (30세션씩)

| 조건 | 기능 체크 | 중앙 턴 | 입력 토큰 중앙값 | 평균 API 단가 환산 |
|---|---|---|---|---|
| A | 72/75 | 8 | 152,324 | $0.283 |
| R | 72/75 | 16 | 409,356 | $0.463 |
| O | 74/75 | 9 | 153,760 | $0.284 |

- 입력 토큰은 `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`다.
- R은 30/30 세션에서 라우터가 발화했고, 각 세션 `search_skills`를 1회 불렀다.

## 2. R 선택 분석 (`stage12/scripts/selection_12.py`, 사용자 요청으로 본 실행 뒤 추가)

### 2.1 필요 스킬(정답 세트) 대 로드

T1–T8의 필요 스킬은 세션 합계 78개다:
- **로드 35**(0.449)
- **top 50에 있었는데 안 고름 14**
- **top 50에 없음 29**

C1–C2를 합치면 96개 중 로드 44, 안 고름 17, 없음 35다.

| 태스크 | 세션별 로드/필요 | 필요 스킬 (3회 결과; 첫 검색 순위) |
|---|---|---|
| T1 | 3/6, 2/6, 3/6 | error-responses 로드 ×3(1–3위) · money 로드 ×3(5–10위) · endpoint-registry 로드 ×2, 안 고름 ×1(16–35위) · public-ids 안 고름 ×3(4–9위) · structured-logging 안 고름 ×3(17–26위) · changelog 없음 ×2, 안 고름 ×1(47위) |
| T2 | 1/4 ×3 | pagination 로드(5–6위) · timestamps 안 고름(7–14위) · endpoint-registry 없음 · changelog 없음 |
| T3 | 2/3 ×3 | migrations 로드(10–23위) · changelog 로드(33–39위) · deploy-checklist 안 고름(5–6위) |
| T4 | 2/3 ×3 | config 로드(1위) · deploy-checklist 로드(4–9위) · changelog 없음 |
| T5 | 1/3 ×3 | feature-flags 로드(2–3위) · structured-logging 없음 · changelog 없음 |
| T6 | 1/1 ×3 | python-tests 로드(7위) |
| T7 | 1/3 ×3 | web-i18n 로드(1–2위) · ui-tokens 없음 · changelog 없음 |
| T8 | 1/3 ×3 | web-analytics 로드(31–45위) · web-i18n 없음 · ui-tokens 없음 |

- **3개 한도**: R은 세션마다 최대 3개를 로드했다. T3 m3만 4개였다(방해 스킬 포함).
- **필요 없는 Northwind 스킬 로드**: T1–T8에서 26회다. 가장 많은 것은 `nw-python-tests`로, T2–T5에서 매 세션 로드됐다.
- **방해 스킬 로드**: 30세션 중 1회(T3 m3 `nw-legacy-migrations`)다. 그 세션의 마이그레이션 파일은 `db/migrations/V20261027_01__add_refund_reason.sql`로, 방해 규칙(`migrations/YYYY_MM_DD_*.py`)을 따르지 않았다.

### 2.2 규칙 실패의 출처 (T1–T8, R 실패 55개)

| 분류 | 수 | 항목 |
|---|---|---|
| 못 찾음 (top 50에 없음) | 32 | changelog 14(T1-R8 ×2, T2-R6, T4-R4, T5-R5, T7-R5 각 ×3) · ui-tokens 9(T7-R3, T7-R4, T8-R5) · structured-logging 3(T5-R3) · endpoint-registry 3(T2-R1) · web-i18n 3(T8-R1) |
| 안 고름 (top 50에 있었는데 로드 안 함) | 14 | T1-R3 ×3, T1-R7 ×3, T1-R5 ×1, T1-R8 ×1, T2-R3 ×3, T3-R3 ×3 |
| 골랐는데 안 지킴 | 9 | T5-R1 ×3("Not found in added lines": flags 호출 없음) · T6-R2 ×3("No new test requests the nw_factory fixture") · T6-R3 ×3("No @pytest.mark.contract in new tests") |

- **로드하지 않고 통과한 항목**: 못 찾음 6(T5-R4 ×3, T8-R2 ×3), 안 고름 3(T1-R4 ×3). 같은 항목을 A도 3회 중 2–3회 통과한다.
- **O도 같은 스킬 항목에서 실패했다**: T5-R3 0/3, T5-R1 1/3, T6-R3 1/3, T5-R2 2/3, T5-R5 2/3. O는 이 스킬들을 직접 받았다. O T5 m2는 코드 변경 없이 질문만 했다(판정 근거 인용 §3).

## 3. 블라인드 판정 (Claude p1·p2, 보고만)

- **패키지**: `stage12-private/judge-package/`, 루브릭 `rubrics/rubric-s12.md`(일반 코드 루브릭, 사내 관례 채점 금지)
- **재료**: diff, 기능 체크 항목, 가린 최종 답이다.
  - 규칙 체크 항목은 넣지 않았다. 판정은 종합 품질만 보고, 규칙 항목의 이름이 회사 규칙을 드러내기 때문이다.
  - 가림(Stage 10 §4.6 규칙)은 R에서 6문장을 지웠고, A·O에는 해당 문장이 없었다.
- **판정자 일치**: 90쌍 중 같은 점수 60, 1점 이내 90이다.
- GPT 판정은 하지 않았다. 패키지 `gpt/`는 만들어 두었다.

| 총점 평균 | A | R | O |
|---|---|---|---|
| T1–T8, p1 | 4.500 | 4.125 | 3.833 |
| T1–T8, p2 | 4.792 | 4.375 | 4.208 |
| T1–T8, 두 판정자 | 4.646 | 4.250 | 4.021 |
| T1–T7, 두 판정자 | 4.738 | 4.357 | 3.976 |
| C1–C2, 두 판정자 | 4.750 | 4.500 | 4.583 |

| 기준 평균(T1–T8, 두 판정자) | A | R | O |
|---|---|---|---|
| 요청 충족 | 4.81 | 4.67 | 4.62 |
| 정확성 | 4.79 | 4.40 | 4.23 |
| 구조·가독성 | 4.60 | 4.19 | 3.79 |
| 검증 | 4.60 | 4.62 | 4.15 |

태스크별 총점(두 판정자 평균, A / R / O):
- T1 4.50 / 4.00 / 4.00
- T2 5.00 / 4.50 / 3.50
- T3 5.00 / 4.33 / 4.17
- T4 4.83 / 4.00 / 4.00
- T5 4.33 / 4.33 / 3.67
- T6 5.00 / 5.00 / 4.50
- T7 4.50 / 4.33 / 4.00
- T8 4.00 / 3.50 / 4.33
- C1 5.00 / 5.00 / 5.00
- C2 4.50 / 4.00 / 4.17

판정 근거 인용(원문):
- T2 O m1(p1, 3점): "커서 목록은 정확하나 기존 POST /orders 타임스탬프 형식을 임의 변경, rate_limit 300을 추측으로 등록"
- T2 O m2(p2, 4점): "Cursor endpoint works with full traversal test, but rewrites existing create_order timestamps outside the request (disclosed)"
- T2 A m1(p1, 5점): "ef4e96d1과 같은 간결한 offset 구현, 테스트 충분, 상태 값·페이지 방식 선택지를 명확히 제시"
- T1 O m3(p1, 4점): "동작과 테스트는 충실하지만 amount_minor 변경, X-Tenant-Id 헤더 임의 도입, 레지스트리·로그 등 요청보다 큰 변경"
- T5 O m2(p2, 2점): "No code: asks for the new rule first, although the requested switch could have been built with a placeholder; useful questions but the deliverable is missing"

**T8 기능 체크 거짓 음성**:
- A 3회·R 3회가 T8-F1("취소 API 호출")에서 `api_call=False`로 실패했다.
  - 원인은 이 6세션의 API 호출이 모두 `fetchApi<Order[]>('/orders')`, `fetchApi<void>(…/cancel…)`처럼 TypeScript 타입 인자가 붙은 형태였기 때문이다. 체크 정규식 `\bfetchApi\s*\(`가 이를 허용하지 않는다.
  - 판정자 회신에는 "`lib/orders.ts`를 거쳐서"라고 적혀 있다. 그러나 T8-F1은 `lib/`도 본다. `lib/`를 빼는 것은 T8 규칙 항목(`_lib._web_added`)이다.
- 판정자 두 명 모두 루브릭대로 체크 결과를 사실로 보고, 이 6개를 요청 충족·총점 4 이하로 매겼다(판정자 회신).
- 체크는 본 실행 전 동결이라 고치지 않았다. 위 표에 T8을 뺀 T1–T7 줄을 함께 적었다.
- **참고 체크**(`stage12-private/checks-ref/`: `lib/` 포함 + 타입 인자 호출 인정, 실행 뒤 만든 사본; stage12b DESIGN §4)로 저장된 T8 9개를 다시 쟀다.
  - T8-F1: A 3/3, R 3/3, O 3/3(고정 A 0/3, R 0/3, O 3/3)
  - T8 규칙 항목: A 9/15, R 9/15, O 15/15로 고정 체크와 같다.

## 4. 결론 (사용자 분석)

- **못 찾음 32개는 모두 작업 설명에 드러나지 않는 팀 공통 규칙이다.** 스킬별로는 `nw-changelog` 14, `nw-ui-tokens` 9, `nw-structured-logging` 3, `nw-endpoint-registry` 3, `nw-web-i18n` 3이다.
  - 5개 스킬 모두 요청 문장이 직접 가리키지 않는 규칙이다. 예: T8 "주문 내역에 취소 버튼을 추가해 주세요…"는 화면 문자열을 언급하지 않는데, T8-R1은 `t()` 사용 항목이다.
  - 앞의 4개(29개 항목)가 Stage 12b `.skillfetch.yaml`의 공통 규칙 목록이다. `nw-web-i18n`(T8-R1, 3개)은 그 목록 밖이다.
- R 실패 55개 중 나머지는 둘이다:
  - **안 고름 14개**: 모두 top 50 안이었고, public-ids 4–9위, deploy-checklist 5–6위, timestamps 7–14위였다.
  - **골랐는데 안 지킴 9개**: feature-flags, python-tests. O도 같은 스킬 항목에서 일부 실패했다.

## 5. 비용과 실행 기록

- **API 단가 환산 합계 $34.97**(상한 $75):
  - index-nw 추출 $1.05(레포 세션, `claude -p` 24회)
  - 검색 점검 쿼리 $0.05
  - 파일럿 $2.21
  - 본 실행 $30.89
  - 사용 한도로 실패한 4세션 $0.77
- **파일럿에서 고친 것**(본 실행 전, DESIGN §11):
  1. 하네스: 체크가 커밋된 HEAD를 읽는데 세션은 커밋하지 않는다. 체크 전 스냅샷 커밋을 더했다.
  2. 체크 `t()` 인정 범위: 같은 파일 래퍼와 import alias. 사용자가 범위를 정했고, 음성 픽스처 3개를 더했다.
  3. 여러 줄 호출 인식.
  - 참조 해답 20개와 픽스처 8개가 28/28 기대대로 나왔다.
  - 파일럿 점수(커밋 수정 전 → 후 → 체크 수정 후): A 0.077 → 0.154 → 0.154, R 0.308 → 0.538 → 0.538, O 0.308 → 0.769 → 1.000.
- **본 실행 중단**: 66번째 job에서 4세션이 "You've hit your org's monthly spend limit"로 harness_fail이 되었다. 다시 로그인한 뒤 같은 job 목록으로 재개했다. 실패 파일은 `runs-hf/`에 남겼다.
- **본 실행 시작 뒤 바뀐 것**: 체크·하네스·job 목록은 없다. 선택 분석, 가림·판정 스크립트는 읽기만 하는 분석이다.

## 6. 한계

- 가상 회사이고 규칙은 우리가 만들었다. 태스크 10개, 3회 반복이다.
- R은 출시 라우터의 "pick up to 3"을 따른다. 가장 잘 고른 3개로 덮을 수 있는 T1–T8 규칙 항목은 42개 중 38개(0.905)다(DESIGN §11).
- Northwind 24개만 다른 추출기(Claude Code 백엔드)로 추출했다. Northwind와 기존 기록 사이 충돌 판정은 하지 않았다(사용자 결정).
- 체크는 정적 패턴과 실행 검사의 조합이다. 확인된 거짓 음성은 둘이다.
  - T8-F1 타입 인자 호출 미인식(§3)
  - 파일럿에서 고친 두 건(§5)
- 가림 뒤에도 최종 답에 "Northwind"·"규칙"·"convention"이 남은 세션은 A 6, O 12, R 19다(Stage 10 규칙의 대상어가 아님).
- 판정은 Claude 하위 에이전트 두 명이다.

## 7. 파일

- **설계·기록**: `stage12/DESIGN.md`
- **하네스·분석**: `stage12/scripts/`
  - 하네스: `run_12.py`, `run_queue_12.py`, `recheck_12.py`
  - 분석: `metrics_12.py`, `selection_12.py`, `redact_12.py`, `build_blind_12.py`, `unblind_12.py`
- **비공개**: `stage12-private/`
  - 결과: `runs/`, `metrics-m.json`, `selection-m.json`, `judging.json`
  - 판정 재료: `judgments/`, `judge-package/`, `keys/`, `redacted/`
  - 고정한 재료: `checks/`, `refs/`, `index-nw/`, `o-prompts/`, `search-check/`
