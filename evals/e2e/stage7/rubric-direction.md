# Direction-aware grading rubric (stage 7a-relabel)

The stage-3 step-2b prompt verbatim, with one added paragraph after the grade list (marked here only for the reader; the prompt sent is `sys-grade-direction.txt`). Each task in `blind-direction-40.jsonl` is graded on its own: the task text plus all its candidate rows. Return one line per row: `{"task_id", "candidate_id", "grade": 0-3, "process": true|false}`.

```text
You grade how useful each candidate "skill" (a reusable instruction document a coding agent can load before working)
would be for one developer task. You see the task and each candidate's id, title, full summary and tags.

Grade every candidate:
- 3 = directly about this task: following it would shape how this exact work is done
- 2 = clearly helpful for this task, though not specifically about it
- 1 = marginal: same general area, little practical value here
- 0 = unrelated, wrong stack/tool, or would mislead

When the task tells you how to work (a working direction such as test-first, minimal diff, no new dependencies,
accessibility first), a skill that fits the task but pulls against that way of working gets at most 1, and a skill
that directly handles that way of working can get 2 or more even if it fits the task's subject less well.

Also mark "process": true when the skill is mainly a method or workflow (how to work: test-first, planning,
debugging procedure, review checklist, refactoring procedure, documentation process), false when it is mainly
domain, tool or framework knowledge. Mark it for every candidate regardless of grade.

Small or trivial tasks (a one-line fix, a rename, a typo, a question) rarely deserve a 2 or 3.

Output JSON only: [{"skill": "<candidate id>", "grade": 0-3, "process": true|false}] — every candidate exactly once.
```

Added paragraph:

> When the task tells you how to work (a working direction such as test-first, minimal diff, no new dependencies, accessibility first), a skill that fits the task but pulls against that way of working gets at most 1, and a skill that directly handles that way of working can get 2 or more even if it fits the task's subject less well.
