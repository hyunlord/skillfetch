# Stage 2 rubrics (fixed before any session ran; `checks/FROZEN.sha256` covers this file)

Judges see one blind set per domain: every session's output under a random code, the condition hidden. Each
criterion is scored 1–5 with these anchors unless a criterion says otherwise:

- **5** a careful senior engineer would accept it as is
- **4** good; small gaps a reviewer would mention but not block on
- **3** usable after real fixes; noticeable gaps or mistakes
- **2** major parts missing or wrong
- **1** fails the task

**총점 1-5** is the judge's overall verdict on the deliverable for the user who asked ("would I accept this
as the result of my request?"), not the average of the criteria. Judges also give a rank over the whole set
(1 = best, competition ranking: 1, 1, 3, …) ordered by 총점, ties broken by the criteria total, and a one-line
reason per code. Objective check results (where given) are facts to use, not to re-derive.

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank
lines):

```
## <set name>

| code | <criterion 1> | … | 총점 1-5 | 근거 |
|---|---|…|---|---|
| <code> | <int> | … | <int> | <one line> |

1. <code>, <code>
3. <code>
```

---

## s2-tests — test suite for `src/recur/rules.py`

Context given to the judge: the module source, the session's diff, and the check output (tests passed/failed,
line and branch coverage of `rules.py`, whether `rules.py` was modified).

| criterion | what earns a 5 |
|---|---|
| 동작 범위 1-5 | every public function (`parse_rule`, `to_string`, `occurrences`, `next_after`, `between`, `describe`, `Rule` validation) and every frequency is exercised, with the documented options (INTERVAL, COUNT, UNTIL, BYDAY, BYMONTHDAY, ONINVALID) |
| 엣지케이스 1-5 | the hard cases the module documents are pinned down: 31st in short months under SKIP and CLAMP, negative BYMONTHDAY incl. one the month does not have, 29 February yearly, UNTIL inclusive / before start, COUNT+UNTIL conflict, BYDAY not including the start weekday, duplicate keys / unknown keys / bad values, `between` inclusive vs exclusive and reversed bounds, round trip `parse_rule(to_string(r)) == r`, never-matching rule terminates |
| 단언 품질 1-5 | assertions check exact values (date lists, exact error type and message fragment, exact strings), not just "no exception" or lengths; a wrong implementation would fail them |
| 구조·가독성 1-5 | parametrisation where cases repeat, clear names that state the behaviour, fixtures/helpers without hiding the inputs, sensible file layout and pytest config |
| 정확성 1-5 | the suite passes against the unmodified module; no test asserts behaviour the module does not have; the module is not edited to make tests pass (an edit to `rules.py` caps this at 2) |

## s2-api — bookmarks REST API (FastAPI, SQLite)

Context: the session's diff and the check output (the session's own test results; the frozen contract script's
per-call results against the spec in the prompt).

| criterion | what earns a 5 |
|---|---|
| 계약 준수 1-5 | all endpoints, fields, filters, pagination and status codes from the prompt (201 / 204 / 404 / 409 / 422, http/https only, duplicate url blocked on create and update); use the contract-script results |
| 스키마·검증 1-5 | separate create / update / read schemas, partial update done right (unset vs null), URL and title validation, tags normalised or validated, created_at server-set |
| 에러 처리 1-5 | consistent error responses, no 500 on bad input or races the spec names (duplicate url), DB errors mapped, not swallowed |
| 구조·가독성 1-5 | clear separation (schemas / storage / routes) proportional to the size, DB path from `BOOKMARKS_DB`, connection handling correct, no dead code |
| 테스트 1-5 | tests cover each endpoint's success and error paths with an isolated database per test, and they pass |

## s2-docs — README and usage docs for the Next.js example app

Context: the session's diff and the repository's source files (the judge checks claims against them) and the
check output (README present, npm scripts referenced in the docs that do not exist in `package.json`, `npm run
build` result).

| criterion | what earns a 5 |
|---|---|
| 정확성 1-5 | every command, script, route, file path, data source and behaviour described matches the code; nothing invented (an invented feature or wrong command caps this at 2) |
| 완전성 1-5 | what it is, requirements, install, run dev / build / start / type-check, project structure, the pages and the `/api/users` route, where the sample data lives and how to change it |
| 명확성 1-5 | a newcomer can go from clone to running app and to making a first change without reading the code; scannable structure, examples that work |
| 간결성 1-5 | no padding, marketing language or generic boilerplate unrelated to this repo; length fits a small example app |
| 문서 구성 1-5 | README vs the extra usage document(s) split sensibly, linked to each other, no duplication between them |

## s2-data — `scripts/clean_orders.py` for `data/orders.csv`

Context: the session's diff, the raw `data/orders.csv`, the files the check produced by running
`uv run python scripts/clean_orders.py` in a fresh copy, and this list of problems planted in the CSV (the
sessions were not told the list):

1. order_date in five forms: ISO `2025-01-11`, `DD/MM/YYYY` (some ambiguous with MM/DD, e.g. `01/04/2025`),
   `May 16 2025`, `2025/08/22`, blank
2. unit_price as `4.20`, `$6.40`, `USD 12.00`, `1,249.00`, blank; 3 prices ×100 (outliers)
3. quantity blank, `5 pcs`, negative, `0`
4. 12 exact duplicate rows; 3 order_ids repeated with different content (ORD-00276, ORD-00147, ORD-00027)
5. category case / whitespace / spelling variants (`ELECTRONICS`, ` electronics`, `Elec.`, `stationary`,
   `groceries`)
6. country variants (`US` / `USA` / `United States` / `u.s.`, `UK` / `United Kingdom` / `GB`, `Korea, Republic
   of` / `South Korea` / `KR`, `Germany` / `germany` / `DE`)
7. status case / whitespace / spelling (`Shipped `, `SHIPPED`, `canceled` vs `cancelled`)
8. customer_email blank, uppercase, trailing space, invalid (`n/a`, no `@`, no TLD)
9. discount as blank, `10%`, `0.10`, `0`
10. 4 order dates in 2027 (future)

| criterion | what earns a 5 |
|---|---|
| 문제 처리 1-5 | count the planted problems (1–10) handled sensibly: 5 = 9–10, 4 = 7–8, 3 = 5–6, 2 = 3–4, 1 = 0–2. "Handled" = detected and either fixed, flagged or dropped with a stated rule; silently mangling it (e.g. reading `01/04/2025` without a stated day-first rule, dropping rows without counting them) does not count |
| 결정 기록 1-5 | every cleaning decision and how many rows it touched is visible in the report or the output (counts dropped / fixed / flagged per rule) |
| 리포트 유용성 1-5 | the summary answers what a person would ask of an orders export (revenue, orders and units by category / country / month / status, cancellations and returns) with correct numbers given the cleaning rules |
| 스크립트 품질 1-5 | runs with the stated command, idempotent, readable structure, pandas or stdlib used correctly, no hard-coded absolute paths |
| 출력 형식 1-5 | clean CSV with consistent types and normalised values plus a readable report (Markdown/text/JSON) in `out/` |
