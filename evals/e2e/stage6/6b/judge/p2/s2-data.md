## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 08eb90f2 | 5 | 5 | 4 | 5 | 5 | 5 | Handles all 10 problems with stated rules (day-first, future dates blanked, x100 prices fixed, all 6 conflicting rows rejected to a file). Per-row `issues` column plus counts per rule. Shipped revenue by category/country/month/product; no revenue by status. |
| 3b4ddc5b | 5 | 4 | 4 | 5 | 5 | 5 | All 10 handled with a full rule docstring and list-price table. Conflicts are resolved by a stated rule (a final status beats pending), but the superseded rows are not written out. Unknown labels fail fast. Report is complete and correct. |
| b214cbd9 | 5 | 5 | 4 | 4 | 5 | 5 | All 10 handled. Report has a full "Cleaning decisions" section, a fix/flag count table and missing-after-cleaning counts; conflicts go to their own file. It guesses repairs for broken emails (`farah14example.com` becomes `@example.com`); these are flagged but invented. No CLI options. |
| a501ffbe | 5 | 5 | 4 | 4 | 5 | 4 | All 10 handled. 40 rejected rows have reasons, and the report gives orders and units per status. Conflicts keep the first occurrence arbitrarily. Every price that differs from list is overwritten. Rejecting bad-quantity rows also removes those orders from the status counts. |
| ba3f2b7c | 5 | 5 | 3 | 4 | 5 | 4 | Rules are clearly stated and dropped rows are listed with their source line. But 2027 dates are only flagged, not removed, so they show up in monthly revenue (2027-01, 2027-02) and in the totals. |
| ca7c9d60 | 5 | 4 | 4 | 4 | 5 | 4 | All 10 handled and the cleaning actions are counted. Future dates are merged into a generic `invalid_order_date`, and the day-first and blank-discount rules appear only in code. The by-category and by-country tables have no units. |
| de60e983 | 5 | 4 | 4 | 4 | 5 | 4 | All 10 handled and the report gives value per status (cancelled and returned included). Conflicts keep the first occurrence arbitrarily; the rules are only in the docstring, not the report. The monthly table is sorted by revenue, and the report prints an absolute source path. |
| 57e2d2b6 | 5 | 4 | 4 | 3 | 5 | 4 | All 10 handled and rejected rows have reasons. Rejection runs before deduplication, so the ORD-00232 duplicate is rejected twice and the report counts 11 duplicates instead of 12. Dropping 38 bad-quantity rows shrinks the status counts. |
| dadb7ef5 | 5 | 4 | 3 | 5 | 4 | 3 | Detailed repair log and an `--as-of` option for the future-date check (run is reproducible). But it rejects 63 rows, including 19 orders that only lack a date, and counts pending orders as revenue. The clean CSV has no per-row issue flags. |

1. 08eb90f2
2. 3b4ddc5b, b214cbd9
4. a501ffbe
5. ba3f2b7c, ca7c9d60, de60e983
8. 57e2d2b6
9. dadb7ef5
