## s14-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| c08c29f3 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 problems handled with stated rules (day-first, x100 fix, imputed prices, future dates blanked, conflicting ids rejected); per-rule counts and issue codes; report has status amounts, units, shares by category/country/month/product; 97 tests incl. end-to-end |
| c44f6e24 | 5 | 5 | 4 | 5 | 5 | 5 | All 10 handled; row-level issues log with original values, conflicting ids set aside in orders_review.csv, category corrected from product; report lacks revenue by status but otherwise complete; 101 tests, --today for reproducibility |
| 9131a2b9 | 5 | 5 | 4 | 5 | 5 | 5 | All 10 detected; per-column action table plus issues log with source_row; does not impute blank prices (32 shipped lines left out of revenue) and keeps both conflicting rows in totals, both stated; 86 tests |
| 8ce7c3eb | 5 | 5 | 4 | 5 | 5 | 4 | All 10 handled with rules in docstring and counts per issue; conflicting ids keep the first row (flagged); report shipped-only by country/category/month, no units or product view, no tests |
| dcbd52e1 | 5 | 5 | 4 | 4 | 5 | 4 | All 10 handled, catalog prices listed, units and revenue by status/category/country/product; but 2027 dates are only flagged, so 2027-01/02 appear in the monthly revenue; script aborts on any unknown value; no tests |
| a99fee9d | 5 | 5 | 4 | 5 | 4 | 4 | Same rules and counts as a solid baseline (fixes vs rejects tables, future dates blanked); rules live only in code comments, report has no units, clean CSV prices/discounts not formatted (4.2, 0.0) |

1. c08c29f3
2. c44f6e24, 9131a2b9
4. 8ce7c3eb
5. dcbd52e1, a99fee9d
