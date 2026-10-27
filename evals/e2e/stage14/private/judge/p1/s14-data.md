## s14-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| afb69cdd | 5 | 5 | 4 | 5 | 5 | 5 | all 10 problems handled with stated rules (day-first, 3×100 prices, future dates cleared, conflicting ids set aside for review); per-cell issues log and per-column action counts; 101 passing tests, CLI options; report gives units/revenue by month/country/category/product but only counts for cancelled/returned |
| e56981ef | 5 | 5 | 5 | 5 | 4 | 5 | all 10 handled, every row accounted for (clean or rejected with reason); clearest report: status with amounts, shipped revenue with units and shares, remaining gaps; 97 tests, --today for reproducibility; floats written as 4.2 / 0.0 |
| ef0a5460 | 5 | 5 | 4 | 5 | 4 | 4 | all 10 detected with a per-column rules table and an issues log; but the 3 conflicting order_ids stay in the clean CSV (both rows), so they count twice in revenue, and missing prices are left blank, which removes 32 shipped lines from revenue |
| 08db765e | 5 | 4 | 4 | 4 | 5 | 4 | all 10 handled with rules in the docstring; per-reason counts, catalog prices, revenue by status/category/country/product/month with units; but 2027 orders are only flagged and remain in the revenue and month tables; variant normalisation is not counted; no tests |
| b39a66ed | 5 | 5 | 3 | 4 | 5 | 4 | all 10 handled, and issue and still-missing counts are clear; for conflicting order_ids it keeps the first row arbitrarily; report has shipped revenue by country/category/month but no units, no product breakdown and no amounts by status |
| a373669c | 5 | 4 | 4 | 4 | 4 | 4 | all 10 handled (day-first noted only in a code comment); fixes and rejects counted, but normalisation counts and rules are not in the report; shipped revenue by category/country/product/month without units; prices written unformatted (4.2) |

1. afb69cdd, e56981ef
3. ef0a5460
4. 08db765e, b39a66ed
6. a373669c
