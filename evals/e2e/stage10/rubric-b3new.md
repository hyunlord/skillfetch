# Judging rubric — stage 10 new bundle (3) (fixed 2026-10-25, before the repos were built and before any session ran)

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
| s10-t001 | 기능 정확성 1-5 — `--dry-run` computes the same reconciliation, prints what would be written (which rows, with the values that differ) in a readable form, and writes nothing; without the flag the script behaves exactly as before | 범위·안전 1-5 — the change stays in the script (and its tests); no partial writes or commits in dry-run; the flag shows in `--help`; tests for the dry-run path |
| s10-t033 | 버그 수정 정확성 1-5 — Google Docs redirect hrefs (`google.com/url?q=`) are unwrapped to the real, decoded URL and kept; the unwrapped URL still goes through the existing allowlist (unsafe schemes still dropped); other sanitizer behaviour unchanged | 최소 diff·제약 준수 1-5 — change limited to the sanitize step; no new packages; toolbar code untouched; no unrelated edits; a test for the fix |
| s10-t114 | 문서 정확성 1-5 — the crate-level docs describe the wire packet byte by byte exactly as the encoder writes it: field order, sizes/offsets, endianness, magic and version, length, checksum and what it covers | 문서 품질 1-5 — clear layout (table or diagram), enough for someone writing a decoder in another language; builds as rustdoc; examples (if any) compile; no code changes |

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank lines):

```
## <set name>

| code | <criterion 1> | <criterion 2> | 총점 1-5 | 근거 |
|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <one line> |

1. <code>, <code>
3. <code>
```
