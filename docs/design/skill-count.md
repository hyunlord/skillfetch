# Skill count and the load budget; re-firing on later tasks

Two items, both without model calls:

1. How many skills the router picks per session, and whether `load_skills`' budget
   (`max_tokens`, 8,000 by default) limited the picks, in Stage 10, 11 and Q.
2. Two router variants for re-firing on a later task in the same conversation (Stage Q2).
   They are not run yet; the shipped router is unchanged.

## 1. Skill count and the budget

### 1.1 Data and method

- **Script:** `scripts/skill_count.py`.
  - `extract` reads the session transcripts in the e2e workspace and writes one derived row
    per session (Stage 10, 11) or request (Stage Q) that called `search_skills`.
  - The rows are in `evals/e2e/skill-count/rows.jsonl`. They hold skill ids, counts and
    grades only. A local pinned path is written as `path:<local>`.
  - `report` prints the tables below from the rows.
- **Sessions:** the main runs with the router on.
  - Stage 10: E1 R0, R1, R1s and E2 R1 (45 each), plus the bundle (3) remeasurement (9
    each).
  - Stage 11: R0 and R1 (72 each).
  - Stage Q: Q1 on (12 requests), Q2 S and C (20 each), Q5 (16), Q6 (6).
  - 425 in all. 370 called `search_skills`, and only those are counted. The 55 others include
    all 20 Q2 S requests, Q2 C positions 1 and 3, the ten Q5 trivial edits, and 15 Stage 10 / 11
    sessions that loaded the router but did not search.
- **Picks:** the `auto_ids` passed to `resolve_set` or `resolve_and_load`. Pinned ids (Q5,
  the user named a skill) are counted separately.
- **Picked tokens:** the sum of the picks' `token_estimate` as the search results showed it
  (characters / 4 of the indexed file).
- **Budget drop:** an `errors` entry of `load_skills` or `resolve_and_load` that says "over
  max_tokens" (`src/skillfetch/mcp/session.py`).
- **Grade ≥ 2 skill not picked:** a result of the task search (the one with four queries)
  that has a label of grade ≥ 2 and is neither picked nor pinned.
  - Labels are used only where they were made for the same request text:
    - the run-c labels (Stage 9) for bundle (4): t016, t263, t115, t198;
    - the pre-run grading of both indexes' top 50 for the bundle (3) tasks (t001, t033,
      t114; t160, t162, t118) and for t266.
  - The other tasks (design, the stage 2 tasks, Stage 10's first bundle (3), the Q2
    repository) have grades only for the skills that were loaded, so they are left out of
    this count.
  - Results without a label are not counted (median 33–42 of 50 have one).

### 1.2 Picks per session

| stage | group | sessions | 0 | 1 | 2 | 3 | pinned ≥ 1 | median picked tokens | max picked tokens | picked > 8,000 | loaded > 8,000 | budget drops |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stage 10 | E1 R0 | 45 | 21 | 6 | 16 | 2 | 0 | 4,616 | 7,954 | 0 | 0 | 0 |
| Stage 10 | E1 R0 b3 remeasure | 9 | 0 | 6 | 3 | 0 | 0 | 1,077 | 3,474 | 0 | 0 | 0 |
| Stage 10 | E1 R1 | 45 | 6 | 8 | 28 | 3 | 0 | 4,474 | 7,414 | 0 | 0 | 0 |
| Stage 10 | E1 R1 b3 remeasure | 8 | 4 | 2 | 2 | 0 | 0 | 2,544.5 | 4,470 | 0 | 0 | 0 |
| Stage 10 | E1 R1s | 43 | 4 | 7 | 28 | 4 | 0 | 4,616 | 7,704 | 0 | 0 | 0 |
| Stage 10 | E1 R1s b3 remeasure | 9 | 5 | 3 | 1 | 0 | 0 | 1,105 | 1,133 | 0 | 0 | 0 |
| Stage 10 | E2 R1 | 38 | 1 | 9 | 24 | 4 | 0 | 4,332 | 7,988 | 0 | 0 | 0 |
| Stage 11 | R0 | 70 | 39 | 13 | 14 | 4 | 0 | 3,916 | 7,975 | 0 | 0 | 0 |
| Stage 11 | R1 | 69 | 11 | 14 | 41 | 3 | 0 | 3,039 | 7,207 | 0 | 0 | 0 |
| Stage Q | Q1 on | 12 | 0 | 2 | 9 | 1 | 0 | 3,837.5 | 7,207 | 0 | 0 | 0 |
| Stage Q | Q2 C (positions 2, 4) | 10 | 0 | 5 | 3 | 2 | 0 | 4,713 | 7,380 | 0 | 0 | 0 |
| Stage Q | Q5 named | 6 | 0 | 5 | 1 | 0 | 6 | 3,299 | 4,218 | 0 | 0 | 0 |
| Stage Q | Q6 (fetch blocked) | 6 | 0 | 1 | 5 | 0 | 0 | 4,679 | 7,207 | 0 | 0 | 0 |
| all | | 370 | 91 | 81 | 175 | 23 | 6 | 4,043 | 7,988 | 0 | 0 | 0 |

- Median and max picked tokens are over the sessions with at least one pick.
- "0" means the session searched and picked nothing.
- **Load calls:** 279 sessions called `load_skills` or `resolve_and_load`, and every one used
  `max_tokens` 8,000 (the default).
- **Other load errors:** 11, all in Q6, where the fetch was blocked by design. A fetch error
  refuses the skill before the budget check.

