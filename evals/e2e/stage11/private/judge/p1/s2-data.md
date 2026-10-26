## s2-data

| code | 문제 처리 1-5 | 결정 기록 1-5 | 리포트 유용성 1-5 | 스크립트 품질 1-5 | 출력 형식 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 41589dbd | 5 | 4 | 4 | 5 | 5 | 5 | Handles all 10 problems with stated rules (day-first dates, ×100 prices fixed from the list price, conflicting IDs rejected, future dates blanked); counts are given for fixes and rejects, but not for the label/format normalisations; revenue by category/country/month without cancellation or return values. |
| 7c487de1 | 5 | 4 | 3 | 5 | 4 | 4 | Flags every problem in an `issues` column, but the flagged 2027 orders still appear in revenue (2027-01/02 months), zero/negative quantities stay in the clean CSV, and conflicting order_ids keep the first row arbitrarily. |
| a4ef71aa | 5 | 5 | 5 | 5 | 5 | 5 | All problems handled with documented rules; per-rule fix counts and reject reasons; report has revenue and units by country/category/product/month plus amounts for cancelled and returned orders; argparse and unit tests. |
| cc7c0221 | 5 | 5 | 4 | 4 | 5 | 4 | Very detailed per-rule counts, but negative quantities are silently flipped to positive (a guess that inflates revenue), conflicting IDs are resolved by "most advanced status", it raises on any unmapped label, and the report embeds a timestamp. |
| d04d6411 | 5 | 5 | 4 | 4 | 5 | 5 | Clear rules, with a fix-count table, reject reasons and a remaining-blanks table, and it notes the undated orders left out of the monthly figures; it fails hard on any unmapped label or price mismatch; no cancellation or return values. |
| fb969a91 | 5 | 5 | 4 | 5 | 4 | 5 | Keeps rows and flags issues, blanks future dates and invalid quantities and leaves them out of revenue, monthly table includes units; the action counts are taken before dedup, and the clean CSV prints prices unpadded (4.2, 0.0). |

1. a4ef71aa
2. 41589dbd, d04d6411, fb969a91
5. cc7c0221
6. 7c487de1
