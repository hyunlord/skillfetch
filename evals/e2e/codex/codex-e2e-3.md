Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro 구독 로그인 (`chatgpt`/`pro`), API 키 환경변수 미상속 | 주 세션 실제 신원·키 부재 확인 57/57

# Codex E2E 3: 전체 skillfetch 라우터, 19개 태스크 × 3회

**FAIL · 완료 판정 불가: 1228/1229개 감사 검사 통과.** manifest=`COMPLETED`, audit=`FAIL`. 관측된 실제 태스크 제출 57/57회, 정상 종료 57/57회다. 발화율은 **57/57 (100.0%)**다. 발화는 모델이 skillfetch MCP 호출을 요청한 세션이며, 응답 수신·프로토콜 성공·스킬 반환과 별도로 센다.

**실제 실행 범위: 주 세션 57개 + 예상하지 않은 native 하위 에이전트 1개.** 관측된 고유 thread/turn은 58/58개다. 모델의 spawn_agent 시도 4회 중 3회는 부모 rollout 누락 오류였고, 1개 하위 thread가 실제 실행됐다. 설정의 multi_agent=false·multi_agent_v2=false가 이 실행에서 하위 에이전트를 막지 못했다. 초기 skillfetch 라우팅 이후 발생한 이 동작 때문에 주 세션 종료 성공과 별개로 런타임 감사 FAIL을 유지한다. 재실행하지 않았다.

[종료 manifest](codex-e2e-3-runs/20261024-full-router-14d2020/manifest.json) · [독립 전수 감사](codex-e2e-3-runs/20261024-full-router-14d2020/audit-verification.json) · [통합 관찰·새 라벨 결합](codex-e2e-3-runs/20261024-full-router-14d2020/observations-e2e3.json) · [별도 원시 파서의 지표 재검증](codex-e2e-3-runs/20261024-full-router-14d2020/independent-metrics-verification.json) (`PASS`)

[하위 에이전트 전수 조사·원시 이벤트 참조](codex-e2e-3-runs/20261024-full-router-14d2020/child-agent-findings.json). 하위 에이전트 MCP 이벤트는 0개이며, 아래 228회 MCP 지표는 57개 주 세션의 호출이다. 하위 에이전트의 독립 인증·프로세스 정리는 확인되지 않았다.

고정된 동일 19개 요청을 세 번 반복하는 57개 주 세션을 대상으로 했다. 아래 발화·질의·프로토콜·로드·관련성 지표의 분모는 이 주 세션이며, 하위 에이전트를 별도 태스크 표본으로 추가하지 않았다. 실제 제출·종료 수와 실패는 아래 기록한다. 이번 변경은 AGENTS.md에 `When`, 1–8단계, `Rules`를 모두 넣은 것이다. Codex 호스트용 1–2단계는 이전 승인본과 같고, 로컬 스킬 예시만 `.agents/skills/`로 바꿨다. 코드 결과물의 품질이나 테스트 통과 여부는 채점하지 않았다.

## 주 세션의 실제 실행과 호출

| 지표 | r1 | r2 | r3 | 합계 |
|---|---:|---:|---:|---:|
| 실제 요청 제출 | 19/19 | 19/19 | 19/19 | 57/57 |
| skillfetch 호출 세션(발화율) | 19/19 (100.0%) | 19/19 (100.0%) | 19/19 (100.0%) | 57/57 (100.0%) |
| 서버 결과 수신 세션 | 19/19 (100.0%) | 19/19 (100.0%) | 19/19 (100.0%) | 57/57 (100.0%) |
| MCP 프로토콜 성공 응답 세션 | 19/19 (100.0%) | 19/19 (100.0%) | 19/19 (100.0%) | 57/57 (100.0%) |
| search 호출 세션 / 횟수 | 19/19 · 19회 | 19/19 · 19회 | 19/19 · 19회 | 57/57 · 57회 |
| queries 4개·4번째 원문 완전 일치 | 19/19 검색 호출 | 19/19 검색 호출 | 19/19 검색 호출 | 57/57 검색 호출 |
| load 호출 세션 / 횟수 | 19/19 · 19회 | 19/19 · 19회 | 19/19 · 19회 | 57/57 · 57회 |
| 실제 스킬 ID 반환 세션 | 19/19 (100.0%) | 19/19 (100.0%) | 19/19 (100.0%) | 57/57 (100.0%) |
| 반환 세트 미확인(null) | 0 | 0 | 0 | 0 |
| 정상 turn 종료 | 19/19 | 19/19 | 19/19 | 57/57 |
| worktree 정리 DONE | 19/19 | 19/19 | 19/19 | 57/57 |

주 세션의 MCP 요청 228회, 서버 결과 수신 228회, 프로토콜 성공 228회, 승인 거절 0회다. 서버 결과가 존재해도 MCP 오류 플래그나 도메인 payload 오류가 있으면 성공과 구분한다.

| MCP 도구 | 모델 호출 요청 | 서버 결과 수신 | 프로토콜 SUCCESS | FAILURE | CONFLICT·UNOBSERVED 등 |
|---|---:|---:|---:|---:|---:|
| `load_skills` | 57 | 57 | 57 | 0 | 0 |
| `profile_repo` | 57 | 57 | 57 | 0 | 0 |
| `resolve_set` | 57 | 57 | 57 | 0 | 0 |
| `search_skills` | 57 | 57 | 57 | 0 | 0 |

load payload 의미 상태: `SUCCESS` 57. 반환 관찰 충돌 0회. `SUCCESS`는 skills 배열과 오류 상태에 대한 추출기 판정이고, `PARTIAL_ERROR`는 일부 스킬 반환과 payload errors가 함께 있는 상태다. 반환 ID는 요청 ID가 아니라 프로토콜 성공 결과의 `skills[].id`에서 가져왔다. 충돌한 반환 세트는 null로 남겼다.

