# Judging rubric — stage 10 bundle (4) (fixed before any session ran)

Judges see one blind set per task: every session's output under a random code, the condition hidden. Each set has
`TASK.md` (the request, verbatim); each code folder has `diff.patch` (the session's change against the starting
commit) and `check.md` (objective check results — facts to use, not to re-derive). Each criterion is scored 1–5:

(Added 2026-10-25, before judging; DESIGN §4.6) Each code folder also has `reply.md`, the session's final reply to the
user (mentions of the tooling used during the session were removed; DESIGN §4.6). Flags or explanations given in the
reply count for the criteria.

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
| s10-t016 | 기능 정확성 1-5 — on join the room's last 50 messages are replayed oldest first before live traffic, per room, bounded memory (a per-room ring buffer such as `VecDeque`), no duplicates or lost lines at the join boundary | 동시성·구조 1-5 — no lock held across awaits that could stall the room, no unbounded growth, sensible placement (room vs server), tests for the replay |
| s10-t263 | 제로 카피 1-5 — `parse_order_book` returns levels borrowing `&str` from the input (no per-level `String`), lifetimes explicit and sound, callers and helpers updated | 정확성·범위 1-5 — parsing behaviour and errors unchanged, existing tests still pass, change limited to what the request needs |
| s10-t115 | SAFETY 정당화 1-5 — every sound `unsafe` block has a `// SAFETY:` comment that states the actual invariant that makes it sound (bounds, alignment, aliasing, validity), not boilerplate | 불건전 지적 1-5 — the blocks that are not sound (`adc::sample_at`, `DmaBuffer::window`) are flagged with the reason instead of being justified; no invented guarantees; no unrequested code changes elsewhere |
| s10-t198 | 이전 정확성 1-5 — every `HabitEntity`/`CheckInEntity` record copied once with ids, dates, notes, archived state and streak counts intact, relationships preserved, saved | 일회성·안전 1-5 — runs on first start only via a `UserDefaults` flag set after a successful save, failure leaves the flag unset, wired into the existing startup hook, tests |

Output format per set (column names exactly as below; every code exactly once in the table and once in the rank lines):

```
## <set name>

| code | <criterion 1> | <criterion 2> | 총점 1-5 | 근거 |
|---|---|---|---|---|
| <code> | <int> | <int> | <int> | <one line> |

1. <code>, <code>
3. <code>
```
