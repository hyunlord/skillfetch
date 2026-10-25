# blind ranking — unblinded

> **판정자 1명(Claude, 이 실험을 운영한 세션)의 결과만 집계했다. 두 번째 판정자는 두지 않았다.**
> 이유: 세트 안 결과물이 거의 구별되지 않는다 — s1-nx-05 PNG 4개는 픽셀 동일, s1-nx-04·s1-nx-03·s1-nx-01은 픽셀 동일 쌍이 있고, (a) AI-룩 체크리스트 해당 수는 24개 스크린샷 전부 0. 추가 판정자가 바꿀 수 있는 범위가 작다고 보고 생략했다.
>
> **비블라인드 노출 (기록)**
> - docs-blind 생성 직전 명령 출력에 `s1-nx-10` 세션별 diff 줄 수가 조건·rep과 함께 표시되었다(A r1 102, A r2 94, B r1 98, B r2 105, C r1 102, C r2 94 — 전체 diff 기준, index 줄 제거 전). 따라서 `docs/s1-nx-10` 판정은 블라인드가 아닐 수 있다. `s1-fa-10`은 6세션 모두 40줄로 같아 이 경로의 누출 없음.
> - 판정자는 판정 지시 전에 `runs/` 세션 기록을 보고서 작성에 사용했다. 키 파일(`screens-key.jsonl`, `docs-key.jsonl`)은 unblind 스크립트 실행 전까지 읽지 않았다.
> - 모바일(375px) PNG는 s1-nx-04에만 있어 나머지 세트는 데스크톱만 판정했다.


sources: `blind-ranking.md`; mapping: `screens-key.jsonl`, `docs-key.jsonl`. 1 = best. 정규화 순위 = (rank − 1) / (n − 1), 0 = 최상.

# 판정 파일: blind-ranking.md

## s1-fa-03

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 56de6e73 | B | r1 | 1 | 0 | 5 |
| 07ea32b5 | C | r1 | 2 | 0 | 4 |
| 1ebaa4de | A | r2 | 2 | 0 | 4 |
| 61724689 | A | r1 | 2 | 0 | 4 |
| 69c12be9 | C | r2 | 2 | 0 | 4 |
| f4ba5d31 | B | r2 | 2 | 0 | 4 |

## s1-nx-01

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 6822978b | C | r2 | 1 | 0 | 4 |
| 84def7fd | A | r1 | 1 | 0 | 4 |
| afb9ab59 | C | r1 | 3 | 0 | 3 |
| bf5a44f4 | A | r2 | 4 | 0 | 3 |

## s1-nx-03

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 23d154f6 | C | r2 | 1 | 0 | 4 |
| 348616f4 | C | r1 | 1 | 0 | 4 |
| 16cff88f | A | r1 | 3 | 0 | 3 |
| 2d5d9a1e | A | r2 | 3 | 0 | 3 |

## s1-nx-04

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 62acb054 | B | r2 | 1 | 0 | 4 |
| a16b770d | C | r1 | 1 | 0 | 4 |
| a5c44d0e | B | r1 | 1 | 0 | 4 |
| bc2accda | C | r2 | 1 | 0 | 4 |
| f494acac | A | r2 | 1 | 0 | 4 |
| fc13e3b3 | A | r1 | 1 | 0 | 4 |

## s1-nx-05

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 2a3587ab | C | r1 | 1 | 0 | 4 |
| 643b308b | A | r2 | 1 | 0 | 4 |
| c47d8429 | C | r2 | 1 | 0 | 4 |
| f97cb3d1 | A | r1 | 1 | 0 | 4 |

## docs/s1-fa-10

| code | 조건 | rep | 순위 | 머지 1-5 |
|---|---|---|---|---|
| 2fba35d2 | C | r2 | 1 | 5 |
| 5b127b8f | B | r1 | 1 | 5 |
| 712edc62 | B | r2 | 1 | 5 |
| a05ec8c6 | C | r1 | 1 | 5 |
| fdeda011 | A | r2 | 1 | 5 |
| ea1f7ebd | A | r1 | 6 | 4 |

## docs/s1-nx-10

| code | 조건 | rep | 순위 | 머지 1-5 |
|---|---|---|---|---|
| 2c24471d | B | r2 | 1 | 5 |
| d11fd9a5 | C | r1 | 1 | 5 |
| 2cafb5ec | B | r1 | 3 | 5 |
| 63378a4c | C | r2 | 3 | 5 |
| 9097e1fa | A | r2 | 3 | 5 |
| e3218b3a | A | r1 | 3 | 5 |

# 조건별 집계 (평균)

| 판정 파일 | 세트 묶음 | 지표 | 조건별 평균 (n) |
|---|---|---|---|
| blind-ranking.md | docs A+B+C | 머지 1-5 | A 4.75 (4), B 5.00 (4), C 5.00 (4) |
| blind-ranking.md | docs A+B+C | 순위 | A 3.25 (4), B 1.50 (4), C 1.50 (4) |
| blind-ranking.md | docs A+B+C | 정규화 순위 | A 0.45 (4), B 0.10 (4), C 0.10 (4) |
| blind-ranking.md | screens A+B+C | (a) AI느낌 수 | A 0.00 (4), B 0.00 (4), C 0.00 (4) |
| blind-ranking.md | screens A+B+C | (b) 쓸만함 1-5 | A 4.00 (4), B 4.25 (4), C 4.00 (4) |
| blind-ranking.md | screens A+B+C | 순위 | A 1.50 (4), B 1.25 (4), C 1.50 (4) |
| blind-ranking.md | screens A+B+C | 정규화 순위 | A 0.10 (4), B 0.05 (4), C 0.10 (4) |
| blind-ranking.md | screens A+C | (a) AI느낌 수 | A 0.00 (6), C 0.00 (6) |
| blind-ranking.md | screens A+C | (b) 쓸만함 1-5 | A 3.50 (6), C 3.83 (6) |
| blind-ranking.md | screens A+C | 순위 | A 2.17 (6), C 1.33 (6) |
| blind-ranking.md | screens A+C | 정규화 순위 | A 0.39 (6), C 0.11 (6) |
| blind-ranking.md | 전체 docs | 머지 1-5 | A 4.75 (4), B 5.00 (4), C 5.00 (4) |
| blind-ranking.md | 전체 docs | 순위 | A 3.25 (4), B 1.50 (4), C 1.50 (4) |
| blind-ranking.md | 전체 docs | 정규화 순위 | A 0.45 (4), B 0.10 (4), C 0.10 (4) |
| blind-ranking.md | 전체 screens | (a) AI느낌 수 | A 0.00 (10), B 0.00 (4), C 0.00 (10) |
| blind-ranking.md | 전체 screens | (b) 쓸만함 1-5 | A 3.70 (10), B 4.25 (4), C 3.90 (10) |
| blind-ranking.md | 전체 screens | 순위 | A 1.90 (10), B 1.25 (4), C 1.40 (10) |
| blind-ranking.md | 전체 screens | 정규화 순위 | A 0.27 (10), B 0.05 (4), C 0.11 (10) |
