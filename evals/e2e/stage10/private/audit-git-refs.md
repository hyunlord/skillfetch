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

Exposure: no other session's code (the tips have no session commits). `log --all` and logs of `feature/room-history-replay` show commit subjects "stage10: router skill (…)" — seen by A-condition sessions E2/A/s10-t016-m1, E2/A/s10-t016-m3 (branch log) and E2/A/s10-t263-m2, E2/A/s10-t263-m3 (`log --all`). E2/R1/s10-t016-m2, -m3 and E2/R1/s2-api-m3 switched onto a branch whose tip equals their own start commit (s10-r); E2/A/d1-landing-m2 onto one at its own start commit (s6b-a): file content unchanged by the switch. `git worktree list` (E2/A/d1-landing-m2, E2/A/s10-t016-m1, E2/R1/s10-t016-m2) shows other worktree paths, which contain run ids with condition names (s10-E2-R1-…).

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
