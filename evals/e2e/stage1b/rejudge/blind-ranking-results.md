# blind ranking — unblinded

sources: `blind-ranking.md`; mapping: key files next to the blind folders in `rejudge/`. 1 = best. 정규화 순위 = (rank − 1) / (n − 1), 0 = 최상.

# 판정 파일: blind-ranking.md

## s1b-nx-landing

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 735036d4 | B | r2 | 1 | 0 | 5 |
| abd0a2d8 | C2 | r2 | 1 | 0 | 5 |
| 39bba881 | C | r2 | 3 | 2 | 5 |
| 3e7828f3 | B | r1 | 4 | 0 | 4 |
| 9d2a4569 | C2 | r1 | 4 | 0 | 4 |
| 71c78cb4 | C | r1 | 6 | 1 | 4 |
| 71fcd341 | A | r1 | 6 | 1 | 4 |
| a675c2d9 | A | r2 | 6 | 1 | 4 |

## s1b-fa-landing

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 6ed168c4 | C2 | r1 | 1 | 1 | 5 |
| 9c86bcda | B | r2 | 1 | 1 | 5 |
| a53cd4ff | B | r1 | 1 | 1 | 5 |
| c1f9daa4 | C2 | r2 | 1 | 1 | 5 |
| 3f3bb8d9 | C | r2 | 5 | 2 | 5 |
| d91526f5 | C | r1 | 6 | 3 | 4 |
| 35af4c58 | A | r1 | 7 | 3 | 3 |
| e59c75ef | A | r2 | 7 | 3 | 3 |

## plans/s1b-fa-tags-plan

| code | 조건 | rep | 순위 | 검증 방법 1-5 | 단계 구체성 1-5 | 리스크 1-5 | 순서 1-5 | 파일 명시 1-5 | 플랜 준수 1-5 |
|---|---|---|---|---|---|---|---|---|---|
| 13017b68 | B | r2 | 1 | 5 | 5 | 4 | 5 | 5 | 5 |
| b20215c8 | B | r1 | 1 | 5 | 5 | 4 | 5 | 5 | 5 |
| dd79f213 | A | r1 | 3 | 4 | 4 | 3 | 4 | 4 | 5 |
| 62d1b5d1 | A | r2 | 4 | 4 | 4 | 2 | 4 | 4 | 5 |
| 0cc603f8 | C | r2 | 5 | 4 | 4 | 2 | 4 | 4 | 5 |
| e5e778c5 | C2 | r2 | 5 | 4 | 4 | 2 | 4 | 4 | 5 |
| 2aaf174d | C2 | r1 | 7 | 4 | 4 | 2 | 4 | 4 | 3 |
| 7c401036 | C | r1 | 8 | 4 | 4 | 2 | 4 | 4 | 2 |

# 조건별 집계 (평균)

| 판정 파일 | 세트 묶음 | 지표 | 조건별 평균 (n) |
|---|---|---|---|
| blind-ranking.md | plans A+B+C+C2 | 검증 방법 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 단계 구체성 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 리스크 1-5 | A 2.50 (2), B 4.00 (2), C 2.00 (2), C2 2.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 순서 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 순위 | A 3.50 (2), B 1.00 (2), C 6.50 (2), C2 6.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 정규화 순위 | A 0.36 (2), B 0.00 (2), C 0.79 (2), C2 0.71 (2) |
| blind-ranking.md | plans A+B+C+C2 | 파일 명시 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | plans A+B+C+C2 | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.50 (2), C2 4.00 (2) |
| blind-ranking.md | screens A+B+C+C2 | (a) AI느낌 수 | A 2.00 (4), B 0.50 (4), C 2.00 (4), C2 0.50 (4) |
| blind-ranking.md | screens A+B+C+C2 | (b) 쓸만함 1-5 | A 3.50 (4), B 4.75 (4), C 4.50 (4), C2 4.75 (4) |
| blind-ranking.md | screens A+B+C+C2 | 순위 | A 6.50 (4), B 1.75 (4), C 5.00 (4), C2 1.75 (4) |
| blind-ranking.md | screens A+B+C+C2 | 정규화 순위 | A 0.79 (4), B 0.11 (4), C 0.57 (4), C2 0.11 (4) |
| blind-ranking.md | 전체 plans | 검증 방법 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | 전체 plans | 단계 구체성 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | 전체 plans | 리스크 1-5 | A 2.50 (2), B 4.00 (2), C 2.00 (2), C2 2.00 (2) |
| blind-ranking.md | 전체 plans | 순서 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | 전체 plans | 순위 | A 3.50 (2), B 1.00 (2), C 6.50 (2), C2 6.00 (2) |
| blind-ranking.md | 전체 plans | 정규화 순위 | A 0.36 (2), B 0.00 (2), C 0.79 (2), C2 0.71 (2) |
| blind-ranking.md | 전체 plans | 파일 명시 1-5 | A 4.00 (2), B 5.00 (2), C 4.00 (2), C2 4.00 (2) |
| blind-ranking.md | 전체 plans | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.50 (2), C2 4.00 (2) |
| blind-ranking.md | 전체 screens | (a) AI느낌 수 | A 2.00 (4), B 0.50 (4), C 2.00 (4), C2 0.50 (4) |
| blind-ranking.md | 전체 screens | (b) 쓸만함 1-5 | A 3.50 (4), B 4.75 (4), C 4.50 (4), C2 4.75 (4) |
| blind-ranking.md | 전체 screens | 순위 | A 6.50 (4), B 1.75 (4), C 5.00 (4), C2 1.75 (4) |
| blind-ranking.md | 전체 screens | 정규화 순위 | A 0.79 (4), B 0.11 (4), C 0.57 (4), C2 0.11 (4) |
