# Judging rubric — stage 6b bundle (3) (fixed before any session ran)

Judges see one blind set per task: every session's output under a random code, the condition hidden. Each set has
`TASK.md` (the request, verbatim); each code folder has `diff.patch` (the session's change against the starting
commit) and `check.md` (objective check results — facts to use, not to re-derive). Each criterion is scored 1–5:

- **5** a careful senior engineer would accept it as is
- **4** good; small gaps a reviewer would mention but not block on
- **3** usable after real fixes; noticeable gaps or mistakes
- **2** major parts missing or wrong
- **1** fails the task (or no change)

**총점 1-5** is the judge's overall verdict on the deliverable for the user who asked ("would I accept this as the
result of my request?"), not the average of the criteria. Rank the whole set (1 = best, competition ranking: 1, 1, 3, …)
by 총점, ties broken by the criteria total, with a one-line reason per code.

| set | criterion 1 | criterion 2 |
|---|---|---|
| s6b-t004 | 기능 완결 1-5 — due date field and migration, the periodic task, no duplicate sends via reminder_sent_at, the email template, wired into what the request named | 운영 적합 1-5 — the periodic schedule actually registered, time handling (UTC / "one day before"), failure and retry behaviour, tests |
| s6b-t133 | 레이어 캐시 1-5 — manifest + lockfile before `npm ci`, BuildKit npm cache mount, source copied after install, sensible `.dockerignore` | 실행 동작 1-5 — the image serves the app with the `start` script on port 3000; build steps that `next start` needs are present |
| s6b-t179 | 중복 제거 정확성 1-5 — keeps the earliest row per (owner_id, title) by created_at, deletes the rest, safe (transaction, ties, NULL created_at), runnable like initial_data.py, no new packages | 검증 출력 1-5 — before/after counts per day that a person can check against the database |
| s6b-t354 | 검사 정확성 1-5 — compares the DB's current revision with the script head(s) correctly, aborts startup on mismatch with a clear message, called in init() before init_db | 변경 범위 1-5 — the minimal diff the user asked for (one new function, one call), nothing unrelated |

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank lines):

```
## <set name>

| code | <criterion 1> | <criterion 2> | 총점 1-5 | 근거 |
|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <one line> |

1. <code>, <code>
3. <code>
```
