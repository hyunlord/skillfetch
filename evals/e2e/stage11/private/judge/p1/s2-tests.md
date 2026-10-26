## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 3111393b | 5 | 5 | 5 | 5 | 5 | 5 | Every function/frequency/option is covered with exact date lists and message fragments, all the documented edge cases are there (incl. 2100, -31 SKIP/CLAMP, scan-limit reset), and the limit=0 bug is recorded as a strict xfail; 100% line/branch. |
| a1719086 | 5 | 5 | 5 | 5 | 5 | 5 | Thorough example tests plus hypothesis property tests (round trip, ordering, next_after/between agreement); real bugs (unsorted-BYDAY round trip, limit=0, date.max overflow) are recorded as strict xfails; adds the hypothesis dev dependency; 100% coverage. |
| b3e0a5a7 | 5 | 5 | 5 | 5 | 5 | 5 | Full coverage of the API and edge cases, exact values throughout, a deterministic round-trip grid (>100 rules), and the known bugs as strict xfails; clean classes and helpers. |
| c16e80ef | 5 | 5 | 5 | 4 | 4 | 5 | Covers everything with exact assertions and strict xfails for the round-trip and date.max bugs, but locks in limit=0 yielding one date as expected behaviour, and includes a trivial MAX_SCAN_PERIODS constant test and a scan-limit test that never trips the limit. |
| e5cee966 | 5 | 5 | 5 | 5 | 4 | 5 | Very complete, with extra strict xfails for directly built rules (unsorted or duplicate BYDAY); a few length-only asserts, and limit=0 yielding one date is locked in as correct while the other bugs are marked xfail. |
| ffa60388 | 5 | 5 | 5 | 5 | 4 | 5 | Flat but well-named parametrised tests with exact messages, -30 SKIP/CLAMP, scan-limit reset and a check that exceptions are not chained; limit=0 yielding one date is locked in as intended behaviour. |

1. 3111393b, a1719086, b3e0a5a7
4. e5cee966, ffa60388
6. c16e80ef
