# Stage 12/12b rulebook judging package — pass p2

Give the judge only this folder (`judge-package-rules/p2/`) and `judge-package-rules/rubrics/`.

`RULES.md` here is **the team's rules** for this repository. Read it first.

Each subfolder is one **set**: eighteen outputs for the same request, each under a random 8-hex code. The judge does
not know how any output was produced and should not try to find out. Judge each set separately, viewing every output in
the set before scoring. Rubric: `rubrics/rubric-s12-rules.md` (all sets).

In each set: `TASK.md` = the request, verbatim; `_context/` = the repository before the change. In each code folder:
`diff.patch` (the change), `check.md` (objective functional check results), `reply.md` (the final reply to the user).

## Output

One file per set, named `<set>.md`, in exactly the rubric's output format: a section headed `## <set>`, the table
with the rubric's column names (including `기존 동작 변경` with 예/아니오), every code exactly once in the table, then the
rank lines, every code exactly once. Please also report whether you opened any file outside this folder and `rubrics/`.
