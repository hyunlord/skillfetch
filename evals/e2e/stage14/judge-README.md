# Stage 14 — blind judging package (pass PASS)

Give the judge only this folder (`judge-package/PASS/`) and `judge-package/rubrics/`.

Each subfolder is one **set**: six outputs for the same request, each under a random 8-hex code. The judge does not
know how any output was produced and should not try to find out. Judge each set separately, viewing every output in the
set before scoring. Every output is the result of that one request in a repository with four areas (`web/`, `api/`,
`media/`, `data/`); some outputs may also touch files outside the area the request is about — judge the result for the
user who asked.

| set | rubric | in each code folder |
|---|---|---|
| s14-landing | `rubrics/rubric-design.md` | `wide.png`, `narrow.png` (screenshots of `/landing`) |
| s14-api | `rubrics/rubrics-s2.md` (general part, output format, section s2-api) | `diff.patch`, `check.txt` |
| s14-apitests | `rubrics/rubrics-14.md` (section s14-apitests; general part and output format of `rubrics-s2.md`) | `diff.patch`, `check.txt` |
| s14-rust | `rubrics/rubric-b4-add.md` (row s11-t266; the crate is `media/`) | `diff.patch`, `check.md`, `reply.md` (the final reply to the user) |
| s14-docs | `rubrics/rubrics-14.md` (section s14-docs) | `diff.patch`, `check.txt`; `_context/` in the set = the repository's starting files |
| s14-data | `rubrics/rubrics-s2.md` (section s2-data; the folder is `data/`) | `diff.patch`, `check.txt`, `out/`; `_context/` = the raw CSV |

`TASK.md` in each set is the request, verbatim. In `check.md`, an item marked UNDECIDABLE could not be measured.

## Output

One file per set, named `<set>.md`, in exactly the rubric's output format:

- a section headed `## <set>`
- a table whose header row starts with `| code |` and uses the rubric's column names exactly (design set:
  `(a) AI느낌 수` and `(b) 쓸만함 1-5`; other sets: the criteria, then `총점 1-5`, then `근거`)
- every code exactly once in the table (integers), then the rank lines (`1. code, code` / `3. code`, competition
  ranking), every code exactly once

Please also report whether you opened any file outside this folder and `rubrics/`.