첫 호출 회차 분포: `2` 57. 연결 방법: `unique_closed_code_exec_interval` 57. 회차 미확인 0개.

외부 사용자 요청은 주 세션마다 1회 제출했다. 여기서 첫 호출 “회차”는 같은 주 thread/turn의 고유 `rawResponse/completed.responseId` 경계를 센 1-based 모델 응답 순서다. `direct_call_id`는 직접 연결이며, `unique_closed_code_exec_interval` 등은 호출을 감싼 exec 구간으로 추론한 값이다. 추론을 실제 부모 ID로 취급하지 않는다. 불명확하면 미확인으로 남겼다. Claude의 assistant-message 순번과 같은 단위로 비교하지 않는다.

## queries 원문과 800자 이상 요청

매 검색 호출의 모든 lifecycle 인자 관찰에 대해 `queries.length === 4`, 네 값이 모두 문자열, `queries[3] === 고정 태스크 prompt`를 검사했다. 공백·줄바꿈·Unicode를 정규화하지 않았다. 네 번째 질의뿐 아니라 네 질의 원문, 관찰 sequence, 충돌 여부를 아래 57개 세션의 JSON 링크에 보존했다. 미호출·인자 없음·충돌은 일치로 세지 않는다.

800자 이상은 원래 요청의 Unicode code point 수로 판정했다(UTF-16 길이·UTF-8 바이트도 JSON에 보존). 해당 태스크 4/19개, 반복 세션 12/57개다.

| 태스크 | 원문 문자 수 | 800자 이상 | r1 검색 일치/호출 | r2 | r3 |
|---|---:|---|---|---|---|
| s4-t027 | 1219 | 예 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t027.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t027.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t027.json) |
| s4-t176 | 485 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t176.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t176.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t176.json) |
| s4-t153 | 179 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t153.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t153.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t153.json) |
| s4-t253 | 303 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t253.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t253.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t253.json) |
| s4-t182 | 294 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t182.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t182.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t182.json) |
| s4-t203 | 271 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t203.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t203.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t203.json) |
| s4-t055 | 103 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t055.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t055.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t055.json) |
| s4-t033 | 942 | 예 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t033.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t033.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t033.json) |
| s4-t130 | 104 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t130.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t130.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t130.json) |
| s4-t177 | 1351 | 예 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t177.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t177.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t177.json) |
| s4-t229 | 731 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t229.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t229.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t229.json) |
| s4-t026 | 823 | 예 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t026.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t026.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t026.json) |
| s4-t224 | 273 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t224.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t224.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t224.json) |
| s4-t211 | 263 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t211.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t211.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t211.json) |
| s4-t354 | 363 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t354.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t354.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t354.json) |
| s4-t101 | 333 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t101.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t101.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t101.json) |
| s4-t342 | 463 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t342.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t342.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t342.json) |
| s4-t280 | 124 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t280.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t280.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t280.json) |
| s4-t001 | 97 | 아니오 | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t001.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t001.json) | 1/1 · [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t001.json) |

## 관련성: 누적 4-0 oracle로 양쪽을 다시 결합

[누적 oracle-4-0.jsonl](stage5/oracle-4-0.jsonl) SHA256: `7db50e73c7dfd6b0b810ba65231fd1475a25a563651310592c88da23795e108c`. [판정 기준](codex-e2e-3-label-basis.json). 태스크 ID와 revision을 포함한 전체 skill ID가 정확히 일치할 때만 기존 grade를 사용했다. grade ≥ 2를 관련 스킬로 본다. 관련 스킬이 있는 태스크는 17개, 없는 태스크는 2개(`s4-t354`, `s4-t342`)다. 신규 채점은 수행하지 않았다.

hit 분모는 **관련 스킬이 존재하는 태스크에서 실제 스킬을 반환받은 세션**이다. 세 반복이 모두 로드되어도 최대 51이며, 전체 57이나 무조건 51을 분모로 넣지 않았다. R=0이고 미채점 U>0인 세션은 미해결로 따로 센다. 이때 확인된 hit 비율은 하한이며, 미해결을 확정 실패로 바꾸지 않는다.

R은 grade ≥ 2, N은 grade < 2, U는 미채점·pool 외 ID다. graded micro precision은 전체 세션의 R 합계/(R+N) 합계다. graded macro precision은 한 개 이상의 채점된 반환이 있는 각 세션의 R/(R+N)을 동일 가중 평균한 값이며, 그 세션 수를 별도 표시한다. U는 0점으로 치환하지 않는다. 동일 ID는 한 세션 안에서 중복 제거하고, 서로 다른 세션에서는 각각 센다.

