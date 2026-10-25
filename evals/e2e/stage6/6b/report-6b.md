# 6b — 효과 게이트 결과 (report)

설계와 판정 규칙은 `../DESIGN.md`(§5는 실행 전 고정), 파일럿은 `report-pilot.md`, 해시는 `FROZEN.sha256`에 있다. 세션 행은 `sessions.jsonl`, 판정 점수는 `judge/scores-p{1,2}.jsonl`이다.

## 판정: **채택**

| 규칙 | 값 | 성립 |
|---|---|---|
| 기각: S(Cb,1) ≤ S(C0,1) − 0.3 | S(Cb,1) 4.25 · S(C0,1) 4.208 · 차 +0.042 | 아니오 |
| (2) T(Cb) < T(C0) (턴 중앙) | 15.5 vs 17.0 | 예 |
| (2) K(Cb) < K(C0) (입력 토큰 중앙) | 553,506 vs 626,666 | 예 |
| (2) S(Cb) ≥ S(C0) − D | 4.708 vs 4.417 − D 0.167 = 4.250 | 예 |
| (3) T(Cb) < T(C0) (턴 중앙) | 13 vs 18 | 예 |
| (3) K(Cb) < K(C0) (입력 토큰 중앙) | 299,649 vs 422,044 | 예 |
| (3) S(Cb) ≥ S(C0) − D | 4.778 vs 4.722 − D 0.444 = 4.278 | 예 |

판정에서 뺀 태스크(§5.5, 묶음 (3)에서 관련 생김): s6b-t004. 아래 표 1–3은 판정 대상만, 표 1b는 그 태스크를 따로 보인다.

## 표 1. 묶음 × 조건

| 묶음 | 조건 | n | 점수 (p1 / p2) | 체크 통과 | 턴 중앙 (평균) | 입력 토큰 중앙 | 비용 중앙 $ | 발화 | 로드 ≥1 | 로드 수 평균 |
|---|---|---|---|---|---|---|---|---|---|---|
| (1) | A | 12 | 3.417 (3.333 / 3.5) | 12/12 | 12.5 (12.417) | 339,550 | 0.373 | 0/12 | 0/12 | 0 |
| (1) | C0 | 12 | 4.208 (4.25 / 4.167) | 12/12 | 22.0 (23.167) | 819,824 | 0.734 | 12/12 | 12/12 | 2.5 |
| (1) | Cb | 12 | 4.25 (4.417 / 4.083) | 12/12 | 24.0 (23.75) | 809,176 | 0.684 | 12/12 | 12/12 | 2.083 |
| (2) | A | 12 | 4.167 (4.083 / 4.25) | 12/12 | 9.0 (9.917) | 264,272 | 0.506 | 0/12 | 0/12 | 0 |
| (2) | C0 | 12 | 4.417 (4.333 / 4.5) | 12/12 | 17.0 (17) | 626,666 | 0.784 | 12/12 | 12/12 | 1.917 |
| (2) | Cb | 12 | 4.708 (4.667 / 4.75) | 12/12 | 15.5 (16.667) | 553,506 | 0.706 | 12/12 | 12/12 | 1.75 |
| (3) | A | 9 | 4.722 (4.556 / 4.889) | 9/9 | 9 (10.111) | 198,989 | 0.219 | 0/9 | 0/9 | 0 |
| (3) | C0 | 9 | 4.722 (4.556 / 4.889) | 9/9 | 18 (17.111) | 422,044 | 0.383 | 9/9 | 5/9 | 0.667 |
| (3) | Cb | 9 | 4.778 (4.556 / 5) | 9/9 | 13 (13.444) | 299,649 | 0.321 | 8/9 | 0/9 | 0 |

### 표 1b. 판정에서 뺀 태스크

| 태스크 | 조건 | n | 점수 (p1 / p2) | 체크 통과 | 턴 중앙 | 입력 토큰 중앙 | 로드 ≥1 |
|---|---|---|---|---|---|---|---|
| s6b-t004 | A | 3 | 4.0 (4 / 4) | 2/3 | 23 | 1,026,900 | 0/3 |
| s6b-t004 | C0 | 3 | 4.167 (4 / 4.333) | 0/3 | 39 | 1,477,627 | 2/3 |
| s6b-t004 | Cb | 3 | 3.667 (3.667 / 3.667) | 1/3 | 33 | 1,000,770 | 1/3 |

## 표 2. 태스크별 점수 평균 (두 판정 평균) · 턴 중앙

| 묶음 | 태스크 | A 점수 | C0 점수 | Cb 점수 | A 턴 | C0 턴 | Cb 턴 |
|---|---|---|---|---|---|---|---|
| (1) | d1-landing | 3.167 | 4.833 | 5.0 | 7 | 22 | 30 |
| (1) | d2-redesign | 3.667 | 4.333 | 3.833 | 8 | 20 | 17 |
| (1) | d3-dashboard | 2.833 | 3.333 | 3.833 | 22 | 22 | 23 |
| (1) | d4-email | 4.0 | 4.333 | 4.333 | 13 | 23 | 25 |
| (2) | s2-tests | 4.167 | 4.667 | 4.833 | 9 | 14 | 13 |
| (2) | s2-api | 4.0 | 4.5 | 4.333 | 12 | 21 | 21 |
| (2) | s2-docs | 4.333 | 4.833 | 5.0 | 8 | 15 | 15 |
| (2) | s2-data | 4.167 | 3.667 | 4.667 | 10 | 17 | 14 |
| (3) | s6b-t004 (판정 제외) | 4.0 | 4.167 | 3.667 | 23 | 39 | 33 |
| (3) | s6b-t133 | 4.667 | 4.5 | 4.5 | 6 | 11 | 10 |
| (3) | s6b-t179 | 4.5 | 4.667 | 4.833 | 11 | 21 | 17 |
| (3) | s6b-t354 | 5.0 | 5.0 | 5.0 | 10 | 19 | 15 |

