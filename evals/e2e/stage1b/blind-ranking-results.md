# blind ranking — unblinded

sources: `blind-ranking.md`; mapping: key files next to the blind folders in `stage1b/`. 1 = best. 정규화 순위 = (rank − 1) / (n − 1), 0 = 최상.

# 판정 파일: blind-ranking.md

## s1b-nx-landing

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| 05e168f2 | B | r1 | 1 | 0 | 5 |
| 6470ec53 | B | r2 | 1 | 0 | 5 |
| 656c8839 | A | r2 | 3 | 1 | 4 |
| 6ea47996 | A | r1 | 3 | 1 | 4 |
| 06793f03 | C | r2 | 5 | 2 | 4 |
| 16a46e33 | C | r1 | 5 | 2 | 4 |

## s1b-fa-landing

| code | 조건 | rep | 순위 | (a) AI느낌 수 | (b) 쓸만함 1-5 |
|---|---|---|---|---|---|
| de0e486f | B | r2 | 1 | 1 | 5 |
| f36cbfb5 | B | r1 | 1 | 1 | 5 |
| 6c8a0096 | C | r2 | 3 | 2 | 4 |
| 8521fa1c | C | r1 | 4 | 2 | 3 |
| de0824b8 | A | r2 | 4 | 2 | 3 |
| e544a0ab | A | r1 | 6 | 3 | 3 |

## plans/s1b-fa-tags-plan

| code | 조건 | rep | 순위 | 검증 방법 1-5 | 단계 구체성 1-5 | 리스크 1-5 | 순서 1-5 | 파일 명시 1-5 | 플랜 준수 1-5 |
|---|---|---|---|---|---|---|---|---|---|
| 0cd645aa | A | r1 | 1 | 5 | 5 | 4 | 5 | 5 | 5 |
| c92f3fba | B | r2 | 1 | 5 | 5 | 4 | 5 | 5 | 5 |
| f8953e63 | B | r1 | 1 | 5 | 5 | 4 | 5 | 5 | 5 |
| 829563bc | A | r2 | 4 | 5 | 5 | 2 | 4 | 5 | 5 |
| a4618ba1 | C | r2 | 5 | 4 | 4 | 2 | 5 | 5 | 4 |
| 0e62f86b | C | r1 | 5 | 5 | 5 | 2 | 5 | 5 | 2 |

# 조건별 집계 (평균)

| 판정 파일 | 세트 묶음 | 지표 | 조건별 평균 (n) |
|---|---|---|---|
| blind-ranking.md | plans A+B+C | 검증 방법 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| blind-ranking.md | plans A+B+C | 단계 구체성 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| blind-ranking.md | plans A+B+C | 리스크 1-5 | A 3.00 (2), B 4.00 (2), C 2.00 (2) |
| blind-ranking.md | plans A+B+C | 순서 1-5 | A 4.50 (2), B 5.00 (2), C 5.00 (2) |
| blind-ranking.md | plans A+B+C | 순위 | A 2.50 (2), B 1.00 (2), C 5.00 (2) |
| blind-ranking.md | plans A+B+C | 정규화 순위 | A 0.30 (2), B 0.00 (2), C 0.80 (2) |
| blind-ranking.md | plans A+B+C | 파일 명시 1-5 | A 5.00 (2), B 5.00 (2), C 5.00 (2) |
| blind-ranking.md | plans A+B+C | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.00 (2) |
| blind-ranking.md | screens A+B+C | (a) AI느낌 수 | A 1.75 (4), B 0.50 (4), C 2.00 (4) |
| blind-ranking.md | screens A+B+C | (b) 쓸만함 1-5 | A 3.50 (4), B 5.00 (4), C 3.75 (4) |
| blind-ranking.md | screens A+B+C | 순위 | A 4.00 (4), B 1.00 (4), C 4.25 (4) |
| blind-ranking.md | screens A+B+C | 정규화 순위 | A 0.60 (4), B 0.00 (4), C 0.65 (4) |
| blind-ranking.md | 전체 plans | 검증 방법 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| blind-ranking.md | 전체 plans | 단계 구체성 1-5 | A 5.00 (2), B 5.00 (2), C 4.50 (2) |
| blind-ranking.md | 전체 plans | 리스크 1-5 | A 3.00 (2), B 4.00 (2), C 2.00 (2) |
| blind-ranking.md | 전체 plans | 순서 1-5 | A 4.50 (2), B 5.00 (2), C 5.00 (2) |
| blind-ranking.md | 전체 plans | 순위 | A 2.50 (2), B 1.00 (2), C 5.00 (2) |
| blind-ranking.md | 전체 plans | 정규화 순위 | A 0.30 (2), B 0.00 (2), C 0.80 (2) |
| blind-ranking.md | 전체 plans | 파일 명시 1-5 | A 5.00 (2), B 5.00 (2), C 5.00 (2) |
| blind-ranking.md | 전체 plans | 플랜 준수 1-5 | A 5.00 (2), B 5.00 (2), C 3.00 (2) |
| blind-ranking.md | 전체 screens | (a) AI느낌 수 | A 1.75 (4), B 0.50 (4), C 2.00 (4) |
| blind-ranking.md | 전체 screens | (b) 쓸만함 1-5 | A 3.50 (4), B 5.00 (4), C 3.75 (4) |
| blind-ranking.md | 전체 screens | 순위 | A 4.00 (4), B 1.00 (4), C 4.25 (4) |
| blind-ranking.md | 전체 screens | 정규화 순위 | A 0.60 (4), B 0.00 (4), C 0.65 (4) |
