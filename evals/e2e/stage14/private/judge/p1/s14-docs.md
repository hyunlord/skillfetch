## s14-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| b9c41671 | 5 | 5 | 5 | 5 | 5 | 5 | short root README (table, tools, quick start, checks) plus one usage doc that covers every area with routes, env vars, codes and examples; matches the files, including the body-limit caveat; api is honestly called unimplemented |
| d131a840 | 5 | 5 | 5 | 5 | 5 | 5 | same shape as above in English: lean README with linked USAGE.md; web routes, cms-api endpoints/config/examples, data rules/outputs and api status are all correct and easy to follow |
| 78361ffe | 4 | 5 | 5 | 4 | 5 | 5 | best split (README + one doc per area, linked) and very thorough, incl. landing-page editing notes; one wrong count (22 empty emails, the file has 19); env table repeated in README and cms-api.md |
| ee72973c | 5 | 4 | 5 | 4 | 5 | 5 | accurate README + api/media/data guides with verified data facts (21 dates, 19 emails, day-first); web gets only commands, with no page/route description; some duplication of commands |
| 5732b33c | 5 | 5 | 5 | 3 | 4 | 5 | complete and accurate (data counts check out, API and resize behaviour described in depth), but long: the README alone repeats config, layout and caveats that docs/usage.md covers again |
| 3ae1a6aa | 4 | 3 | 4 | 4 | 3 | 3 | accurate root README + a good data/README, but no usage doc for web or media (it points to the stock Next.js README and the short media README); tells you to run `uv run pytest` in an api with no tests |

1. b9c41671, d131a840
3. 78361ffe, ee72973c
5. 5732b33c
6. 3ae1a6aa
