## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| fe29a067 | 5 | 5 | 5 | 4 | 5 | 5 | All public functions, frequencies and options covered with exact dates and full message fragments; all listed edge cases incl. -31 SKIP/CLAMP, century leap day, scan-limit reset; 100% line/branch, rules.py untouched; flat file with long one-line asserts |
| 32d9eb16 | 5 | 5 | 5 | 5 | 5 | 5 | Class-per-area layout with date helpers, exact date lists and messages, all documented edge cases, strict xfails for real defects (unsorted BYDAY round trip, date.max overflow), package export check; 100% coverage, module untouched |
| 38f302cf | 5 | 5 | 5 | 5 | 5 | 5 | Thorough and well organised, matches full error messages, covers every listed edge case incl. clamped duplicates and scan limit, strict xfails for BYDAY/BYMONTHDAY round-trip and date.max defects; 100% coverage, module untouched |
| 09207a2b | 5 | 5 | 5 | 5 | 5 | 5 | Complete coverage in classes, exact dates/messages, all edge cases (31st SKIP/CLAMP, -30 in Feb, 2096 leap, COUNT+UNTIL, between bounds, round trip, never-matching), strict xfails for real defects; 100% coverage; tests private `_ordinal` directly |
| 5d620c01 | 5 | 5 | 5 | 5 | 5 | 5 | Most extensive suite: every function/option, exact date lists, coincident-day collapse, scan-limit reset, re-export check, strict xfails for unsorted BYDAY/UNTIL and limit=0; 100% coverage, module untouched |
| 06d2f141 | 5 | 5 | 5 | 4 | 5 | 5 | Full coverage with exact dates/messages, all documented edge cases incl. -31 SKIP/CLAMP, 2100 non-leap, monkeypatched scan limit, strict xfails for hand-built Rule defects; 100% coverage; flat single file, a few length-only checks |

1. 32d9eb16, 38f302cf, 09207a2b, 5d620c01
5. fe29a067, 06d2f141
