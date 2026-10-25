## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 05d95d0e | 5 | 5 | 5 | 5 | 5 | 5 | Handles all 10 planted problems: day-first rule stated, x100 prices fixed, the 6 conflicting rows set aside in a separate file, future dates blanked, emails repaired. The report states each rule, has full row accounting and per-issue counts, and gives shipped revenue/units by country, category, product and month. |
| 1c6d5f15 | 5 | 4 | 4 | 4 | 5 | 4 | All problems handled, and rejected rows go to a file with reasons. Small accounting slip: one exact-duplicate pair is rejected twice, so the report says 11 duplicates collapsed instead of 12. Status counts cover kept rows only, and the rules are in the docstring, not the report. |
| 35a65132 | 5 | 4 | 4 | 5 | 5 | 4 | All problems handled. Conflicts are resolved by keeping the "most advanced status" row (rule stated and counted; the dropped rows go to needs_review.csv). Clean parser table. The report does not state its rules (no day-first or future-date wording), and the category/country tables have no units. |
| 86bec73c | 5 | 5 | 4 | 4 | 4 | 4 | Rules, counts and a dropped_rows.csv are all in the report. But 2027 dates are only flagged and kept, so the monthly revenue table shows 2027-01 and 2027-02 and the total includes them. The report also embeds a generation timestamp. |
| 99de335b | 5 | 4 | 5 | 4 | 5 | 5 | All problems handled. The report gives flag counts, the list prices used, revenue/units by category, country, product and month, and the excluded count. Weak points: the rules live only in the docstring, the dropped conflict rows are not saved, and the parsers raise on any value they have not seen. |
| c02890f0 | 5 | 4 | 4 | 5 | 5 | 4 | All problems handled, and the 6 conflicting rows are rejected to a file with their ids listed. The notes miss the country/category/status mapping rules, and the month table is sorted by revenue rather than by date, with an "unknown" bucket. |
| d466bb3f | 5 | 4 | 4 | 4 | 5 | 4 | Rows with bad quantities and later conflict rows are rejected with reasons and counted. For conflicts it keeps the first occurrence, an arbitrary choice that is stated. Revenue tables have no units and products are top 5 only. A conflict reason can overwrite a quantity reason. The report includes a timestamp. |
| d6759c51 | 5 | 4 | 4 | 4 | 4 | 4 | All problems handled, and duplicates_removed.csv gives reasons. For conflicts it keeps the first row, which is flagged. Revenue by status is a useful addition. The month table is sorted by revenue, the rules are only in the docstring, and the report leaks the absolute input path. |
| e3b78894 | 5 | 5 | 3 | 4 | 5 | 3 | Most detailed repair log (normalisation counts per field) and an --as-of option, but two questionable choices hurt the summary: it rejects 19 orders only for a missing date, and it counts pending orders as revenue (146,829.69 vs about 127k shipped). That makes the summary numbers less useful. |

1. 05d95d0e
2. 99de335b
3. c02890f0, 35a65132
5. 1c6d5f15, 86bec73c, d466bb3f
8. d6759c51
9. e3b78894