## 표 3. 로드 세트 (C0 · Cb; 세션별 로드한 스킬)

| 태스크 | 조건 | r1 | r2 | r3 |
|---|---|---|---|---|
| d1-landing | C0 | frontend-design, copywriting | frontend-design, copywriting | frontend-design, next-best-practices, copywriting |
| d1-landing | Cb | frontend-design, copywriting, next-best-practices | frontend-design, copywriting | frontend-design, copywriting, next-best-practices |
| d2-redesign | C0 | redesign-skill, frontend-design, responsive-design | redesign-skill, frontend-design, responsive-design | redesign-skill, responsive-design, frontend-design |
| d2-redesign | Cb | redesign-skill, frontend-design, ui-audit | redesign-skill, responsive-design | redesign-skill, responsive-design |
| d3-dashboard | C0 | next-best-practices, frontend-patterns | next-best-practices, frontend-design, accessibility-compliance | next-best-practices, frontend-design |
| d3-dashboard | Cb | next-best-practices | next-best-practices, frontend-design | next-best-practices, accessibility-compliance |
| d4-email | C0 | email-marketing, redesign-skill | frontend-design, redesign-skill | email-marketing, redesign-skill, frontend-design |
| d4-email | Cb | email-marketing, redesign-skill | email-marketing, redesign-skill | email-marketing |
| s2-tests | C0 | python-testing-patterns, verification-loop | python-testing-patterns, verification-loop | python-testing-patterns, property-based-testing |
| s2-tests | Cb | python-testing-patterns, property-based-testing | python-testing-patterns, verification-loop | python-testing-patterns, property-based-testing |
| s2-api | C0 | fastapi-templates, api-design | api-design, fastapi-endpoint | api-design, fastapi-templates |
| s2-api | Cb | api-design, fastapi-templates | api-design, fastapi-templates | api-design, fastapi-templates |
| s2-docs | C0 | quill | quill, spec-miner | quill, spec-miner |
| s2-docs | Cb | quill | quill, spec-miner | quill, spec-miner |
| s2-data | C0 | data-analyst-engine, python-error-handling | data-analyst-engine, python-error-handling | data-analyst-engine, python-error-handling |
| s2-data | Cb | data-analyst-engine | data-analyst-engine | data-analyst-engine, python-error-handling |
| s6b-t004 | C0 | 없음 (발화) | verification-loop | sqlmodel |
| s6b-t004 | Cb | 없음 (발화) | sqlmodel | 없음 (발화) |
| s6b-t133 | C0 | 없음 (발화) | 없음 (발화) | 없음 (발화) |
| s6b-t133 | Cb | 없음 (발화) | 없음 (발화) | 없음 (발화) |
| s6b-t179 | C0 | 없음 (발화) | verification-loop | sqlmodel |
| s6b-t179 | Cb | 없음 (발화) | 없음 (발화) | 없음 |
| s6b-t354 | C0 | verification-loop | sqlmodel, verification-loop | verification-loop |
| s6b-t354 | Cb | 없음 (발화) | 없음 (발화) | 없음 (발화) |

## 표 4. 판정 일치 (p1 vs p2, 같은 루브릭, 새 코드·새 판정자)

| 묶음 | n | 세션 점수 일치 | 평균 절대 차 | 최대 차 | D(b) = 조건 평균 차 최대 |
|---|---|---|---|---|---|
| (1) | 36 | 21/36 | 0.417 | 1 | 0.334 |
| (2) | 36 | 31/36 | 0.139 | 1 | 0.167 |
| (3) | 27 | 15/27 | 0.444 | 1 | 0.444 |

## 실행 기록

- **1차 큐(108세션 중 39세션 유효)**: 02:03 KST부터 세션이 1턴 $0으로 끝났다. 결과는 "You've hit your org's monthly spend limit"였다(69세션). 그 계정의 한도 소진 때문이고, 세션이 작업을 시작하지 못한 하네스 실패라 §5.6에 따라 제외했다. 출력은 `runs/_spendlimit/`에 있다.
- **2차 큐(계정 전환 뒤, 69세션 재실행 중 22세션 유효)**: 47세션이 "You've hit your session limit · resets 3:10am"로 1턴 $0에 끝났다. 같은 방식으로 제외했다(`runs/_sessionlimit/`).
- **3차 큐**: 나머지 47세션을 재실행했다. 사용량 한도 메시지는 0건이었고, 108/108 모두 `success`이며 1턴 $0 세션은 0이다.
- **세션별 계정**: 처음 39세션과 재실행 69세션은 서로 다른 로그인 계정에서 돌았다. 큐 순서는 처음과 같다(`runs/_queue.txt`, 고정 시드). 재실행은 (태스크, 반복, 조건) 단위로 빠진 것만 다시 돌렸다.
- **파일럿**: 조건 A의 skill 목록에 메인 체크아웃의 옛 라우터가 보였다. 메인 체크아웃을 `s6b-a`로 바꿔 고쳤다(`report-pilot.md`).
- **판정**: 24패스(12 세트 × p1·p2), 각 패스는 새 하위 에이전트이고 루브릭과 세트 폴더만 받았다. 형식 검증 뒤에 키를 읽었다(`scripts/unblind_6b.py`).

## 비용

본 실행 108세션 $63.65(API 환산). 파일럿은 `report-pilot.md`.

