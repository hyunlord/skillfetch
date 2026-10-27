# Stage 12/12b rubric with the team rulebook — general code changes

Written 2026-10-27 before any judge saw an output (stage12b/DESIGN.md §4, "규칙집 판정"). It is
`stage12-private/judge-package/rubrics/rubric-s12.md` with three changes, marked (R1)–(R3). The team's rules are in
`RULES.md` next to this folder.

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

(R1) **A change made to follow the team's rules (`RULES.md`) is not "beyond the request".** Do not lower 구조·가독성 or
요청 충족 because an output added a registry entry, a changelog fragment, an error-catalog entry, tokens, locale keys and
the like that the rules require.

(R2) Whether each output follows the team's rules is measured separately by a hidden check. Score overall quality as
above; following a team rule is never a reason to take points off. Do not add points just for following a rule either.

(R3) **Mark separately whether the output changed existing behaviour the request did not ask for**: an existing
endpoint's response shape or values, an existing function's behaviour, an existing field's format. Put 예 or 아니오 in the
column `기존 동작 변경`, and say what changed in 근거 when it is 예. A change of existing behaviour that a team rule
requires is still marked 예 (say "규칙 N" in 근거); score it under 정확성 by whether it breaks anything for existing
callers.

**총점 1-5** is the judge's overall verdict on the deliverable for the user who asked ("would I accept this as the
result of my request?"), not the average of the criteria. Judges also give a rank over the whole set (1 = best,
competition ranking: 1, 1, 3, …) ordered by 총점, ties broken by the criteria total, and a one-line reason per code.
Objective check results (`check.md`) are facts to use, not to re-derive.

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank
lines):

```
## <set name>

| code | 요청 충족 1-5 | 정확성 1-5 | 구조·가독성 1-5 | 검증 1-5 | 총점 1-5 | 기존 동작 변경 | 근거 |
|---|---|---|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <int> | <int> | 예/아니오 | <one line> |

1. <code>, <code>
3. <code>
```
