## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 18359e90 | 5 | 4 | 4 | 5 | 5 | 4 | handles all 10 (day-first rule stated in code, 12 dupes + 3 conflicting ids rejected, future dates nulled, cents prices fixed, bad qty rejected with counts); report counts rejects and value fixes but says format normalisation is "not counted"; revenue by category/country/month and status counts only, no units or returns/cancellation revenue; fixed export date keeps it reproducible; tidy CSV with fixes column + rejected CSV |
| c0f3fecf | 5 | 5 | 5 | 4 | 5 | 5 | all 10 handled with rules in the docstring; report counts every rule (dupes, rejects, ISO reformatting, label normalisation, cents prices, imputations, discounts); orders/units/revenue by status, category, country, product and month; fails loudly on unmapped values; future check uses date.today() so output can drift over time |
| e9c7f28e | 5 | 4 | 4 | 5 | 4 | 4 | all 10 handled, rules documented in the docstring, argparse with defaults; quality counts are taken before dedup/rejection so they don't reconcile with the 320 clean rows; "booked revenue" headline and breakdowns include returned orders; floats written unformatted (4.2, 1249.0) |
| f3a99b82 | 5 | 5 | 4 | 4 | 4 | 4 | all 10 handled with per-row data_issues.csv (field, issue, raw value), the best audit trail; but conflicting duplicate ids are resolved by keeping the "most advanced status" (a guess) and rows with invalid quantity stay in the clean CSV with null amounts; normalisation counts missing from the report; row-wise Python loops |

1. c0f3fecf
2. 18359e90
3. e9c7f28e, f3a99b82
