# Router cost: where the extra turns go, and what to cut (issue #26)

Status: analysis and an e2e design. No e2e run, no change to the router or the server yet.
Measured 2026-10-26 with `scripts/router_cost.py` (no model calls).

## 1. Data and method

- **Sessions:** Stage 10, environment E1, main run only (tags m1–m3: 15 tasks × 3 runs per
  condition; numbers.md §21). Conditions:
  - A: no router;
  - R0: shipped router on the release index;
  - R1: the same router on index-staging-4;
  - R1s: the `resolve_and_load` variant, `assets/router-skill/variants/fast.md`.

  Transcripts were read in place, read-only, from the private e2e workspace. The per-session
  rows derived from them (counts and public skill ids only) are in
  `evals/e2e/stage10/derived/router-cost.jsonl`.
- **API calls:** one per assistant message id. Claude Code's `num_turns` (the "turns" column,
  as in §21) counts differently, so both are given.
- **Tokens:** the API's own usage numbers. Per call, input tokens, cache creation and cache
  reads add up exactly to the session totals in the result event. Output tokens per call are
  partial in the stream, so output appears only as a session total. "Uncached input" =
  input + cache creation.
- **Phases:** each API call is labelled by the skillfetch tool it calls:
  - `router_skill`: the router skill is invoked;
  - `tool_schema`: Claude Code's ToolSearch, which loads the deferred MCP tool schemas;
  - `profile`, `search`, `resolve`, `load`, `resolve_and_load`.

  Calls before the first of these are `pre`, calls after the last are `work`, and calls
  in between are `between`.
- **Result tokens:** the text a skillfetch tool returned, in characters / 4. A result stays
  in the context, so every later call reads it again. "Carried" = result tokens × the number
  of later calls.
- **Offline part:**
  - the shipped router's queries (R-c) on the 380 tasks, labelled with oracle v3;
  - `search_skills` called for real at each k, because each query's own top k is merged, so
    the result is not a cut of the k=50 list;
  - result size = the server's compact JSON, characters / 4.

  At k=50 this reproduces numbers.md §13 (release: hit@50 0.930, recall@50 0.808) and §20
  (index-staging-4, fixed labels: 0.845 / 0.624).

## 2. Where the router's extra cost goes

Medians over the 45 sessions of each condition:

| cond | sessions | fired | turns | API calls | cost $ | uncached input | cache read | output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 45 | 0 | 9 | 7 | 0.329 | 19,373 | 197,288 | 6,857 |
| R0 | 45 | 45 | 15 | 12 | 0.525 | 33,313 | 424,441 | 8,184 |
| R1 | 45 | 45 | 16 | 12 | 0.542 | 36,525 | 444,766 | 8,231 |
| R1s | 45 | 43 | 17 | 12 | 0.615 | 38,744 | 466,605 | 8,380 |

Router minus A on the same task (mean over sessions of the session minus the median A
session of its task):

| cond | turns | API calls | cost $ | uncached input | cache read | output |
|---|---:|---:|---:|---:|---:|---:|
| R0 | +6.56 | +4.76 | +0.174 | +12,419 | +237,431 | +1,511 |
| R1 | +7.53 | +5.47 | +0.203 | +14,859 | +286,456 | +1,534 |
| R1s | +8.11 | +5.47 | +0.240 | +18,660 | +293,009 | +1,763 |

Per phase (mean per fired session; R1 and R1s in `scripts/router_cost.py` output):

| R0 phase | API calls | uncached input | cache read | result tokens | carried |
|---|---:|---:|---:|---:|---:|
| router_skill | 1.00 | 7,060 | 19,413 | 8 | 91 |
| tool_schema | 1.00 | 1,379 | 26,471 | 0 | 0 |
| profile | 1.00 | 1,990 | 27,848 | 61 | 596 |
| search | 1.00 | 257 | 29,836 | 3,137 | 26,454 |
| resolve | 0.07 | 357 | 2,001 | 5 | 40 |
| load | 0.07 | 33 | 2,359 | 541 | 3,798 |
| resolve_and_load | 0.47 | 2,536 | 14,033 | 2,166 | 19,721 |
| work | 7.82 | 20,944 | 364,087 | 0 | 0 |

