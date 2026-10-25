## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 08b44092 | 5 | 5 | 5 | 5 | 5 | 5 | Covers every function and option. Exact error messages including the offending values. Exhaustive to_string/parse_rule round-trip grid plus a brute-force oracle across 14 rules x 5 starts. Strict xfails pin real bugs (unsorted BYDAY, limit=0, overflow at date.max). 100% line/branch coverage, all pass. |
| 84ae941f | 5 | 5 | 5 | 5 | 5 | 5 | Long table of parse errors with ids and exact message fragments. Property round trip over 1000 random rules, also run with messy case and spacing. Every documented edge case is pinned down. Strict xfails with raises= for the overflow bugs plus limit=0. Clean classes, all pass. |
| 96850034 | 5 | 5 | 4 | 4 | 5 | 5 | Full coverage of functions and edge cases, with a seeded random round trip and scan-limit monkeypatch tests. Some limit tests only check lengths, and one generic "strictly increasing" test is weak. Flat functions instead of grouped classes. Does not cover the date.max overflow. |
| bc376839 | 5 | 5 | 4 | 5 | 5 | 5 | Thorough and well grouped. Pins limit=0, the date.max/9999 crashes and the unsorted/duplicate round-trip bugs as strict xfails. A few length-only checks, and some messages are matched without their values. No property-based round trip. |
| a0a9b7a0 | 5 | 5 | 4 | 5 | 5 | 4 | Good coverage of all frequencies and edge cases. Strict xfail on date.max across all four frequencies. Several error matches are fragments only, some limit checks only check lengths, and there is no randomised round trip. Misses the limit=0 case. |
| ab9b405b | 5 | 5 | 4 | 5 | 5 | 4 | Clean, complete coverage of the documented behaviour, including scan-limit reset and the never-matching rule. Fewer probing cases (no date.max, no limit=0, only one xfail). Some error matches are generic fragments and some count/limit checks only check lengths. |
| ea3597bc | 5 | 5 | 4 | 4 | 5 | 4 | Broad coverage, including direct tests of _month_day/_add_months that pin negative days a month does not have. Rule validation matches only "INTERVAL"/"COUNT"/"BYDAY". Coupled to private helpers. Repetitive list(occurrences(...)) boilerplate. |
| f98c881b | 5 | 4 | 4 | 4 | 5 | 4 | Covers the API and helpers. The never-matching termination is tested only with MAX_SCAN_PERIODS monkeypatched. No next_after-never case and no xfail for the unsorted Rule round trip. Some pytest.raises have no match, plus length-only and [-1]-only checks. A stray brute-force test sits at the end of the file. |
| d3513acf | 5 | 5 | 3 | 4 | 4 | 4 | Edge-case content is complete, but Rule-validation assertions match only a key name ("INTERVAL", "BYDAY"), the laziness test checks only a length, and several messages are vague. One strict xfail asserts an undocumented contract (rejecting INTERVAL=1_0) as a bug. |

1. 08b44092, 84ae941f
3. bc376839
4. 96850034
5. a0a9b7a0, ab9b405b
7. ea3597bc
8. f98c881b
9. d3513acf
