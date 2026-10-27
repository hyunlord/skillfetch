## s14-docs

| code | 정확성 1-5 | 완전성 1-5 | 명확성 1-5 | 간결성 1-5 | 문서 구성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 17546041 | 5 | 5 | 5 | 5 | 4 | 5 | Every verifiable claim matches (web routes/ids 101–104, media 201/422/404/400/413, healthz ok, DefaultBodyLimit caveat); honest that api has no app; compact README + one usage doc, linked |
| b3281aa1 | 5 | 5 | 5 | 5 | 4 | 5 | Accurate and concise; route table with source files, correct curl outputs (200x150 example, id from 1), api honestly skeleton-only; README links usage doc and media/README |
| ba5638bc | 5 | 5 | 5 | 4 | 5 | 5 | Most thorough: accurate media details (415/400/422 JSON errors, 1067x800 example, startup line), data counts match the CSV, known issues listed; README is long (681 words) and repeats some config |
| 2f685e66 | 5 | 4 | 5 | 5 | 4 | 5 | Accurate per-area guides for api, media and data (CSV counts verified: 15 dup ids, 21/19 blanks, 33 of 54 day-first); web gets only quick-start commands, no doc of its pages |
| eb00c49b | 4 | 5 | 5 | 4 | 5 | 5 | Clean split into four per-area docs linked from README, includes landing-page editing guide; data doc says 22 empty emails (CSV has 19) and overall length is high |
| 41edf496 | 4 | 4 | 4 | 5 | 4 | 4 | Short and mostly right, data/README detailed; tells users to run `uv run pytest` in api where no tests exist, web points only to the stock Next.js README, odd `.claude/` entry in layout |

1. 17546041, b3281aa1, ba5638bc
4. 2f685e66, eb00c49b
6. 41edf496