| 코호트 | 로드 세션 | hit(loaded related) | 미해결 related | graded micro | graded macro(분모 세션) | R / N / U | 채점 coverage | none 태스크 로드 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Codex 전체 라우터 r1 | 19/19 | 9/17 (52.9%) | 2 | 10/18 (55.6%) | 52.9% (17) | 10 / 8 / 2 | 18/20 (90.0%) | 2/2 (100.0%) |
| Codex 전체 라우터 r2 | 19/19 | 8/17 (47.1%) | 0 | 9/20 (45.0%) | 42.1% (19) | 9 / 11 / 1 | 20/21 (95.2%) | 2/2 (100.0%) |
| Codex 전체 라우터 r3 | 19/19 | 9/17 (52.9%) | 1 | 10/18 (55.6%) | 52.9% (17) | 10 / 8 / 3 | 18/21 (85.7%) | 2/2 (100.0%) |
| Codex 전체 라우터 합계 | 57/57 | 26/51 (51.0%) | 3 | 29/56 (51.8%) | 49.1% (53) | 29 / 27 / 6 | 56/62 (90.3%) | 6/6 (100.0%) |
| 기존 Claude V2 r1 | 19/19 | 11/17 (64.7%) | 0 | 13/27 (48.1%) | 51.8% (19) | 13 / 14 / 2 | 27/29 (93.1%) | 2/2 (100.0%) |
| 기존 Claude V2 r2 | 17/19 | 13/15 (86.7%) | 0 | 16/24 (66.7%) | 70.6% (17) | 16 / 8 / 1 | 24/25 (96.0%) | 2/2 (100.0%) |
| 기존 Claude V2 r3 | 19/19 | 13/17 (76.5%) | 1 | 16/28 (57.1%) | 63.9% (18) | 16 / 12 / 3 | 28/31 (90.3%) | 2/2 (100.0%) |
| 기존 Claude V2 합계 | 55/57 | 37/49 (75.5%) | 1 | 45/79 (57.0%) | 61.7% (54) | 45 / 34 / 6 | 79/85 (92.9%) | 6/6 (100.0%) |

Codex graded macro에서 채점된 반환이 하나도 없어 제외한 로드 세션: 4. 전체 반환 중 확인된 관련 스킬 비율: 29/62 (46.8%); U가 있으면 하한이다. 미채점 coverage: 6/62 (9.7%). path: ID 0건은 다른 ID로 정규화하지 않았다.

기존 Claude V2 57개 세션은 [기존 반환·원시 로그 참조](codex-e2e-2-oracle-v2.json)에서 반환 ID와 요청 해시를 읽고, 이전 grade 값을 버린 뒤 같은 누적 4-0 oracle에 새로 결합했다. Claude를 다시 실행하지 않았다. 아래는 동일 태스크·동일 라벨로 계산한 관찰 비교이며, 호스트·모델·실행 시점이 다른 코호트의 차이를 라우터만의 인과 효과로 해석하지 않는다. 이전 Codex 보고서에 있던 재채점 전 수치를 복사하지 않았다.

| 코호트 합계 | 발화 | 검색 | 스킬 반환 | none 로드/검색된 none | none의 N / U | 실제 모델 기록 |
|---|---:|---:|---:|---:|---:|---|
| Codex | 57/57 (100.0%) | 57/57 | 57/57 | 6/6 (100.0%) | 5 / 1 | `gpt-6-astra` 57 |
| Claude V2 | 57/57 (100.0%) | 57/57 | 55/57 | 6/6 (100.0%) | 9 / 0 | `claude-opus-5-5[1m]` 57 |

Claude의 비-load 호출에 대해 Codex와 같은 프로토콜 결과 증거가 없는 경우 0건의 성공으로 해석하지 않는다. 두 코호트의 로드 세트·관련성 지표만 같은 라벨 규칙으로 맞췄다.

## 57개 주 세션 기록

세션 링크는 원시 JSONL이다. 질의 링크는 원문을 재번역·축약하지 않은 별도 JSON이다. 종료 상태는 각 주 manifest.turn_id에 해당하는 lifecycle 결과이며, 코딩 품질 평가가 아니다. 원시 transcript에 함께 기록된 하위 turn 종료는 이 열에서 제외하고 별도 기록했다.

