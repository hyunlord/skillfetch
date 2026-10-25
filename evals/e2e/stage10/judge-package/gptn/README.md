# Stage 10 blind judging — new bundle 3 (3 sets)

Give the judge only this folder (`judge-package/gptn/`) and `judge-package/rubrics/rubric-b3new.md`.

Sets: `s10-t001/`, `s10-t033/`, `s10-t114/`. Each set holds 9 outputs for the same request under random 8-hex codes;
`TASK.md` is the request, verbatim. Each code folder has `diff.patch` (the session's change) and `check.md` (objective
check results). The judge does not know how any output was produced and should not try to find out. View all 9
outputs of a set before scoring it; judge each set separately.

Rubric: `../rubrics/rubric-b3new.md` (its instructions, its output format, and the row for the set).

Output: one file per set, `<set>.md`, in exactly the rubric's format — a section headed `## <set>`, a table whose header
row starts with `| code |` and uses the rubric's column names exactly (the two criteria, `총점 1-5`, `근거`), every code
exactly once (integers 1-5), then the rank lines (`1. code, code` / `3. code`, competition ranking), every code exactly
once.

Please also report whether you opened any file outside `judge-package/gptn/` and `judge-package/rubrics/`.
