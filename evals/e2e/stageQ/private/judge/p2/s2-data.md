## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 33df49e6 | 5 | 5 | 5 | 4 | 5 | 5 | Handles all 10 problems with stated rules (day-first, list-price ×100 fix, conflicting ids rejected, future dates blanked). Every fix and rejection is counted, and the report breaks down orders, units and revenue by status, category, country, product and month. Raising on unmapped labels is brittle, and the future-date cutoff depends on date.today(). |
| dc1a4628 | 5 | 4 | 4 | 5 | 5 | 5 | All 10 problems handled; a fixed EXPORT_DATE makes reruns deterministic; per-row `fixes` column and a rejected CSV with reasons. The report states that format normalisation is not counted, and gives revenue only (no orders/units) by category, country and month. |
| 910230a5 | 5 | 4 | 5 | 5 | 4 | 4 | All 10 problems handled with documented rules and a per-row data_issues.csv. Rows with invalid quantity stay in the "clean" CSV with null quantity, and conflicting ids are resolved by picking the most advanced status (arbitrary). No counts for label normalisation; prices are written as 4.2, not 4.20. |
| ef5519d8 | 5 | 5 | 3 | 5 | 4 | 4 | All 10 problems handled with full counts. The headline "booked revenue" of 164k includes pending and returned orders, which is misleading. Quality counts are taken before dedup and rejection, so they don't reconcile with the clean rows. Prices are written as 4.2, not 4.20. |

1. 33df49e6
2. dc1a4628
3. 910230a5
4. ef5519d8
