# Stage 12 rubric — general code changes

Written 2026-10-27 from the general part of `stage10/judge-package/rubrics/rubrics-s2.md` (anchors, overall score,
rank, output format), before any judge saw an output. Stage 12 DESIGN §7: rule compliance is measured by the hidden
check; the judges score overall quality only.

Judges see one blind set per request: every output under a random code, how it was produced hidden. Each criterion is
scored 1–5 with these anchors:

- **5** a careful senior engineer would accept it as is
- **4** good; small gaps a reviewer would mention but not block on
- **3** usable after real fixes; noticeable gaps or mistakes
- **2** major parts missing or wrong
- **1** fails the task

| criterion | what earns a 5 |
|---|---|
| 요청 충족 1-5 | everything the request asks for is there and works as asked (endpoints, fields, status codes, UI behaviour, configuration) |
| 정확성 1-5 | no bugs a reviewer would find from the diff: correct logic, data handling, edge cases the request implies, no broken existing behaviour |
| 구조·가독성 1-5 | the change fits the existing code (where things live, how they are wired), clear names, no dead code, size proportional to the request |
| 검증 1-5 | the change is checked in proportion to its size: tests where the repository has them, error paths handled; the final reply says honestly what was and was not checked |

Do **not** score whether the change follows a company convention, naming scheme or process that the request does not
state. Score the change as a response to the request, using the starting repository in `_context/` to judge fit.

**총점 1-5** is the judge's overall verdict on the deliverable for the user who asked ("would I accept this as the
result of my request?"), not the average of the criteria. Judges also give a rank over the whole set (1 = best,
competition ranking: 1, 1, 3, …) ordered by 총점, ties broken by the criteria total, and a one-line reason per code.
Objective check results (`check.md`) are facts to use, not to re-derive.

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank
lines):

```
## <set name>

| code | 요청 충족 1-5 | 정확성 1-5 | 구조·가독성 1-5 | 검증 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <int> | <int> | <one line> |

1. <code>, <code>
3. <code>
```
