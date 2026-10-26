## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 19745edc | 5 | 4 | 4 | 5 | 5 | 4 | All 10 planted problems handled with stated rules (day-first, catalog price for blanks and ×100, per-row `issues` flags, dups to rejected.csv); per-issue counts but normalisations not counted; future-dated 2027 rows stay in shipped revenue and the month table, and there are no unit counts |
| 2c20bd78 | 5 | 4 | 5 | 5 | 5 | 5 | All 10 handled; every rejection reason and fix counted (country/category/status mapping not counted); report gives shipped revenue with orders/units by country, category, product and month plus amounts by status; CLI args and 7 passing tests |
| 43f0ddf6 | 5 | 4 | 4 | 5 | 5 | 4 | All 10 handled with stated rules and a counted action log; future dates blanked rather than flagged; the "net revenue" headline and breakdowns include pending orders, which is a debatable definition; label normalisation not counted |
| 741014b9 | 5 | 4 | 5 | 5 | 5 | 5 | All 10 handled (it fails fast on unmapped labels or unexpected prices); fix counts, rejection reasons and a "remaining blanks" table; shipped-only revenue with a note on undated orders; consistent numbers; label normalisation described but not counted |
| c1fb11d1 | 5 | 4 | 4 | 4 | 4 | 4 | All 10 flagged with stated rules, but action counts are taken before deduplication so they don't match the clean file; shipped order counts include rows with no quantity/line_total; prices written unformatted (4.2, 1249.0) |
| c4fc7130 | 4 | 5 | 4 | 4 | 5 | 4 | Fullest decision log (counts for every normalisation, conflicting ids listed), but negative quantities are turned positive with abs(), which is a guess that feeds revenue; the report has a `datetime.now()` stamp, so output is not idempotent |

1. 2c20bd78, 741014b9
3. 19745edc, 43f0ddf6
5. c4fc7130
6. c1fb11d1
