# Stage 10 git ref/object audit (2026-10-25)

Stage 10 harness: each session ran in `git worktree add --detach <wt> <base>` of the main repo (run_s10.py:93; nextjs/fastapi via run_stage1.py:39). Worktrees share the main repo's refs, reflogs and objects (reachable and unreachable).

Scope: 321 transcripts (`stage10-private/runs/**/*.jsonl`, incl. harness-fail and pilot), 1596 Bash calls, 530 git-related. No Read/Glob/Grep on `.git/` paths.

- `git fsck`, `cat-file`, `reflog`, `rev-list`, `lost-found`, `for-each-ref`, `show-ref`: **0 calls** → no session touched unreachable objects.
- `git show <hash>`: 1 call (`git show --stat 2678925` = s2-docs start commit, in the session's own history).
- **E1 (gate environment): 0 sessions** read refs or objects outside their own history.

## A. Read or switched onto refs outside the session's own history: 10 sessions (all E2)

Every referenced branch was created by an earlier session that made no commit; tips (from session-created-branches.txt):

- `feature/room-history-replay` → 099753b (s10-t016 s10-r router commit; created by E2/R1/s10-t016-p0, no commits)
- `feature/landing-s10-e2a-d1` → 76de3ce (nextjs base s6b-a; created by E2/A/d1-landing-m1, no commits)
- `perf/l2-zero-copy` → 4b89110 (s10-t263 base s10-a; created by E2/A/s10-t263-m1, no commits)
- `feature/bookmarks-api-s10-m1` → 42a09c9 (s2-api base s6b-a; created by E2/A/s2-api-m1, no commits)
- `feature/bookmarks-api-s10-e2-r1-m3` → f34b78f (s2-api s10-r router commit; created by harness-fail/E2/R1/s2-api-m3, no commits)

| session | calls |
|---|---|
| E2/A/d1-landing-m2 | git checkout feature/landing-s10-e2a-d1; git branch -a -v; git worktree list |
| E2/A/s10-t016-m1 | git log --oneline -3 feature/room-history-replay; git rev-parse HEAD feature/room-history-replay; git branch; git worktree list |
| E2/A/s10-t016-m3 | git log --oneline -3 feature/room-history-replay; git branch |
| E2/A/s10-t263-m2 | git log --oneline --all; git log --oneline -3 perf/l2-zero-copy; git branch |
| E2/A/s10-t263-m3 | git log --oneline -5 --all; git branch |
| E2/R1/s10-t016-m1 | git log --oneline -3 feature/room-history-replay; git branch |
| E2/R1/s10-t016-m2 | git log --oneline -5 feature/room-history-replay; git diff HEAD feature/room-history-replay --stat; git switch feature/room-history-replay; git branch; git worktree list; git stash list |
| E2/R1/s10-t016-m3 | git log --oneline -3 feature/room-history-replay; git diff HEAD feature/room-history-replay --stat; git checkout feature/room-history-replay; git branch |
| E2/R1/s2-api-m1 | git log --oneline -3 feature/bookmarks-api-s10-m1; git branch |
| E2/R1/s2-api-m3 | git log --oneline -3 feature/bookmarks-api-s10-e2-r1-m3; git checkout feature/bookmarks-api-s10-e2-r1-m3; git branch |

Exposure: no other session's code (the tips have no session commits). `log --all` and logs of `feature/room-history-replay` show commit subjects "stage10: router skill (…)" — seen by A-condition sessions E2/A/s10-t016-m1, E2/A/s10-t016-m3 (branch log), E2/A/s10-t263-m2, E2/A/s10-t263-m3 (`log --all`) and E2/A/d1-landing-m2 (`branch -a -v`; corrected 4 → 5, see below). E2/R1/s10-t016-m2, -m3 and E2/R1/s2-api-m3 switched onto a branch whose tip equals their own start commit (s10-r); E2/A/d1-landing-m2 onto one at its own start commit (s6b-a): file content unchanged by the switch. `git worktree list` ran in E2/A/d1-landing-m2, E2/A/s10-t016-m1, E2/R1/s10-t016-m2; only d1-landing-m2's output showed other directories (earlier-stage worktrees nx-*-R1 …); the other two showed the main checkout and their own directory (corrected, see below).

## B. Listed shared refs or worktrees only (names, no contents): 22 more sessions (all E2)

| session | calls |
|---|---|
| E2/A/d1-landing-m1 | git branch |
| E2/A/d1-landing-m3 | git branch |
| E2/A/s10-t016-m2 | git branch -a |
| E2/A/s10-t016-p0 | git branch |
| E2/A/s10-t115-m3 | git branch |
| E2/A/s10-t198-m2 | git branch |
| E2/A/s2-api-m1 | git branch |
| E2/A/s2-api-m2 | git branch |
| E2/A/s2-api-m3 | git branch |
| E2/A/s2-data-m1 | git branch |
| E2/A/s2-data-m3 | git branch |
| E2/A/s2-tests-m1 | git branch |
| E2/A/s2-tests-m3 | git branch |
| E2/A/s6b-t133-m1 | git branch |
| E2/A/s6b-t133-m3 | git branch |
| E2/R1/d1-landing-m1 | git branch -a |
| E2/R1/d1-landing-m3 | git branch -a |
| E2/R1/s10-t016-p0 | git branch |
| E2/R1/s2-api-m2 | git branch |
| E2/R1/s2-data-m1 | git branch |
| E2/R1/s2-data-m2 | git branch |
| harness-fail/E2/R1/s2-api-m3 | git branch |

## C. Second criterion: other sessions' branch or directory names in tool output (any command) — added 2026-10-25

Definition: tool output (any command) shows another session's branch name or worktree directory name; the session's own created branches and own directory excluded; repo branch list incl. the 18 deleted session branches; names 'main'/'master' and <5-char names without '-' excluded.

- **E1: 0 sessions.** The earlier report figure "E1 R0 1/45" (report §8) is E1/R0/s2-tests-m2: `git log --stat -3 | head -40` printed the subject of its own start commit, "stage10: router skill (main 57acc45 = 3fef3f8 assets/router-skill/SKILL.md)". No branch name (piped output, no decoration), no condition token; the router words are from its own history.
- **E2: 33 sessions** (A 21, R1 12, incl. harness-fail/E2/R1/s2-api-m3) — the 32 sessions of A/B above plus E2/A/d3-dashboard-m3, whose own `git checkout -b feature/dashboard` failed with "a branch named 'feature/dashboard' already exists" (created by E2/R1/d3-dashboard-m2 at nextjs s10-r df50fcf; no switch).
  - names with a condition token (r1, e2, e2a, …; e.g. feature/bookmarks-api-s10-e2-r1, e2e-r1, feature/landing-page-c-r1): 14 sessions
  - only the router condition branches s10-r / s10-rs: 18 sessions
  - neither: 1 (E2/A/d3-dashboard-m3)
- **Other sessions' directory names: 3 sessions (all E2)** — E2/A/d1-landing-m2 (`git worktree list`: earlier-stage worktrees nx-01, nx-01-R1, nx-01-R1R2, …), E2/R1/d1-landing-m1 (`lsof` cwd of a process: concurrent session s10/s10-E2-R1-s2-docs-m1), E2/A/s2-api-m1 (`lsof`/`ps` of the server on port 8765: s6b/s6b-A-s2-api-r1, a server process left from Stage 6b).
- Reconciliation with report §8 ("E2 A 25/45, E2 R1 12/45, E1 R0 1/45"): that count also included a session's own created branch names and the router subject of its own start commit; this criterion excludes both.
- Per-session names: `audit-git-refs.json` → `criterion_output_names.sessions`.

## Corrections (2026-10-25)
- router commit subject seen by A-condition sessions: 5, not 4 (d1-landing-m2 via branch -a -v)
- `git worktree list` in E2/A/s10-t016-m1 and E2/R1/s10-t016-m2 showed only the main checkout and the session's own directory; only E2/A/d1-landing-m2 saw other (earlier-stage) worktree names. Other-session directory names were seen by 3 sessions via 3 channels (worktree list 1, lsof 2)
