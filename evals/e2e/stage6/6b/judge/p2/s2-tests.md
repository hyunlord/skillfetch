## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 146a0ac7 | 5 | 5 | 5 | 5 | 5 | 5 | Covers every documented edge case. A brute-force day-by-day oracle checks 14 rules x 5 starts, and an exhaustive grid checks the round trip. Error messages are matched exactly. Strict xfails pin 3 real bugs (unsorted BYDAY, limit=0, date.max overflow). 100% line/branch coverage. |
| ee8f6b82 | 5 | 5 | 5 | 5 | 5 | 5 | 1000-rule seeded round-trip property test, also run on messy case/spacing input. Error messages are matched exactly, including values. Count/limit checks use exact date lists. Strict xfails pin 4 real bugs. Clean class layout. |
| 577bce3f | 5 | 5 | 5 | 5 | 5 | 5 | All listed edge cases are pinned with exact date lists and messages, including negative days missing under both SKIP and CLAMP, and the scan-limit reset. Strict xfails cover 4 real bugs. Ordinals are tested through the public describe(). |
| dc309466 | 5 | 5 | 5 | 5 | 5 | 5 | Seeded random round-trip property test. Parametrised cases have readable ids and exact messages. Adds an increasing / not-before-start invariant test. Flat function layout, but section headers and names keep it easy to follow. |
| adcb0616 | 5 | 5 | 4 | 5 | 5 | 5 | Thorough: exact messages, xfails pin real bugs (unsorted BYDAY, date.max checked for all 4 frequencies), never-matching tested in both occurrences and next_after. Limit/count tests only check lengths. |
| 1dcb4f98 | 5 | 5 | 4 | 5 | 5 | 5 | Very broad: direct parametrised tables for _month_day and _add_months, scan-limit tests, date.max xfail. Rule-validation matches use loose fragments ("INTERVAL", "BYDAY"), and some limit tests only check lengths. |
| c30ff225 | 5 | 4 | 5 | 5 | 5 | 4 | Clean and correct, and covers the rubric's list with exact values. Thinner than the rest: DAILY has only 3 tests, the round trip is tested on examples only, there is a single xfail, and it does not probe limit=0 or date.max. |
| b549d100 | 5 | 5 | 4 | 5 | 4 | 4 | Good coverage of edge cases, including the scan limit and clamp collisions. One strict xfail asserts behaviour the module never documents (INTERVAL=1_0 should be rejected). Rule-validation message matches are loose. |
| c5bd93ce | 5 | 4 | 4 | 4 | 5 | 4 | The never-matching case is tested only with a monkeypatched MAX_SCAN_PERIODS, not as a real rule. The empty-input tests check no message, and validation fragments are loose. Leans on private-helper tests, and a stray brute-force test sits after the package-export test. |

1. 146a0ac7, ee8f6b82, 577bce3f
4. dc309466, adcb0616, 1dcb4f98
7. c30ff225
8. b549d100
9. c5bd93ce