Picked tokens, sessions with ≥ 1 pick (279):

| picked tokens | sessions |
|---|---:|
| 0–2,000 | 35 |
| 2,001–4,000 | 104 |
| 4,001–6,000 | 69 |
| 6,001–7,000 | 31 |
| 7,001–8,000 | 40 |
| > 8,000 | 0 |

### 1.3 Grade ≥ 2 skills in the results that were not picked (labeled tasks)

| stage | group | sessions on labeled tasks | labeled results (median of 50) | with an unpicked grade ≥ 2 | of those, < 3 picks | of those, the smallest unpicked one would go over 8,000 |
|---|---|---:|---:|---:|---:|---:|
| Stage 10 | E1 R0 | 12 | 38 | 0 | 0 | 0 |
| Stage 10 | E1 R0 b3 remeasure | 9 | 33 | 0 | 0 | 0 |
| Stage 10 | E1 R1 | 12 | 41 | 12 | 11 | 0 |
| Stage 10 | E1 R1 b3 remeasure | 8 | 42 | 0 | 0 | 0 |
| Stage 10 | E1 R1s | 11 | 42 | 11 | 10 | 0 |
| Stage 10 | E1 R1s b3 remeasure | 9 | 42 | 0 | 0 | 0 |
| Stage 10 | E2 R1 | 11 | 40 | 11 | 11 | 0 |
| Stage 11 | R0 | 46 | 37 | 0 | 0 | 0 |
| Stage 11 | R1 | 45 | 38 | 30 | 28 | 0 |
| Stage Q | Q1 on | 4 | 41 | 4 | 4 | 0 |
| Stage Q | Q5 named | 2 | 40 | 2 | 2 | 0 |
| Stage Q | Q6 | 2 | 40 | 2 | 2 | 0 |
| all | | 171 | | 72 | 68 | 0 |

- **Where they are:** all 72 are on the bundle (4) tasks and t016 / t266, with index-staging-4
  (R1, R1s, Q).
- **Picks in those 72 sessions:** 1 pick in 2, 2 picks in 66, 3 picks in 4. Most had 2 or 3
  unpicked grade ≥ 2 results (median 2, max 3); one had a grade 3.
- **Budget left** after adding the smallest unpicked grade ≥ 2 skill (the 68 sessions with
  < 3 picks): min 189 tokens, median 4,381.
- **Filling the set to 3** with the smallest unpicked grade ≥ 2 skills stays within 8,000 in
  66 of the 68.
- **Grades of the picks on labeled tasks:** 3: 101, 2: 45, 1: 24, 0: 5, no label: 7.

### 1.4 Conclusion

**The budget was not a constraint in these runs.**
- **Nothing was dropped:** no skill was dropped for the budget in 279 load calls, all with
  the 8,000 default.
- **No set went over:** no session's picks summed to more than 8,000 (max 7,988).
- **Unpicked skills would have fit:** 68 sessions left out a labeled grade ≥ 2 result while
  under the 3-pick cap. In every one, the smallest such skill would have fit.

**Fewer picks than allowed.** The sessions picked fewer skills than the cap and the budget
allowed:
- 2 picks is the most common count (175 of 370);
- 3 picks occurred 23 times.

**What the records cannot show.** The router tells the model to keep the set under the
budget (step 4), and 40 sessions picked between 7,001 and 8,000 tokens. Whether that
instruction changed a choice cannot be read from these records.

**Limits.**
- **Unlabeled results:** 8–17 of each task search's 50 results have no label (group medians).
- **Unlabeled tasks:** the design and stage 2 tasks have no labels for their results at all.
- **Token measure:** `token_estimate` counts the indexed file, while the budget counts the
  loaded body. Both are characters / 4.

## 2. Re-firing on later tasks in one conversation (Stage Q2)

### 2.1 What Stage Q2 showed

Source: the e2e workspace, Stage Q report §3 (not yet published).

**S arm** (one session, `--resume`, four tasks, 5 runs): 0 of 20 requests called skillfetch.
That includes position 1, a design task that named a local skill.

**C arm** (a new session per task, 5 runs):

| position | task | sessions that fired |
|---:|---|---:|
| 2 | Rust | 5/5 |
| 3 | README typo (a skip case) | 0/5 |
| 4 | Python | 5/5 |

Position 1 was 0/5 in C as well.

### 2.2 Variants (not run; the shipped `assets/router-skill/SKILL.md` is unchanged)

**(a) `assets/router-skill/variants/refire.md`**
- sha256 `e3402ffbda29a64b8e026662f315ac91968c467caa2a51fdde38d8bbc9f2d9aa`.
- This is the shipped router (sha256 `3efef1e0…f040`, S-b′) with one change. The description
  and the body's first line both say: "Run it again each time a new task arrives in the same
  conversation; do not reuse the skill choice from an earlier task."
- No other byte differs; the file is 60 lines.

**(b) `refire.md` plus a project `CLAUDE.md` line**
- The line is the file `assets/router-skill/variants/refire-CLAUDE.md`, sha256
  `f62aa422ce814ca530167e3ef8b9fe1dd0240b0065e7778e2e1a757684a44f4c`. It is placed as the
  repository's `CLAUDE.md` (or appended to it), in the form of Stage 5's V2.
- The line is V2's sentence with the same re-run clause:

> Before your first tool call on any coding task in this repository (anything beyond a
> one-line edit, a rename or a question), run the `skillfetch-router` skill and follow its
> steps; run it again each time a new task arrives in the same conversation, and do not
> reuse the skill choice from an earlier task.
