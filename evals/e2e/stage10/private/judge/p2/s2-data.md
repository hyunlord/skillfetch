## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 0b9c9024 | 5 | 4 | 5 | 5 | 5 | 5 | All 10 problems handled with stated rules (day-first in docstring, x100 fixed, first-kept conflicts rejected); fix/reject/gap tables with counts; revenue by country/category/month/product plus status amounts; no counts for label normalisation |
| 114f16fc | 5 | 4 | 4 | 5 | 5 | 5 | All 10 handled, rules in docstring, per-row flags column with counts; status amounts shown; month table has no units; label normalisation counts missing |
| 1927b305 | 5 | 5 | 4 | 5 | 5 | 5 | All 10 handled with counts for every fix incl. label/date/price normalisation and an issues column; future dates flagged but kept, so 2027 months appear in the shipped revenue table |
| 21fdfb36 | 5 | 4 | 4 | 5 | 5 | 4 | All 10 handled (rejects all copies of a conflicting id); fix table, but normalisations only listed as "every row" with no counts; status table shows counts only, no amounts |
| 23ec8cd8 | 5 | 4 | 4 | 5 | 5 | 4 | Clear rule docstring, unknown labels fail loudly, injectable date; action log has counts but no normalisation counts; status counts only, cancellations/returns have no value |
| 4088d313 | 5 | 5 | 5 | 5 | 5 | 5 | Most complete: all 10 handled, issues column, conflicting ids listed, variant-collapse counts, status amounts, revenue shares, 27 passing tests; replaces any off-list price (flagged) |
| 5d3ab2a5 | 5 | 4 | 4 | 4 | 5 | 4 | All 10 handled with stated rules, but rejects 19 orders only because the date is missing, which understates revenue; status counts only; default paths depend on the working directory |
| 5f023b98 | 5 | 5 | 4 | 5 | 4 | 4 | Detailed issue flags and counts; keeps 37 rows with blank quantity/line_total in the clean CSV, so the status table (242 shipped) disagrees with the revenue base (223) |
| 5f05cb72 | 5 | 5 | 4 | 5 | 5 | 4 | Thorough log (relabel, pcs, discount, price counts, source_row, --as-of), but rejects 19 orders for a missing date, which lowers revenue figures; status counts only |
| 63ace8de | 5 | 4 | 5 | 5 | 5 | 5 | All handled, conflicting ids listed, source_line in rejects, status values, units by month, 31 passing tests; day-first rule appears only in a test comment; no normalisation counts |
| 6c38ffac | 5 | 4 | 4 | 5 | 5 | 4 | All 10 handled (future-dated rows rejected); short data-quality list; status counts only, country/month tables have no units, top-5 products only |
| 6cbc3c4d | 5 | 4 | 5 | 5 | 5 | 5 | All 10 handled, --max-date for reproducibility, price flag columns, status amounts, full breakdowns; normalisation described but not counted |
| 86ed1fd3 | 5 | 4 | 4 | 5 | 4 | 4 | Keeps the last version of a conflicting order_id (an assumption); 37 rows with null quantity kept in clean CSV; normalisation explicitly "silent"; status counts only |
| 8b383c0a | 5 | 5 | 5 | 5 | 5 | 5 | All 10 handled; fixes list counts every rule incl. variant collapse and off-list prices; quality_flags column; status amounts; full country/category/product/month tables |
| 95b62d5f | 5 | 5 | 3 | 4 | 5 | 4 | Fix table counts every normalisation; report gives revenue only, with no orders or units per country/category/month and no status amounts; catch-all digit-strip parser is fragile |
| a01ba756 | 5 | 4 | 5 | 5 | 5 | 5 | Clear rule docstring, single cleaning log with counts, price_note column, status amounts, full breakdowns; label normalisation not counted |
| bccda43d | 5 | 4 | 4 | 5 | 5 | 4 | Gross/discount/net split and issues column; one duplicate of a rejected row is counted as rejected twice (11 dups instead of 12); status counts only |
| d84dcd3b | 5 | 4 | 4 | 5 | 4 | 4 | Issues column and conflicting ids listed; rows with bad quantity are kept in the clean CSV with blanks, so status counts (242 shipped) disagree with revenue base (223) |

1. 4088d313, 8b383c0a
3. 0b9c9024, 1927b305, 63ace8de, 6cbc3c4d, a01ba756
8. 114f16fc
9. 5f05cb72
10. 21fdfb36, 23ec8cd8, 5f023b98, 6c38ffac, bccda43d
15. 5d3ab2a5, 86ed1fd3, 95b62d5f, d84dcd3b
