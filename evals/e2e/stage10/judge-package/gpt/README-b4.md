# Stage 10 blind judging — additional 4 sets (bundle 4)

The 11 sets already judged stay as they are. Judge only these 4 sets in this folder:

- `s10-t016/`, `s10-t263/`, `s10-t115/`, `s10-t198/`

Rubric: `../rubrics/rubric-b4.md` (its instructions, its output format, and the row for the set).
Each code folder has `diff.patch` (the session's change), `check.md` (objective check results) and `reply.md` (the
session's final reply to the user). `TASK.md` in each set is the request, verbatim. There are 18 outputs per set; view
all of them before scoring. Judge each set separately.

Output: one file per set, `<set>.md`, in exactly the rubric's format — a section headed `## <set>`, a table whose header
row starts with `| code |` and uses the rubric's column names exactly (the two criteria, `총점 1-5`, `근거`), every code
exactly once (integers 1-5), then the rank lines (`1. code, code` / `3. code`, competition ranking), every code exactly
once.

Please also report whether you opened any file outside `judge-package/gpt/` and `judge-package/rubrics/`.
