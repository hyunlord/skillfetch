## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 27842b85 | 5 | 5 | 5 | 5 | 5 | 5 | Every public function and option covered, 100% line/branch, exact date lists and message fragments, documented edge cases all pinned, strict xfails for real bugs (date.max overflow, unsorted BYDAY round trip) |
| 494f8102 | 5 | 5 | 5 | 5 | 5 | 5 | Complete coverage with a separate termination group (scan-limit reset and exhaustion), exact assertions, strict xfail for limit=0, clean classes and parametrisation |
| 5cb5edd3 | 5 | 5 | 5 | 4 | 5 | 5 | Thorough, with six strict xfails documenting real bugs (date.max, year 10000, unsorted/repeated BYDAY); the `D` alias and very long lines hurt readability a little |
| 74f8960f | 5 | 5 | 5 | 5 | 5 | 5 | Flat, well-named tests with pytest.param ids, exact error messages including values, scan-limit reset/exhaustion, exception-chaining check, strict xfails for real bugs |
| c386d03e | 5 | 5 | 5 | 4 | 5 | 5 | Solid example tests plus Hypothesis property tests (round trip, ordering, next_after/between agreement, CLAMP superset of SKIP); adds a new dev dependency, and direct Rule validation is tested mostly through parse_rule |
| fe6bcaa0 | 5 | 5 | 5 | 5 | 5 | 5 | Complete coverage, deterministic grid round trip over >100 canonical rules, exact date lists, strict xfails for limit=0, date.max and unsorted BYDAY |

1. 27842b85, 494f8102, 74f8960f, fe6bcaa0
5. 5cb5edd3, c386d03e