| 세션 | 레포 | 호출 수 | 첫 도구 | 첫 호출 회차 | queries 원문·검사 | 반환 스킬 ID | 종료 / turn 상태 | 정리 |
|---|---|---:|---|---|---|---|---|---|
| [r1/s4-t027](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t027/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t027.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t176](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t176/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t176.json)<br>PASS | `uasl/tdd-workflow@6eadb0bf0ea8` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t153](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t153/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t153.json)<br>PASS | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t253](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t253/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t253.json)<br>PASS | `uasl/python-performance-optimization@bf455fd100bf` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t182](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t182/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t182.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t203](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t203/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t203.json)<br>PASS | `uasl/data-analyst-engine@79799e01e2dd` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t055/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t055.json)<br>PASS | `uasl/zen@f72229d0a781` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t033](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t033/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t033.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t130](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t130/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t130.json)<br>PASS | `uasl/github-workflow-automation@519f4ba6e482` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t177](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t177/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t177.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t229](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t229/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t229.json)<br>PASS | `uasl/auth-implementation-patterns@7a99b395d548` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t026](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t026/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t026.json)<br>PASS | `uasl/vercel-react-best-practices@70f3b5aaf775` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t224](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t224/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t224.json)<br>PASS | `uasl/typescript-unit-testing@6fb3561edcb3` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t211](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t211/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t211.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t354](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t354/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t354.json)<br>PASS | `uasl/verification-loop@39d9be23cf50` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t101](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t101/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t101.json)<br>PASS | `uasl/quill@336ba74b0e79` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t342](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t342/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t342.json)<br>PASS | `uasl/coding-standards@f854e26a9529` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t280](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t280/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t280.json)<br>PASS | `uasl/interaction-design@7c9d38549c2b` | `COMPLETED` / completed | `DONE` |
| [r1/s4-t001](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t001/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r1/s4-t001.json)<br>PASS | `uasl/anvil@3a36e8410205` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t027](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t027/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t027.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t176](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t176/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t176.json)<br>PASS | `uasl/debugging-strategies@c55dad9c9654` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t153](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t153/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t153.json)<br>PASS | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t253](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t253/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t253.json)<br>PASS | `uasl/sql-optimization-patterns@389f90da7b56` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t182](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t182/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t182.json)<br>PASS | `uasl/stream@94a72913c590` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t203](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t203/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t203.json)<br>PASS | `uasl/data-analyst-engine@79799e01e2dd` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t055/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t055.json)<br>PASS | `uasl/zen@f72229d0a781` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t033](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t033/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t033.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t130](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t130/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t130.json)<br>PASS | `uasl/github-workflow-automation@519f4ba6e482` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t177](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t177/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t177.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t229](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t229/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t229.json)<br>PASS | `uasl/auth-implementation-patterns@7a99b395d548` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t026](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t026/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t026.json)<br>PASS | `uasl/codenavi@109490043377` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t224](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t224/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t224.json)<br>PASS | `uasl/radar@a47ea6fd5f95` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t211](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t211/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t211.json)<br>PASS | `uasl/python-design-patterns@5c0fbe0d4633`<br>`uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t354](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t354/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t354.json)<br>PASS | `uasl/verification-loop@39d9be23cf50` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t101](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t101/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t101.json)<br>PASS | `uasl/quill@336ba74b0e79` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t342](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t342/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t342.json)<br>PASS | `uasl/verification-loop@39d9be23cf50` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t280](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t280/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t280.json)<br>PASS | `uasl/interaction-design@7c9d38549c2b` | `COMPLETED` / completed | `DONE` |
| [r2/s4-t001](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t001/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r2/s4-t001.json)<br>PASS | `uasl/coding-standards@f854e26a9529` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t027](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t027/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t027.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t176](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t176/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t176.json)<br>PASS | `uasl/debugging-strategies@c55dad9c9654` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t153](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t153/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t153.json)<br>PASS | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t253](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t253/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t253.json)<br>PASS | `uasl/python-performance-optimization@bf455fd100bf` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t182](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t182/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t182.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t203](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t203/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t203.json)<br>PASS | `uasl/data-analyst-engine@79799e01e2dd` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t055/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t055.json)<br>PASS | `uasl/zen@f72229d0a781` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t033](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t033/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t033.json)<br>PASS | `uasl/debug-root-cause@1d7ea4a832dc` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t130](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t130/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t130.json)<br>PASS | `uasl/github-workflow-automation@519f4ba6e482` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t177](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t177/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t177.json)<br>PASS | `uasl/python-error-handling@8dc34883a143`<br>`uasl/radar@a47ea6fd5f95` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t229](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t229/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t229.json)<br>PASS | `uasl/auth-implementation-patterns@7a99b395d548` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t026](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t026/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t026.json)<br>PASS | `uasl/radar@a47ea6fd5f95` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t224](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t224/transcript.jsonl) | nextjs | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t224.json)<br>PASS | `uasl/radar@a47ea6fd5f95` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t211](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t211/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t211.json)<br>PASS | `uasl/error-handling-patterns@4c19ee7d7821` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t354](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t354/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t354.json)<br>PASS | `uasl/python-error-handling@8dc34883a143` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t101](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t101/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t101.json)<br>PASS | `uasl/quill@336ba74b0e79` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t342](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t342/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t342.json)<br>PASS | `uasl/verification-loop@39d9be23cf50` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t280](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t280/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t280.json)<br>PASS | `uasl/interaction-design@7c9d38549c2b` | `COMPLETED` / completed | `DONE` |
| [r3/s4-t001](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t001/transcript.jsonl) | fastapi | 4 | `profile_repo` | 2 (추론) | [queries 원문 JSON](codex-e2e-3-runs/20261024-full-router-14d2020/query-records/r3/s4-t001.json)<br>PASS | `uasl/anvil@3a36e8410205` | `COMPLETED` / completed | `DONE` |

## 19개 태스크의 실제 선택 세트 비교

각 칸은 실제 load 반환 ID의 세션 내 고유 집합이다. `[]`는 반환 없음, null은 증거 충돌·누락 등으로 확정할 수 없는 세트다. revision과 로컬 path를 그대로 표시한다.

| 태스크 | Codex r1 | Codex r2 | Codex r3 | Claude V2 r1 | Claude V2 r2 | Claude V2 r3 |
|---|---|---|---|---|---|---|
| s4-t027 | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/coding-guidelines@0ec7e45f92f2` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/coding-guidelines@0ec7e45f92f2` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/tdd@ff86dad94075` |
| s4-t176 | `uasl/tdd-workflow@6eadb0bf0ea8` | `uasl/debugging-strategies@c55dad9c9654` | `uasl/debugging-strategies@c55dad9c9654` | `path:<worktrees>/s5/s5-V2-s4-t176-r1/.agents/skills/sqlmodel`<br>`uasl/debug-root-cause@1d7ea4a832dc` | `uasl/debug-root-cause@1d7ea4a832dc` | `uasl/debug-root-cause@1d7ea4a832dc` |
| s4-t153 | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `uasl/deployment-pipeline-design@2a89fc6f32ff` | `uasl/verification-loop@39d9be23cf50` | `uasl/karpathy-guidelines@da897c8c3bab` | `uasl/karpathy-guidelines@da897c8c3bab` |
| s4-t253 | `uasl/python-performance-optimization@bf455fd100bf` | `uasl/sql-optimization-patterns@389f90da7b56` | `uasl/python-performance-optimization@bf455fd100bf` | `path:<worktrees>/s5/s5-V2-s4-t253-r1/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel`<br>`uasl/python-performance-optimization@bf455fd100bf` | `path:<worktrees>/s5/s5-V2-s4-t253-r2/.claude/skills/sqlmodel`<br>`uasl/sql-optimization-patterns@389f90da7b56` | `path:<worktrees>/s5/s5-V2-s4-t253-r3/.claude/skills/sqlmodel`<br>`uasl/schema@e6f260ce62e0` |
| s4-t182 | `uasl/python-error-handling@8dc34883a143` | `uasl/stream@94a72913c590` | `uasl/python-error-handling@8dc34883a143` | `uasl/python-error-handling@8dc34883a143` | `[]` | `path:<worktrees>/s5/s5-V2-s4-t182-r3/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel` |
| s4-t203 | `uasl/data-analyst-engine@79799e01e2dd` | `uasl/data-analyst-engine@79799e01e2dd` | `uasl/data-analyst-engine@79799e01e2dd` | `uasl/data-analyst-engine@79799e01e2dd` | `uasl/data-analyst-engine@79799e01e2dd` | `uasl/data-analyst-engine@79799e01e2dd` |
| s4-t055 | `uasl/zen@f72229d0a781` | `uasl/zen@f72229d0a781` | `uasl/zen@f72229d0a781` | `uasl/refactoring-patterns@7283bad3e86e` | `uasl/refactoring-patterns@7283bad3e86e`<br>`uasl/verification-loop@39d9be23cf50` | `uasl/refactoring-patterns@7283bad3e86e`<br>`uasl/react-patterns@73d1ecc06997` |
| s4-t033 | `uasl/debug-root-cause@1d7ea4a832dc` | `uasl/debug-root-cause@1d7ea4a832dc` | `uasl/debug-root-cause@1d7ea4a832dc` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/coding-guidelines@0ec7e45f92f2`<br>`uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/coding-guidelines@0ec7e45f92f2` |
| s4-t130 | `uasl/github-workflow-automation@519f4ba6e482` | `uasl/github-workflow-automation@519f4ba6e482` | `uasl/github-workflow-automation@519f4ba6e482` | `uasl/github-actions-templates@ce03df93ccdf` | `uasl/github-actions-templates@ce03df93ccdf` | `uasl/github-actions-templates@ce03df93ccdf` |
| s4-t177 | `uasl/python-error-handling@8dc34883a143` | `uasl/python-error-handling@8dc34883a143` | `uasl/python-error-handling@8dc34883a143`<br>`uasl/radar@a47ea6fd5f95` | `uasl/stream@94a72913c590`<br>`uasl/python-error-handling@8dc34883a143` | `uasl/stream@94a72913c590`<br>`uasl/python-error-handling@8dc34883a143` | `path:<worktrees>/s5/s5-V2-s4-t177-r3/.venv/lib/python3.14/site-packages/sqlmodel/.agents/skills/sqlmodel`<br>`uasl/python-error-handling@8dc34883a143`<br>`uasl/stream@94a72913c590` |
| s4-t229 | `uasl/auth-implementation-patterns@7a99b395d548` | `uasl/auth-implementation-patterns@7a99b395d548` | `uasl/auth-implementation-patterns@7a99b395d548` | `uasl/auth-implementation-patterns@7a99b395d548`<br>`uasl/verification-loop@39d9be23cf50` | `uasl/auth-implementation-patterns@7a99b395d548`<br>`uasl/verification-loop@39d9be23cf50` | `uasl/auth-implementation-patterns@7a99b395d548`<br>`uasl/verification-loop@39d9be23cf50` |
| s4-t026 | `uasl/vercel-react-best-practices@70f3b5aaf775` | `uasl/codenavi@109490043377` | `uasl/radar@a47ea6fd5f95` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/verification-loop@39d9be23cf50` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/vercel-react-best-practices@70f3b5aaf775` | `uasl/debug-root-cause@1d7ea4a832dc`<br>`uasl/verification-loop@39d9be23cf50` |
| s4-t224 | `uasl/typescript-unit-testing@6fb3561edcb3` | `uasl/radar@a47ea6fd5f95` | `uasl/radar@a47ea6fd5f95` | `uasl/documentation-lookup@dee6d7478eab` | `uasl/documentation-lookup@dee6d7478eab`<br>`uasl/next-best-practices@ee058f89acea` | `uasl/documentation-lookup@dee6d7478eab` |
| s4-t211 | `uasl/python-error-handling@8dc34883a143` | `uasl/python-design-patterns@5c0fbe0d4633`<br>`uasl/python-error-handling@8dc34883a143` | `uasl/error-handling-patterns@4c19ee7d7821` | `uasl/coding-standards@f854e26a9529` | `uasl/fastapi-templates@effcd0de0b4c` | `uasl/error-handling-patterns@4c19ee7d7821` |
| s4-t354 | `uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50` | `uasl/python-error-handling@8dc34883a143` | `uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50` |
| s4-t101 | `uasl/quill@336ba74b0e79` | `uasl/quill@336ba74b0e79` | `uasl/quill@336ba74b0e79` | `uasl/quill@336ba74b0e79` | `uasl/quill@336ba74b0e79` | `uasl/quill@336ba74b0e79`<br>`uasl/verification-before-completion@134bf517af69` |
| s4-t342 | `uasl/coding-standards@f854e26a9529` | `uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50` | `uasl/verification-loop@39d9be23cf50`<br>`uasl/coding-standards@f854e26a9529` | `uasl/verification-loop@39d9be23cf50`<br>`uasl/coding-standards@f854e26a9529` | `uasl/verification-loop@39d9be23cf50`<br>`uasl/coding-standards@f854e26a9529` |
| s4-t280 | `uasl/interaction-design@7c9d38549c2b` | `uasl/interaction-design@7c9d38549c2b` | `uasl/interaction-design@7c9d38549c2b` | `uasl/react-patterns@73d1ecc06997`<br>`uasl/design-to-code@fae28f73cda0` | `uasl/artisan@1e09f38ffcab` | `uasl/design-to-code@fae28f73cda0`<br>`uasl/react-patterns@73d1ecc06997` |
| s4-t001 | `uasl/anvil@3a36e8410205` | `uasl/coding-standards@f854e26a9529` | `uasl/anvil@3a36e8410205` | `uasl/coding-standards@f854e26a9529` | `[]` | `uasl/coding-standards@f854e26a9529`<br>`uasl/verification-loop@39d9be23cf50` |

## 실패·부분 오류·미확인 기록

실제 실행 종료 상태: `COMPLETED` 57. 감사 판정은 별도 축이며 `FAIL`다. 실제 세션 실패를 증거 변조나 해시 불일치로 간주하지 않으며, 감사 FAIL도 전부 세션 실패 때문이라고 추정하지 않는다. 무결성 세부 판정: `별도 분류 없음; 실패 검사 참조`.

실패한 감사 검사: `r1:s4-t055:turn_lifecycle_complete`. 제출 관측이 없는 transcript 0개는 0회 제출로 간주하지 않는다.

하위 에이전트 조사: [57개 transcript SHA256와 전수 스캔 결과](codex-e2e-3-runs/20261024-full-router-14d2020/child-agent-findings.json). 아래 seq는 링크된 원시 JSONL의 event_sequence와 행 번호다. 세 번의 실패는 `no rollout found for thread id` 오류이며 승인 거절로 분류하지 않았다.

| 주 세션 | spawn seq | task_name | fork_turns | 결과 | 출력 seq |
|---|---:|---|---|---|---:|
| [r1/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t055/transcript.jsonl) | 132 | `extract_items` | 미지정 | `FAILED_BEFORE_OBSERVED_CHILD` | 136 |
| [r1/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t055/transcript.jsonl) | 160 | `implementation` | `none` | `OBSERVED_CHILD_STARTED` | 168 |
| [r2/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r2/tasks/s4-t055/transcript.jsonl) | 143 | `extract_items` | 미지정 | `FAILED_BEFORE_OBSERVED_CHILD` | 147 |
| [r3/s4-t055](codex-e2e-3-runs/20261024-full-router-14d2020/r3/tasks/s4-t055/transcript.jsonl) | 132 | `extract_hook` | 미지정 | `FAILED_BEFORE_OBSERVED_CHILD` | 136 |

spawn message 인자는 모두 불투명한 gAAAA 접두 문자열이다. 위임 지시의 평문은 관측되지 않았으며 해독·재구성하지 않았다. 인자의 길이와 SHA256만 조사 JSON에 별도로 기록했다.

`r1/s4-t055`의 실제 하위 에이전트 `/root/implementation`, thread `01a169a1-85d6-7b60-bcbe-9d1486224573`: `gpt-6-astra` / `medium`는 subAgentActivity 메타데이터 관측값이다. `turn/started` seq 165 (`inProgress`) → `turn/completed` seq 495 (`completed`); 하위 이벤트 209개, MCP 이벤트 0개. [원시 기록](codex-e2e-3-runs/20261024-full-router-14d2020/r1/tasks/s4-t055/transcript.jsonl).

하위 도구 요청: `exec` 6, `send_message` 1. 명령 cwd는 주 worktree와 그 frontend 하위 디렉터리였고, 공유 worktree 제거·Git 등록 해제는 각각 `true`, `true`로 확인됐다. 하위 turn 종료는 `VERIFIED`지만 독립 하위 인증은 `NOT_VERIFIED: no child-specific login-status/account-read evidence; parent ChatGPT Pro evidence exists.`, 독립 하위 프로세스 정리는 `NOT_VERIFIED: no separate child process identity or cleanup record; child turn completion and parent app-server exit are recorded.`다. 별도 하위 worktree는 관측되지 않았다.

프로토콜 비성공 호출 0회, load 의미 상태 비성공·반환 충돌 0회. 실제 실패와 부분 오류는 아래와 원시 기록에 보존했다.

관측된 MCP 프로토콜 오류와 load payload 오류·충돌은 없다.

미채점 반환 또는 반환 세트 미확인 세션 6개: `r1/s4-t176` (U=1, `UNRESOLVED_UNGRADED`), `r1/s4-t224` (U=1, `UNRESOLVED_UNGRADED`), `r2/s4-t211` (U=1, `CONFIRMED_RELEVANT_RETURN`), `r3/s4-t177` (U=1, `CONFIRMED_RELEVANT_RETURN`), `r3/s4-t026` (U=1, `UNRESOLVED_UNGRADED`), `r3/s4-t354` (U=1, `UNRESOLVED_UNGRADED`). 정확한 ID별 grade/null과 oracle 행 번호는 통합 관찰 JSON의 oracle_matches에 보존했다.

추출 경고 0건. [전체 경고](codex-e2e-3-runs/20261024-full-router-14d2020/observations-e2e3.json)의 warnings 배열을 참조한다.

## 적용 지침·설정·격리와 보존

[실제로 배포한 전체 AGENTS.md](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/AGENTS.md) · [원본 라우터](codex-e2e-3-preparation/router.original.SKILL.md) · [Codex 호스트 수정 diff](codex-e2e-3-preparation/router-codex.diff). 원본의 When, 3–8단계, Rules를 보존했고, 1–2단계는 승인된 Codex 문구다. AGENTS SHA256 `4cdfac9064f4f6dda0846dff9c8fe52a90dd2e65ba09cc494c735ea9c83bfa8a`. 각 worktree에 복사한 직후와 turn/start 직전에 실제 바이트를 확인한 기록을 감사했다.

실제 config ([원본 파일](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/config.toml))는 MCP 승인 수정이 이미 적용된 E2E-2와 바이트가 같다. skillfetch 서버만 `default_tools_approval_mode = "approve"`이고, 전역 승인 정책·셸 sandbox·네트워크 제한은 아래와 같다.

```toml
model = "gpt-6-astra"
model_reasoning_effort = "medium"
forced_login_method = "chatgpt"
approval_policy = "never"
sandbox_mode = "workspace-write"
web_search = "disabled"

