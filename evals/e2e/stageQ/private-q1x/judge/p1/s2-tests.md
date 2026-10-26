## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 46720d58 | 5 | 5 | 5 | 5 | 5 | 5 | Covers every public function, every frequency and every option. It pins all the documented hard cases (SKIP/CLAMP 31st, -30/-31, 29 Feb including the century rule, UNTIL edges, never-matching rule plus the MAX_SCAN reset). Asserts exact date lists and messages; organised in classes; strict xfails mark real defects. 100%/100% coverage, rules.py unchanged. |
| 6cd5c73f | 5 | 5 | 5 | 4 | 5 | 5 | Very thorough: about 37 parse-error cases with exact messages, plus strict xfails for an unsorted BYDAY round trip/order and the limit=0 bug. Exact date assertions throughout. Flat module of functions with a `D = date` alias is a little less navigable. 100%/100% coverage. |
| a567bcac | 5 | 5 | 5 | 5 | 5 | 5 | Complete coverage, including the package exports, all documented edge cases, collapsed clamped duplicates and the scan limit. Clear `ds()` date helpers and class grouping; strict xfails document unsorted/duplicate BYDAY and overflow at the calendar end. 100%/100% coverage. |
| a7f51ead | 5 | 5 | 4 | 4 | 5 | 4 | All functions and edge cases are covered, with useful strict xfails for directly built Rules. But `test_rule_accepts_boundary_values` asserts nothing, several COUNT/limit tests check only lengths, and there is no frozen-dataclass test. Flat layout. 100%/100% coverage. |
| bb25e0dc | 5 | 5 | 5 | 5 | 5 | 5 | The largest suite (182 passed). Covers every function, frequency and option with exact date lists. Adds extra edges: 29 Feb with COUNT and UNTIL, MONTHLY INTERVAL=12, between on the last day of the month, and the scan-counter reset. Readable weekday constants and classes; real defects in strict xfails. 100%/100% coverage. |
| f62887b9 | 5 | 5 | 5 | 5 | 5 | 5 | Complete and exact (messages include the values). Finds the duplicate-BYMONTHDAY round-trip defect besides the BYDAY one, and checks the bridging behaviour of the scan limit. The never-matching tests run with a lowered MAX_SCAN_PERIODS but still verify termination. 100%/100% coverage. |

1. 46720d58, a567bcac, bb25e0dc, f62887b9
5. 6cd5c73f
6. a7f51ead
