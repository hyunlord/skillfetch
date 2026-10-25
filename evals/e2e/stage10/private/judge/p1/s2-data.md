## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| e77c2a98 | 5 | 5 | 5 | 5 | 5 | 5 | All 10 problems handled under rules written in the docstring. Every conflicting order_id is rejected. The report gives row accounting, fix counts (including how many spelling variants collapsed into one value), quality-flag counts, status amounts and orders/units/net sales by country, category, product and month. The CSV has 2-decimal floats and a quality_flags column. |
| 383e8e7a | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled. Day-first is stated. Unknown labels and price mismatches fail loudly. Future dates are cut off with a --max-date option. Rejections and fixes are counted, and the report has status amounts and full breakdowns. Minor: floats are unformatted (4.2). |
| 0f6c3cce | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled. The docstring lists every rule. A per-row issues column, rejection reasons and the conflicting IDs are all listed, and the report includes revenue shares. Ships 27 passing tests. Minor: the Generated timestamp makes output differ between runs, floats are unformatted, and any price off the list price is overwritten. |
| 9170e686 | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled. Fixes are recorded per row, rejections are counted (multiple reasons allowed), all copies of conflicting IDs are rejected, and the report has status values and full breakdowns. Ships 31 passing tests. Minor: day-first is stated only in a test, plus a timestamp and unformatted floats. |
| 9addb7f1 | 5 | 5 | 5 | 5 | 4 | 5 | All 10 handled with rules in the docstring. A single cleaning log covers every step with counts, unknown labels and off-list prices exit loudly, and the report has status values and breakdowns by category, country, product and month. Minor: floats are unformatted. |
| 5bd07dd6 | 5 | 5 | 4 | 5 | 5 | 4 | All 10 handled with a documented rule list, a table of actions with counts and fail-loud mapping. Revenue includes pending orders, and for a conflicting order_id the first row is kept arbitrarily (both rules are stated). The status table has counts only. |
| 6bbb29fe | 5 | 5 | 4 | 5 | 5 | 4 | Thorough: rows missing a date, future-dated rows and bad quantities are rejected with counts, an --as-of option is provided, and fixes are counted per step. Revenue includes pending orders, though cancelled/returned amounts are reported separately. For a conflicting order_id the first row is kept. Dropping undated rows shrinks the revenue base. |
| 92a841ae | 5 | 4 | 4 | 5 | 5 | 4 | All 10 handled with clear RowError rejection, an issues column, and gross/discount/net totals. An exact duplicate of a rejected row is rejected twice instead of being deduplicated (11 vs 12 dropped). The status table has counts only, with no cancel/return amounts. |
| 295fd510 | 5 | 5 | 4 | 5 | 4 | 4 | All 10 handled and flagged per row. Rows with a bad quantity are kept in the clean CSV with blank quantity and line total, so the status counts (242 shipped) do not match the revenue base (223). The status table has counts only. |
| 7f1094d6 | 5 | 5 | 4 | 5 | 4 | 4 | Rules are clearly documented, issues are flagged per row and conflicts are listed in the report. Like 295fd510, it keeps 37 rows without a quantity in the clean CSV, so status counts do not match revenue. Uses a 10x-median outlier rule. Floats are unformatted. |
| 0035e469 | 5 | 4 | 4 | 4 | 5 | 4 | All 10 handled and the code is compact. Fixes and rejections are counted. The day-first rule appears only as a code comment. The status table has counts only, and there is no module docstring of rules. |
| 26c2c79c | 5 | 5 | 4 | 4 | 4 | 4 | All 10 handled and the fix log is detailed. For a conflicting order_id the first row is kept. Revenue counts pending orders. The month table is sorted by revenue rather than chronologically. Floats are unformatted. |
| 39ca0303 | 5 | 4 | 4 | 4 | 5 | 4 | All 10 handled, and missing or future dates cause a reject. Only the first reason is kept per row, so overlapping problems are under-counted. The status table has counts only. Input and output paths are resolved from the working directory. |
| 665d8118 | 5 | 4 | 4 | 5 | 4 | 4 | Flags are recorded per row with a clear legend. For a conflicting order_id the last row is kept, on the assumption that it is the latest. Rows without a quantity stay in the clean CSV. Formatting fixes are applied "silently" and not counted. The status table has counts only. |
| ad3e34e4 | 5 | 5 | 3 | 4 | 5 | 4 | All 10 handled with a full fix log. The breakdowns show revenue only, with no order or unit counts, and the status table has counts only. The rejected file is written normalized rather than as the raw rows. |
| 95d2057d | 5 | 4 | 4 | 4 | 4 | 4 | All 10 handled, and future-dated rows are rejected. Normalisation counts are thin. The country table has no units, and only the top 5 products are shown. The rejected file is normalized rather than raw. Floats are unformatted. |
| f620765c | 5 | 4 | 4 | 4 | 4 | 4 | All 10 handled with documented rules. For a conflicting order_id the first row is kept. Unknown labels are flagged but kept. Normalisation counts are missing from the report. Floats are unformatted. |
| aad4dab3 | 5 | 5 | 3 | 4 | 4 | 3 | Fix counts are detailed, but future dates are only flagged and kept. As a result 2027-01/02 months appear in the revenue table and the date range ends in 2027-02-22. The day-first comment is garbled. For a conflicting order_id the first row is kept. |

1. e77c2a98
2. 383e8e7a, 0f6c3cce, 9170e686, 9addb7f1
7. 5bd07dd6, 6bbb29fe
9. 92a841ae, 295fd510, 7f1094d6
12. 0035e469, 26c2c79c, 39ca0303, 665d8118, ad3e34e4
17. 95d2057d, f620765c
18. aad4dab3