- **The cost is the chain itself.**
  - Every fired session made 4–5 calls before work: invoke the router skill; ToolSearch; `profile_repo`; `search_skills`; then resolve and load.
  - Each of these calls re-reads a context of 20–30k tokens.
  - Those calls (122k) plus the results they leave behind (51k carried) make about 173k cache-read tokens. That is 73% of R0's +237k over A.
  - The router skill's own text is the largest uncached item (7k).
- **Work after the router is about what A does.** API calls outside the router phases minus A's calls on the same task:
  - R0, bundles (1)–(4): −0.17, +0.17, +1.33, −0.42;
  - R1: +2.75, −0.75, −0.56, −0.08.

  So the extra skill text mostly does not lengthen the work. The exception is R1 on design, (1) +2.75.
- **R0 often called `resolve_and_load` unprompted** (0.47 per session), although its router says resolve, then load. Separate resolve-then-load calls were rare: 0.07 per session in R0, 0.20 in R1.
- **Many sessions ran the chain and loaded nothing.** Each spent 4 router calls and about 125k cache-read tokens.

  | cond | fired | loaded nothing | by bundle | cache read + carried, mean |
  |---|---:|---:|---|---:|
  | R0 | 45 | 21 | (3) 9, (4) 12 | 126,162 |
  | R1 | 45 | 6 | (3) 6 | 123,242 |
  | R1s | 43 | 4 | (3) 4 | 133,949 |

## 3. Candidates, measured offline

**k and summary length** (release index, R-c queries, oracle v3; tasks scored: all 284, 2a
209; result tokens are medians over all 380 tasks):

| k | hit@k all | recall@k all | hit@k 2a | recall@k 2a | result tokens, summary 160 / 120 / 80 chars |
|---:|---:|---:|---:|---:|---|
| 10 | 0.806 | 0.486 | 0.632 | 0.521 | 625 / 574 / 483 |
| 20 | 0.877 | 0.646 | 0.751 | 0.640 | 1,248 / 1,146 / 966 |
| 30 | 0.905 | 0.737 | 0.775 | 0.684 | 1,870 / 1,716 / 1,447 |
| 50 | 0.930 | 0.808 | 0.813 | 0.746 | 3,120 / 2,862 / 2,408 |

(index-staging-4 on the same fixed labels: 0.743 / 0.426 at k=20, 0.803 / 0.500 at k=30,
0.845 / 0.624 at k=50. Its new records are unlabelled here, see §20.)

**Where the sessions' picks ranked** in their own k=50 search result:

| cond | picks | rank ≤ 10 | ≤ 20 | ≤ 30 | > 30 | > 30 and graded ≥ 2 |
|---|---:|---:|---:|---:|---:|---:|
| R0 | 44 | 16 | 23 | 34 | 10 | 7 |
| R1 | 73 | 39 | 52 | 67 | 6 | 4 |
| R1s | 75 | 41 | 58 | 67 | 8 | 7 |

Grades come from the Stage 10 grading (`evals/e2e/stage10/private/grades-s10.jsonl`); every pick ranked below 30 is
graded. Most of them are on the design tasks: `refactoring-ui`, `next-best-practices`,
`email-marketing` and `frontend-design`. Design is the one task type where the expert's
skill changed the result (numbers.md §11).

**Savings estimate per fired session**
- Removing a call saves that call's context.
- Shrinking a result saves its tokens on the first read plus once per later call (search: 8.4
  later calls in R0).
- Assumes nothing else changes.

