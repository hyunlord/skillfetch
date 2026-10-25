# Codex blind judging: bundle (3)

조건 매핑 및 기존 판정을 열지 않고 blind-p1의 TASK.md, diff.patch, check.md와 rubric-b3.md만 사용했다. 후보 실행이나 외부 API 호출은 하지 않았다. 총점은 기준 점수의 산술평균이 아닌 수용성 판정이다.

증거 충돌: t004의 2f6ab686/a64942e2/f3d4b454/f6997c9a/fb34fdf8/fec61524 check.md에는 Item 필드 검사가 FAIL로 기록되어 있다. 이 FAIL은 그대로 보존하되, 각 diff에는 ItemBase.due_date와 이를 상속한 Item 및 reminder_sent_at이 실제로 보이고 같은 check에서 migration/model 일치 검사가 PASS다. 따라서 이 정적 판정에서는 상속 필드를 누락으로 간주하지 않았다. 검사 원인이나 실행 결과를 새로 검증한 것은 아니다.

## s6b-t004

| code | 기능 완결 1-5 | 운영 적합 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| 2f6ab686 | 5 | 4 | 4 | due_date 상속·마이그레이션, 시간별 UTC 일정과 행 잠금은 갖췄으나 신규 태스크 테스트가 없고 잠금 재조회에서 예정일을 재확인하지 않는다. |
| 33a37583 | 5 | 4 | 4 | 15분 주기와 잠금 후 전체 조건 재검사는 좋지만 새 동작 테스트가 없고 입력 datetime의 시간대 제약이 없다. |
| 59b35b8d | 5 | 4 | 4 | AwareDatetime·UTC 24시간 창·행 잠금·실패 rollback을 갖췄으나 신규 테스트가 없고 잠금 후 예정일 조건을 재검사하지 않는다. |
| a64942e2 | 5 | 4 | 4 | 상속 필드·마이그레이션과 시간별 UTC 일정, 개별 트랜잭션 잠금은 완결됐으나 신규 테스트와 잠금 후 예정일 재검사가 없다. |
| fb34fdf8 | 5 | 4 | 4 | 시간별 일정·행 잠금·발송 실패 시 미표시 및 날짜 변경/중복 방지 테스트가 있으나 잠금 후 예정일을 재확인하지 않는 경합 틈은 남는다. |
| 6df44a4a | 4 | 3 | 3 | 시간별 일정과 순차 재발송 방지 테스트는 있으나 잠금 없이 후보를 일괄 읽어 겹친 실행이 같은 메일을 중복 발송할 수 있다. |
| f3d4b454 | 4 | 3 | 3 | 일일 일정·오늘 포함 catch-up은 있지만 잠금 없는 전송은 중복 위험이 있고 실패 항목을 같은 날 재시도하지 않으며 신규 테스트도 없다. |
| fec61524 | 4 | 3 | 3 | 시간별 재시도와 정상 전송 후 sent 표시는 있으나 잠금 없이 일괄 조회하여 중복 발송 가능하며 신규 태스크 테스트가 없다. |
| f6997c9a | 4 | 2 | 3 | 필드·템플릿·기본 발송은 있으나 자정 1회 조회 후 생성된 내일 만기 항목과 SMTP 실패 항목을 놓치고 동시 실행 중복도 막지 못한다. |

1. 2f6ab686, 33a37583, 59b35b8d, a64942e2, fb34fdf8
6. 6df44a4a, f3d4b454, fec61524
9. f6997c9a

## s6b-t133

| code | 레이어 캐시 1-5 | 실행 동작 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| 4c95c839 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| 747190bc | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| 77f00a88 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| 9d2de06d | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| b64cfb35 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| d7efa73e | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| e7c0a985 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| e8017e36 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |
| eaf86736 | 5 | 5 | 5 | manifest와 lockfile 선복사, npm ci 캐시 마운트, 소스 후복사 및 next build→npm start:3000을 모두 충족한다; Docker 실빌드는 제공 검사에서 미확인이다. |

1. 4c95c839, 747190bc, 77f00a88, 9d2de06d, b64cfb35, d7efa73e, e7c0a985, e8017e36, eaf86736

## s6b-t179

| code | 중복 제거 정확성 1-5 | 검증 출력 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| 02d8febe | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| 339e5172 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| 3495e763 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| 7dcce826 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| 9549d007 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| ce208202 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| cf52b639 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| df0b7532 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |
| e8f25480 | 5 | 5 | 5 | 기존 engine·한 트랜잭션의 row_number 삭제로 가장 이른 행을 보존하고 id 동률·NULL 처리를 명시하며 UTC 일별 전후/삭제 수를 출력한다. |

1. 02d8febe, 339e5172, 3495e763, 7dcce826, 9549d007, ce208202, cf52b639, df0b7532, e8f25480

## s6b-t354

| code | 검사 정확성 1-5 | 변경 범위 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|
| 1b741e0b | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| 4c9defb9 | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| 64aabebc | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| 7aecd146 | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| 891d7f5b | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| 90edf13a | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| d8803865 | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| e27b07d0 | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |
| e909eebf | 5 | 5 | 5 | DB current_heads와 script heads의 집합을 비교하여 불일치 시 명확히 중단하며 init_db 전에 호출한다; 새 함수·호출 외 무관한 변경이 없다. |

1. 1b741e0b, 4c9defb9, 64aabebc, 7aecd146, 891d7f5b, 90edf13a, d8803865, e27b07d0, e909eebf

