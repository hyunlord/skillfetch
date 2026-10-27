# Stage 12 blind judging package — pass gpt

Give the judge only this folder (`judge-package/gpt/`) and `judge-package/rubrics/`.

Each subfolder is one **set**: nine outputs for the same request, each under a random 8-hex code. The judge does not
know how any output was produced and should not try to find out. Judge each set separately, viewing every output in the
set before scoring. Rubric: `rubrics/rubric-s12.md` (all sets).

In each set: `TASK.md` = the request, verbatim; `_context/` = the repository before the change. In each code folder:
`diff.patch` (the change), `check.md` (objective functional check results), `reply.md` (the final reply to the user).

## Output

One file per set, named `<set>.md`, in exactly the rubric's output format: a section headed `## <set>`, the table
with the rubric's column names, every code exactly once in the table (integers), then the rank lines, every code exactly
once. Please also report whether you opened any file outside this folder and `rubrics/`.