[features]
apps = false
plugins = false
remote_plugin = false
hooks = false
memories = false
multi_agent = false
multi_agent_v2 = false
browser_use = false
browser_use_external = false
computer_use = false
image_generation = false
skill_mcp_dependency_install = false

[analytics]
enabled = false

[sandbox_workspace_write]
network_access = false

[mcp_servers.skillfetch]
default_tools_approval_mode = "approve"
command = "<skillfetch>/.venv/bin/skillfetch"
args = ["serve", "--index", "/tmp/skillfetch-codex-e2e-prep-20261023T224338/index"]
startup_timeout_sec = 60
tool_timeout_sec = 120

[mcp_servers.skillfetch.env]
PYTHONPATH = "/tmp/skillfetch-codex-e2e-prep-20261023T224338/source/src"
PYTHONDONTWRITEBYTECODE = "1"
HOME = "<home>"
```

실제 CLI/model/reasoning과 account/read의 chatgpt/pro, login status, API 키 환경변수 미상속이 모두 확인된 주 세션은 57/57개다. 나머지는 확인되지 않은 항목을 성공으로 세지 않는다. 각 주 세션의 실행 설정은 고정 s5의 새 detached worktree, 새 ephemeral thread, 격리된 HOME/CODEX_HOME을 사용한다. 등록 MCP는 skillfetch만이며 앱·플러그인·외부 스킬 자동 설치는 껐다. 셸 네트워크 차단은 MCP 서버 프로세스나 구독 추론 자체의 네트워크 금지로 해석하지 않는다. 하위 에이전트의 독립 인증·환경 격리는 이 주 세션 검사로 입증하지 않는다.

반복은 r1→r2→r3 순서이며 동시 실행 4개, 세션 제한 2700초, 모델 응답 회차 상한 없음이다. 관측된 prompt 제출 57회 중 원문 일치 57회, 불일치 0회다. UTC 2026-10-23T16:35:53.455Z ~ 2026-10-23T17:07:23.934Z.

주 세션 정리 완료는 57/57개다. worktree 디렉터리·Git 등록·인증 symlink 및 세 반복의 소유 임시 루트 제거를 감사했다. 이 결과를 하위 에이전트의 독립 프로세스·인증 정리 확인으로 확대하지 않는다. 원시 transcript, 종료 상태, 오류, 고정 소스·인덱스 지문은 보존했다.

| 고정 입력 | SHA256 또는 commit | 증거 |
|---|---|---|
| skillfetch 소스 | `14d2020f1275e10a272eb46575c9bd6d4a2182e4` | [소스·인덱스 지문](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/source-preflight.json) |
| fastapi s5 | `2b38acb4586092ef0318bc6a8ab36436ba8fc09a` | [r1 manifest](codex-e2e-3-runs/20261024-full-router-14d2020/r1/manifest.json) |
| nextjs s5 | `2a1df71575f0c45a0f7a999bf77f4286d81e8706` | [r1 manifest](codex-e2e-3-runs/20261024-full-router-14d2020/r1/manifest.json) |
| tasks | `d8822df5b8afeb587fc209218ca3f81fbe9ec3153acb66348c3f6a132306e572` | [고정 입력](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/tasks.jsonl) |
| agents | `4cdfac9064f4f6dda0846dff9c8fe52a90dd2e65ba09cc494c735ea9c83bfa8a` | [고정 입력](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/AGENTS.md) |
| config | `69fb11307213035fce1442078304ff1891a1b4b22e5254a75d9387884bb590e1` | [고정 입력](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/config.toml) |
| source_preflight | `6bb7b3d73e521b223670c9fc05b960c93577c7abfe127f8fa0faaf1e23fb931d` | [고정 입력](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/source-preflight.json) |
| cloud_skills | `bc7b79e1b6590794a9a245ae3d8038685bad313692cbac7cbd68697c6e0d4cd4` | [고정 입력](codex-e2e-3-runs/20261024-full-router-14d2020/inputs/cloud-skills.json) |
| oracle-4-0 | `7db50e73c7dfd6b0b810ba65231fd1475a25a563651310592c88da23795e108c` | [누적 oracle](stage5/oracle-4-0.jsonl) |
| runtime audit (원래 FAIL 보존) | `9e1e26506dabe3dc6b8d2ce56804361542c3c2aa28ff4da86cbffdb88ff1e5e4` | [검증 증거](codex-e2e-3-runs/20261024-full-router-14d2020/audit-verification.json) |
| 하위 에이전트 조사 | `965b9de431a8c60febf991d681a8280170c62538638481a9bd1bd145b329f91b` | [검증 증거](codex-e2e-3-runs/20261024-full-router-14d2020/child-agent-findings.json) |
| 독립 지표 검증 | `c6fe0b7c49a8be54f510529aaee84e81e689ed9fb51b9564fd244c797b6b9638` | [검증 증거](codex-e2e-3-runs/20261024-full-router-14d2020/independent-metrics-verification.json) |
| 이전 codex-e2e.md | `db5b22600f4d20048f5669a39221335d8b5f7106cd1824d4b2deb57848d139c5` | [변경하지 않은 보고서](codex-e2e.md) |
| 이전 codex-e2e-2.md | `bc8e4d41b17785b3408c5cb62519d55dd32d77751eaedc751d32d019e437effc` | [변경하지 않은 보고서](codex-e2e-2.md) |

소스 파일 238개와 인덱스 파일 6개의 개별 지문은 소스 preflight에 있다. 세션별 전후 검증과 현재 동일성은 감사 기록에 남겼다. 인덱스 파일 지문:

| 인덱스 파일 | SHA256 |
|---|---|
| `constraints.jsonl` | `7fcc7ff0d126846d15dde6bbb7461029c03b78cb0b37ad4f137dedf7de645f6c` |
| `dupgroups.json` | `502375be66f581285c99a8961687f7f6a593c1a80e67a3ab2c81afa90b1b7bba` |
| `manifest.json` | `cd4f46aa4af7a0e5c8acc1d0749987eb0d4ed4ea8f7c01c4c17fd104be20574d` |
| `pairs.jsonl` | `1ec67b12030b39b823b8f078f3320f46496652bd8f397e32b9ab2842c1fba976` |
| `rejected.jsonl` | `df1e2c16830ff5636b1b17552e1cfca27700b1a78bea0a80d0bfbb0098b0f509` |
| `skills.jsonl` | `19dcf0b91e57d329be10ddca5b0c3fad1cf1d6f605fd1192aa070b99bd5c44c4` |

보고서와 질의 JSON은 모델 호출 없이 종료된 기록에서 생성했다. 결과물 품질, 스킬 지침의 준수·유용성, 반복 간 차이의 통계적 유의성은 평가하지 않았다. 원시 로그를 별도로 읽은 지표 검증 `PASS`는 런타임 감사 `FAIL`를 대체하지 않는다. 격리 요건 전체 통과나 스킬 선택의 정답을 보증하지 않는다.

[실행기](codex-e2e-3-runner.cjs) · [추출기](codex-e2e-3-extract.cjs) · [감사기](codex-e2e-3-verify.cjs) · [렌더러](codex-e2e-3-render.cjs)

## 보완: 관련 스킬 없는 태스크의 로드와 하위 에이전트 세션 제외

새 세션 실행 없이 [기존 57개 관측](codex-e2e-3-runs/20261024-full-router-14d2020/observations-e2e3.json)과 같은 누적 `oracle-4-0.jsonl`로 계산했다. 기존 본문·원시 기록·감사 FAIL 판정은 유지한다.

### 관련 스킬이 없는 2개 태스크의 실제 로드

누적 oracle에 grade ≥ 2인 스킬이 없는 `s4-t354`, `s4-t342`는 **각각 3/3세션, 합계 6/6세션(100%)에서 스킬을 로드했다.** 반환 ID는 아래와 같다. 같은 ID도 서로 다른 세션의 반환이면 각각 센다.

| 태스크 | 반복 | 로드 | load_skills가 반환한 스킬 ID | 기존 oracle 등급 |
|---|---|---|---|---|
| s4-t354 | r1 | 예 | `uasl/verification-loop@39d9be23cf50` | 1 |
| s4-t354 | r2 | 예 | `uasl/verification-loop@39d9be23cf50` | 1 |
| s4-t354 | r3 | 예 | `uasl/python-error-handling@8dc34883a143` | 미채점(pool 밖) |
| s4-t342 | r1 | 예 | `uasl/coding-standards@f854e26a9529` | 1 |
| s4-t342 | r2 | 예 | `uasl/verification-loop@39d9be23cf50` | 1 |
| s4-t342 | r3 | 예 | `uasl/verification-loop@39d9be23cf50` | 1 |

총 반환은 6개 세션–ID 쌍(고유 ID 3개)이며, 기존 grade 1이 5개, 미채점이 1개다. “관련 스킬 없음”은 현재 oracle의 태스크 분류이며, 미채점 반환을 0점이나 무관으로 새로 판정하지 않았다.

### 실제 하위 에이전트 실행 세션을 제외한 지표

[하위 에이전트 조사](codex-e2e-3-runs/20261024-full-router-14d2020/child-agent-findings.json)에서 실제 하위 에이전트가 실행된 주 세션은 **`r1/s4-t055`**다. 이 세션만 제외하고, 생성 시도만 실패한 `r2/s4-t055`, `r3/s4-t055`는 유지했다. 제외한 세션의 반환은 `uasl/zen@f72229d0a781` 1개, 기존 grade 1이므로 R=0, N=1, U=0이며 적중 세션이 아니다.

| 계산 대상 | 로드 세션 | 관련 태스크 적중(loaded related) | 전체 로드 세션 적중 | graded micro precision | graded macro precision(채점 세션 수) | R / N / U |
|---|---:|---:|---:|---:|---:|---:|
| 기존 전체 | 57/57 | 26/51 (51.0%) | 26/57 (45.6%) | 29/56 (51.8%) | 49.1% (53) | 29 / 27 / 6 |
| `r1/s4-t055`만 제외 | 56/56 | **26/50 (52.0%)** | 26/56 (46.4%) | **29/55 (52.7%)** | **50.0% (52)** | 29 / 26 / 6 |

적중 분모와 precision 정의는 본문과 같다. 미채점 6개는 precision 분모에서 제외했고, 미채점만 반환한 로드 세션 4개는 macro 평균에서 제외했다. 관련 태스크의 미해결 적중 세션은 두 행 모두 3개로 남는다. 관련 스킬 없는 태스크의 로드도 두 행 모두 6/6이다. 이 제외 계산은 민감도 확인이며 원래 57세션의 결과나 런타임 감사 FAIL을 대체하지 않는다.
