# Judging rubric — stage 11 bundle (3) (fixed 2026-10-25, before the repos were built and before any session ran)

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
| s11-t160 | 릴리스 정확성 1-5 — `make release` now also builds the `cmd/tracker-ingest` image with ko and pushes it to the project's registry, tagged consistently with the existing release artifacts; a ko failure fails the release; the existing release steps still run as before | 범위·유지보수 1-5 — the change stays in the release tooling (Makefile, ko config, docs); reuses the Makefile's existing variables instead of hard-coding them; no Go code changes; readable for the next person who touches the release |
| s11-t162 | 설정 정확성 1-5 — `.goreleaser.yaml` builds `inventory-cli` only for darwin/arm64 and linux/amd64; Homebrew tap publishing is configured so a release updates the tap automatically (tap repository, the credentials it needs, install/test stanza); the config passes `goreleaser check` | 범위·운영 1-5 — the change stays in the release config (and the release workflow if the tap credentials need it); leftover windows-only settings handled sensibly; no Go code changes; nothing that would break the existing release |
| s11-t118 | 문서 정확성 1-5 — the Javadoc of `PaymentReconciliationService` (class and its public methods, at least `reconcileBatch`) is accurate to the code; `reconcileBatch` documents every exception it can throw with an `@throws` tag stating when it is thrown | 문서 품질·범위 1-5 — idiomatic Javadoc (summary sentence, `@param`/`@return`/`@throws`, `{@link}` where useful); builds with `javadoc` without doclint errors; no code behaviour changes |

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank lines):

```
## <set name>

| code | <criterion 1> | <criterion 2> | 총점 1-5 | 근거 |
|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <one line> |

1. <code>, <code>
3. <code>
```