| candidate | what it changes | measured offline | input tokens saved | API calls saved | risk |
|---|---|---|---:|---:|---|
| **P: server-side profile** (not in #26's list; from §2) | `search_skills` without `profile` uses the profile of the server's working directory; the router drops the `profile_repo` step | ranking unchanged: every fired session passed `profile_repo`'s result for the same repository; the offline eval uses no profile | ≈ 30,400 (1,990 uncached + 27,848 read + 596 carried) | 1 | the server's working directory must be the repository root (to be checked for project-scoped MCP servers); if it is not, the router keeps its `profile_repo` call |
| S80: summaries cut to 80 chars | `one_line` limit 160 → 80 | ranking unchanged; result 3,120 → 2,408 tokens | ≈ 6,700 | 0 | the model chooses from shorter summaries; selection quality unmeasured offline |
| S120: summaries cut to 120 chars | 160 → 120 | 3,120 → 2,862 | ≈ 2,400 | 0 | as S80, smaller |
| K30: k = 30 | default k 50 → 30 | hit@k 0.930 → 0.905, recall 0.808 → 0.737; picks at rank > 30: R0 10 of 44 (7 graded ≥ 2) | ≈ 11,800 | 0 | **cuts the design picks**; not recommended |
| K20: k = 20 | 50 → 20 | hit 0.877, recall 0.646; picks at rank > 20: R0 21 of 44 | ≈ 17,700 | 0 | as K30, worse |
| RL: one `resolve_and_load` call (R1s) | router steps 6–7 as one call | sessions already used it unprompted (R0 0.47); separate calls only 0.07 / 0.20 per session | ≤ 6,000 | ≤ 0.2 | measured in Stage 10: no turn saving (§21: R1s criterion (a) held in 1 of 4 bundles) |
| SK: skip before search when unsure | decide from the task alone, before `search_skills` | not measurable offline: the decision needs the model. Upper bound: the sessions that loaded nothing (R0 21/45, R1 6/45) at about 125k each | up to ≈ 125,000 on such tasks | 4 | a false skip loses the design gain; needs its own selection-style measurement first |

Not under our control: the ToolSearch call (Claude Code defers MCP tool schemas), about 28k
per session.

## 4. Recommendation

1. **P (server-side profile).** It removes one of the four fixed calls, about 30k input
   tokens per fired session, roughly an eighth of R0's cache-read overhead. Offline ranking
   cannot change, because the profile is the same. It needs a small server change and a
   router edit; neither is made here.
2. **S80 together with P, as a second arm.** It cuts about 6.7k more per session without
   touching the ranking, but it changes what the model reads when choosing, which only a
   session run can check. Before the e2e run, a cheap pre-check: the 6a offline selection
   (380 tasks, `claude -p` on the plan) with 80-character summaries. It must keep hit
   (≥ 1 relevant pick) within 0.03 of S-b′'s and none-accuracy no lower.

Not recommended:
- **K30 and K20:** 23% of R0's picks (7 of them relevant) sat below rank 30, mostly on design.
- **RL:** already measured, no saving.
- **SK:** the largest potential, but the false-skip rate is unknown. Measure it offline in a
  selection-style run before considering an e2e run.

## 5. e2e design (not run)

- **Tasks:** Stage 10's four bundles, 15 tasks; for bundle (3), the remeasurement tasks
  (t001, t033, t114). Same repositories, hidden checks and harness (§21).
- **Environment:** E1 only. Index: index-staging-4, the next release candidate.
- **Conditions** (3 runs each, 135 sessions):
  - **C**: the current router and server (Stage 10's R1, rerun now, not reused);
  - **P**: server-side profile, router without the `profile_repo` step;
  - **PS**: P plus 80-character summaries.
- **Judging:** as in Stage 10. Two blind Claude passes (p1, p2) and GPT, over diffs, checks
  and (bundle 4) redacted final answers. D is defined per judge as in §21.
- **Cost estimate:** Stage 10 R1 median $0.542 per session × 135 ≈ $73 API-price
  equivalent on the plan.
- **Gate, fixed before the run.** Each variant against C:
  - (i) cost: the variant's median API calls per fired session are at least 1 lower (P,
    PS) in at least 3 of 4 bundles, and its mean uncached input + cache read per session is
    lower overall;
  - (ii) quality: in no bundle is the variant's mean score more than D below C's, for each
    judge separately;
  - (iii) bundle (4): sessions that loaded a relevant skill (grade ≥ 2), variant ≥ C − 1,
    of 12;
  - (iv) bundle (3): sessions that loaded any skill, variant ≤ C + 1, of 9;
  - (v) median turns: no bundle above C + 2.
- **Ship rule:** ship PS if it passes all five; else P if it does; else nothing.
- **Before the run:**
  - P's server change, with an offline test that the derived profile equals `profile_repo`
    on the task repositories;
  - the S80 selection pre-check above (if it fails, the PS arm is dropped);
  - the gate and the ship rule written into the stage's DESIGN.md.

## 6. Limits

- One stage, 15 tasks, 3 runs; the per-phase means are over 43–45 fired sessions.
- Savings are estimates from the measured phase costs under "nothing else changes". A
  shorter chain can change what the model does next.
- Result sizes are characters / 4, not tokenizer counts.
- The K30/K20 evidence is the ranks of what sessions picked. A smaller k would also change
  the 50 summaries the model reads, which this does not capture.
