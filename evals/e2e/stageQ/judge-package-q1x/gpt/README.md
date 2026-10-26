# Stage Q, Q1 extension — blind judging package (pass gpt)

Give the judge only this folder (`judge-package-q1x/gpt/`) and `judge-package-q1x/rubrics/`.

Each subfolder is one **set**: several outputs for the same request, each under a random 8-hex code. The judge does
not know how any output was produced and should not try to find out. Judge each set separately, viewing every output in
the set before scoring.

| set | rubric | in each code folder |
|---|---|---|
| d2-redesign, d3-dashboard | `rubrics/rubric-design.md` | `wide.png`, `narrow.png` (screenshots) |
| s2-docs, s2-tests | `rubrics/rubrics-s2.md` (general part, output format, and the section with the set's name) | `diff.patch`, `check.txt` (objective results); `_context/` in the set = starting source |
| s10-t263, s10-t115, s10-t198 | `rubrics/rubric-b4.md` (the row for the set) | `diff.patch`, `check.md`, `reply.md` (the session's final reply to the user) |
| s11-t160, s11-t118 | `rubrics/rubric-b3-s11.md` (the row for the set) | `diff.patch`, `check.md` |
| s10-t001, s10-t033 | `rubrics/rubric-b3new.md` (the row for the set) | `diff.patch`, `check.md` |
| s6b-t179 | `rubrics/rubric-b3-s10.md` (the row for the set) | `diff.patch`, `check.md` |

`TASK.md` in each set is the request, verbatim. In `check.md`, an item marked UNDECIDABLE could not be measured.

## Output

One file per set, named `<set>.md`, in exactly the rubric's output format:

- a section headed `## <set>`
- a table whose header row starts with `| code |` and uses the rubric's column names exactly (design sets:
  `(a) AI느낌 수` and `(b) 쓸만함 1-5`; other sets: the criteria, then `총점 1-5`, then `근거`)
- every code exactly once in the table (integers), then the rank lines (`1. code, code` / `3. code`, competition
  ranking), every code exactly once

Please also report whether you opened any file outside this folder and `rubrics/`.
