# Stage-1 check validation (2026-10-22)

Worktrees: fastapi `b1125d8` (upstream), nextjs `76de3ce` (upstream import), under `stage1/wt/` (removed afterwards).
For each task: `run_check.py` on the pristine worktree ("baseline"), then on a second worktree with
`reference/<task>.patch` applied ("reference"). For s1-nx-07/08 the reference worktree's `node_modules` was deleted
after applying the patch so `run_check.py` ran `npm ci` from the patched lockfile. Baseline screen manifests were
captured with `run_check.py --capture-baseline` from the pristine worktrees. Every run left `git status --porcelain`
unchanged (checked by the driver before/after and by `check.json.git_status_unchanged`); no file needed restoring.
fastapi runs used throw-away `chk_<hex>` databases on localhost:55432, dropped at the end of each run.

Extra edge runs: s1-fa-07 with the reference tests plus a rewritten `is_active` check and condition files
(`.claude/…`, `.mcp.json`) present -> M1 `not_applicable` (null), M2/M3 caught, pass, worktree unchanged;
s1-fa-10 reference with `<E2 MCP server>/`, `<E2 plugin>/`, `.mcp.json` present -> pass; plus an extra untracked
`backend/notes.txt` -> fail on the changed-files item.

## Summary

| task | baseline (expected: fail) | failing items on baseline | reference |
|---|---|---|---|
| s1-fa-01 | fail | hidden tests test_s1_fa01.py all pass; hidden::test_2_title_asc; hidden::test_3_title_desc; hidden::test_4_created_at_asc; hidden::test_5_bad_order_by_422; hidden::test_6_bad_order_422 | pass |
| s1-fa-02 | fail | existing row at fe56fa70289e -> upgrade head -> is_done = false; hidden tests test_s1_fa02.py all pass; hidden::test_create_default_false; hidden::test_create_true; hidden::test_update_true_and_read | pass |
| s1-fa-03 | fail | '/' text contains 'Seed item 4'; '/' text contains 'Seed item 3'; '/' text contains 'Seed item 2'; '/' text has a standalone '4' | pass |
| s1-fa-04 | fail | grep -c 'Not enough permissions' items.py <= 1; grep -c 'Item not found' items.py <= 1 | pass |
| s1-fa-05 | fail | grep -cE 'skip: int = 0\|limit: int = 100' backend/app/api/routes/items.py == 0; grep -cE 'skip: int = 0\|limit: int = 100' backend/app/api/routes/users.py == 0 | pass |
| s1-fa-06 | fail | mutant M1 caught (backend/app/api/routes/items.py); mutant M2 caught (backend/app/api/routes/items.py) | pass (mutants caught 2/2) |
| s1-fa-07 | fail | mutant M1 caught (backend/app/api/deps.py); mutant M2 caught (backend/app/api/deps.py); mutant M3 caught (backend/app/api/deps.py) | pass (mutants caught 3/3) |
| s1-fa-08 | fail | hidden tests test_s1_fa08.py all pass; hidden::test_title_null_422_and_unchanged | pass |
| s1-fa-09 | fail | hidden tests test_s1_fa09.py all pass; hidden::test_login_upper_superuser_200; hidden::test_patch_me_case_variant_409; hidden::test_signup_case_variant_400; hidden::test_superuser_create_case_variant_400 | pass |
| s1-fa-10 | fail | all 20 Settings names occur in a '\|' line of backend/README.md; rows of the 5 required settings contain 'required'; changed files vs base == [backend/README.md] | pass |
| s1-nx-01 | fail | /users/102 links: Previous->/users/101, Next->/users/103, Back to list->/users | pass |
| s1-nx-02 | fail | /api/users/101: 200 and JSON == {"id":101,"name":"Alice"}; /api/users/999: 404 and JSON body; /api/users/abc: 400 and JSON body | pass |
| s1-nx-03 | fail | /does-not-exist: text has 페이지를 찾을 수 없습니다 / Users List / Footer; /does-not-exist: a link with href '/'; /does-not-exist: not 'This page could not be found'; /users/999: text has 페이지를 찾을 수 없습니다 / Users List / Footer; /users/999: a link with href '/'; /users/999: not 'This page could not be found' | pass |
| s1-nx-04 | fail | /about text contains Alice, Bob, Caroline, Dave, 101..104; /about links include /users/101../users/104 | pass |
| s1-nx-05 | fail | /: exactly one aria-current=page link, href /; /about: exactly one aria-current=page link, href /about; /users: exactly one aria-current=page link, href /users | pass |
| s1-nx-06 | fail | grep -rl sampleUserData (*.ts, *.tsx) only utils/sample-data.ts and lib/users.ts; lib/users.ts exports getAllUsers and getUserById | pass |
| s1-nx-07 | fail | npm test passes unmutated | pass (mutants caught 2/2) |
| s1-nx-08 | fail | npm test passes unmutated | pass (mutants caught 2/2) |
| s1-nx-09 | fail | /: html_lang == 'en'; /about: html_lang == 'en'; /users: html_lang == 'en'; /users/101: html_lang == 'en'; /does-not-exist: html_lang == 'en' | pass |
| s1-nx-10 | fail | JSDoc on every component, Props member (or @param) and exported type | pass |

## Deviations / readings

General
- "58 existing pass" = every non-hidden test passes and at least 58 of them pass (sessions may add tests; the 58 upstream ids are not pinned by name).
- Hidden tests are copied to `backend/tests/hidden_s1/` (not `tests/hidden/` as the yaml says) so they cannot collide with a session's own `tests/hidden/`. One fresh `chk_` DB per pytest run (unmutated and each mutant get their own DB).
- Hidden tests create users through `POST /users/signup` + login and items through the API, so they do not depend on test utils a session might change.
- Mutants are exact string replacements of the first occurrence. Target text missing -> `not_applicable` (null). If the unmutated suite fails, mutant items are null ("skipped") and the check fails on the suite item.
- Visual expectations (screens `expect:` lines, "judged from the PNGs", "judged by reading the diff") are null items; their PNGs are listed in `visual`.
- Baseline comparisons use manifests captured once from the upstream-commit worktrees (`baseline-screens/`). fastapi `/items` text is compared with UUIDs normalised (seeded item ids are random per run).
- A worktree guard snapshots tracked + untracked non-ignored files and restores them at the end (covers tool side effects such as `uv sync` lock rewrites); `check.json` reports `worktree_restored` and `git_status_unchanged`.
- nextjs validation used `76de3ce` (the import of the example; the yaml's `upstream_commit` `fa3830c` is the next.js monorepo sha it was imported from and is not in `repos/nextjs`).

Per task
- s1-fa-01: (7) "count == 3 in all 200 responses" passes on baseline (params are ignored, count 3) — consistent with the yaml baseline, which lists only (2)–(6) as failing.
- s1-fa-02: "previous head" = alembic head of the upstream commit (`fe56fa70289e`); the existing-row step fails on the baseline too (no column), in addition to the hidden test. `alembic check` requires rc 0 and "No new upgrade operations detected".
- s1-fa-03: "standalone 4" = a `4` not adjacent to `[0-9A-Za-z]` after removing "Seed item N", the seeded descriptions and UUIDs (so "4개" counts, "Seed item 4" and ids do not). `/items` must equal baseline in status, text (UUID-normalised) and links.
- s1-fa-04: behaviour-lock hidden test passes on baseline (13/13); the baseline fails only on the two greps, as specified.
- s1-fa-10: names are taken from the base commit's `config.py` (20). "Occurs" uses identifier boundaries (so `FIRST_SUPERUSER` is not satisfied by `FIRST_SUPERUSER_PASSWORD`). "Row for X" = a `|` line whose first cell contains X (fallback: any `|` line containing X); at least one such row must contain "required". "git diff --name-only <base>" also counts untracked non-ignored files, minus condition files.
- s1-nx-01: "text~Previous" = case-sensitive substring of the link text; hrefs compared exactly.
- s1-nx-02: `/api/users` unchanged = status 200 and parsed JSON equal to the baseline manifest (4 users).
- s1-nx-05: "nav links in the same order as baseline" = the first four links (href, text) equal the baseline's first four on each route.
- s1-nx-06: grep result must be a subset of {utils/sample-data.ts, lib/users.ts} (walk of *.ts/*.tsx skipping node_modules/.next/.venv/.git and condition dirs). Exports: a line with `export` and the name, or an `export { ... }` list containing it.
- s1-nx-07/08: `npm test` gets `-- --run` only when the script calls vitest without `run`/`--run`. On this tree, adding vitest needs `@types/react`/`@types/react-dom` >= 18 and `@types/node` >= 18 (npm peer conflicts; `npm install -D vitest` crashes in arborist otherwise) — the reference bumps them; sessions face the same environment.
- s1-nx-10: the diff count re-implements the yaml grep pipeline in Python; untracked new files under components/ or interfaces/ count as all-added lines. JSDoc check: a JSDoc on the component's declaration or on its `export default` statement; a Props member passes with its own JSDoc or a component `@param` whose last name segment matches (e.g. `@param props.title`). Fields of exported types in interfaces/ are not required (the check text only requires a JSDoc block per exported type).

## Item results

### s1-fa-01

**pristine upstream**: pass=False, 5.2 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=1
- FAIL — hidden tests test_s1_fa01.py all pass — passed=2 failed=5 skipped=0 expected=7
- pass — hidden::test_1_default_newest_first — passed
- FAIL — hidden::test_2_title_asc — failed
- FAIL — hidden::test_3_title_desc — failed
- FAIL — hidden::test_4_created_at_asc — failed
- FAIL — hidden::test_5_bad_order_by_422 — failed
- FAIL — hidden::test_6_bad_order_422 — failed
- pass — hidden::test_7_count_is_3 — passed

**reference patch**: pass=True, 9.2 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa01.py all pass — passed=7 failed=0 skipped=0 expected=7
- pass — hidden::test_1_default_newest_first — passed
- pass — hidden::test_2_title_asc — passed
- pass — hidden::test_3_title_desc — passed
- pass — hidden::test_4_created_at_asc — passed
- pass — hidden::test_5_bad_order_by_422 — passed
- pass — hidden::test_6_bad_order_422 — passed
- pass — hidden::test_7_count_is_3 — passed

### s1-fa-02

**pristine upstream**: pass=False, 7.6 s, git status unchanged=True, restored=[]

- pass — fresh DB: alembic upgrade head — rc=0
- pass — alembic check clean — rc=0; INFO [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments No new upgrade operations detected.
- pass — alembic downgrade -1 && upgrade head — downgrade rc=0, upgrade rc=0
- FAIL — existing row at fe56fa70289e -> upgrade head -> is_done = false — upgrade fe56fa70289e rc=0; insert rc=0; upgrade head rc=0; is_done = 'ERROR: column "is_done" does not exist\nLINE 1: SELECT is_done FROM item WHERE title = \'o
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=1
- FAIL — hidden tests test_s1_fa02.py all pass — passed=0 failed=3 skipped=0 expected=3
- FAIL — hidden::test_create_default_false — failed
- FAIL — hidden::test_create_true — failed
- FAIL — hidden::test_update_true_and_read — failed

**reference patch**: pass=True, 13.6 s, git status unchanged=True, restored=[]

- pass — fresh DB: alembic upgrade head — rc=0
- pass — alembic check clean — rc=0; INFO [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments No new upgrade operations detected.
- pass — alembic downgrade -1 && upgrade head — downgrade rc=0, upgrade rc=0
- pass — existing row at fe56fa70289e -> upgrade head -> is_done = false — upgrade fe56fa70289e rc=0; insert rc=0; upgrade head rc=0; is_done = 'f'
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa02.py all pass — passed=3 failed=0 skipped=0 expected=3
- pass — hidden::test_create_default_false — passed
- pass — hidden::test_create_true — passed
- pass — hidden::test_update_true_and_read — passed

### s1-fa-03

**pristine upstream**: pass=False, 12.6 s, git status unchanged=True, restored=[]

- pass — bunx tsc -p tsconfig.build.json — rc=0
- pass — bunx biome ci ./ — rc=0
- pass — screenshot.py screens (/ /items) — rc=0
- pass — '/' status 200, no page_errors — status=200 page_errors=[]
- FAIL — '/' text contains 'Seed item 4'
- FAIL — '/' text contains 'Seed item 3'
- FAIL — '/' text contains 'Seed item 2'
- pass — '/' text does not contain 'Seed item 1'
- FAIL — '/' text has a standalone '4' — after removing 'Seed item N', seeded descriptions and UUIDs; 4 not adjacent to [0-9A-Za-z]
- pass — /items text+links unchanged vs baseline — status 200 (baseline 200)
- null — visual screens/ — card with item count 4 and titles Seed item 4/3/2, styled like the app (index.png)

**reference patch**: pass=True, 18.3 s, git status unchanged=True, restored=[]

- pass — bunx tsc -p tsconfig.build.json — rc=0
- pass — bunx biome ci ./ — rc=0
- pass — screenshot.py screens (/ /items) — rc=0
- pass — '/' status 200, no page_errors — status=200 page_errors=[]
- pass — '/' text contains 'Seed item 4'
- pass — '/' text contains 'Seed item 3'
- pass — '/' text contains 'Seed item 2'
- pass — '/' text does not contain 'Seed item 1'
- pass — '/' text has a standalone '4' — after removing 'Seed item N', seeded descriptions and UUIDs; 4 not adjacent to [0-9A-Za-z]
- pass — /items text+links unchanged vs baseline — status 200 (baseline 200)
- null — visual screens/ — card with item count 4 and titles Seed item 4/3/2, styled like the app (index.png)

### s1-fa-04

**pristine upstream**: pass=False, 6.1 s, git status unchanged=True, restored=[]

- FAIL — grep -c 'Not enough permissions' items.py <= 1 — count=3
- FAIL — grep -c 'Item not found' items.py <= 1 — count=3
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa04.py all pass — passed=13 failed=0 skipped=0 expected=13
- pass — hidden::test_missing_404[delete] — passed
- pass — hidden::test_missing_404[get] — passed
- pass — hidden::test_missing_404[put] — passed
- pass — hidden::test_openapi_path_param_is_id — passed
- pass — hidden::test_other_users_item_403[delete] — passed
- pass — hidden::test_other_users_item_403[get] — passed
- pass — hidden::test_other_users_item_403[put] — passed
- pass — hidden::test_owner_200[delete] — passed
- pass — hidden::test_owner_200[get] — passed
- pass — hidden::test_owner_200[put] — passed
- pass — hidden::test_superuser_200[delete] — passed
- pass — hidden::test_superuser_200[get] — passed
- pass — hidden::test_superuser_200[put] — passed

**reference patch**: pass=True, 8.5 s, git status unchanged=True, restored=[]

- pass — grep -c 'Not enough permissions' items.py <= 1 — count=1
- pass — grep -c 'Item not found' items.py <= 1 — count=1
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa04.py all pass — passed=13 failed=0 skipped=0 expected=13
- pass — hidden::test_missing_404[delete] — passed
- pass — hidden::test_missing_404[get] — passed
- pass — hidden::test_missing_404[put] — passed
- pass — hidden::test_openapi_path_param_is_id — passed
- pass — hidden::test_other_users_item_403[delete] — passed
- pass — hidden::test_other_users_item_403[get] — passed
- pass — hidden::test_other_users_item_403[put] — passed
- pass — hidden::test_owner_200[delete] — passed
- pass — hidden::test_owner_200[get] — passed
- pass — hidden::test_owner_200[put] — passed
- pass — hidden::test_superuser_200[delete] — passed
- pass — hidden::test_superuser_200[get] — passed
- pass — hidden::test_superuser_200[put] — passed

### s1-fa-05

**pristine upstream**: pass=False, 6.6 s, git status unchanged=True, restored=[]

- FAIL — grep -cE 'skip: int = 0|limit: int = 100' backend/app/api/routes/items.py == 0 — count=1
- FAIL — grep -cE 'skip: int = 0|limit: int = 100' backend/app/api/routes/users.py == 0 — count=1
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa05.py all pass — passed=4 failed=0 skipped=0 expected=4
- pass — hidden::test_openapi_skip_limit[/items/] — passed
- pass — hidden::test_openapi_skip_limit[/users/] — passed
- pass — hidden::test_skip1_limit1[/items/-Item] — passed
- pass — hidden::test_skip1_limit1[/users/-User] — passed

**reference patch**: pass=True, 7.9 s, git status unchanged=True, restored=[]

- pass — grep -cE 'skip: int = 0|limit: int = 100' backend/app/api/routes/items.py == 0 — count=0
- pass — grep -cE 'skip: int = 0|limit: int = 100' backend/app/api/routes/users.py == 0 — count=0
- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa05.py all pass — passed=4 failed=0 skipped=0 expected=4
- pass — hidden::test_openapi_skip_limit[/items/] — passed
- pass — hidden::test_openapi_skip_limit[/users/] — passed
- pass — hidden::test_skip1_limit1[/items/-Item] — passed
- pass — hidden::test_skip1_limit1[/users/-User] — passed

### s1-fa-06

**pristine upstream**: pass=False, 14.2 s, git status unchanged=True, restored=[]

- pass — suite passes unmutated — passed=58 failed=0 rc=0
- FAIL — mutant M1 caught (backend/app/api/routes/items.py) — NOT caught: rc=0 passed=58 failed=0
- FAIL — mutant M2 caught (backend/app/api/routes/items.py) — NOT caught: rc=0 passed=58 failed=0

**reference patch**: pass=True, 28.0 s, git status unchanged=True, restored=[]

- pass — suite passes unmutated — passed=59 failed=0 rc=0
- pass — mutant M1 caught (backend/app/api/routes/items.py) — caught: rc=1 passed=58 failed=1
- pass — mutant M2 caught (backend/app/api/routes/items.py) — caught: rc=1 passed=58 failed=1

### s1-fa-07

**pristine upstream**: pass=False, 24.6 s, git status unchanged=True, restored=[]

- pass — suite passes unmutated — passed=58 failed=0 rc=0
- FAIL — mutant M1 caught (backend/app/api/deps.py) — NOT caught: rc=0 passed=58 failed=0
- FAIL — mutant M2 caught (backend/app/api/deps.py) — NOT caught: rc=0 passed=58 failed=0
- FAIL — mutant M3 caught (backend/app/api/deps.py) — NOT caught: rc=0 passed=58 failed=0

**reference patch**: pass=True, 30.4 s, git status unchanged=True, restored=[]

- pass — suite passes unmutated — passed=62 failed=0 rc=0
- pass — mutant M1 caught (backend/app/api/deps.py) — caught: rc=1 passed=61 failed=1
- pass — mutant M2 caught (backend/app/api/deps.py) — caught: rc=1 passed=61 failed=1
- pass — mutant M3 caught (backend/app/api/deps.py) — caught: rc=1 passed=61 failed=1

### s1-fa-08

**pristine upstream**: pass=False, 6.6 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=1
- FAIL — hidden tests test_s1_fa08.py all pass — passed=2 failed=1 skipped=0 expected=3
- pass — hidden::test_description_null_200 — passed
- FAIL — hidden::test_title_null_422_and_unchanged — failed
- pass — hidden::test_title_x_200 — passed

**reference patch**: pass=True, 7.4 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa08.py all pass — passed=3 failed=0 skipped=0 expected=3
- pass — hidden::test_description_null_200 — passed
- pass — hidden::test_title_null_422_and_unchanged — passed
- pass — hidden::test_title_x_200 — passed

### s1-fa-09

**pristine upstream**: pass=False, 6.3 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=1
- FAIL — hidden tests test_s1_fa09.py all pass — passed=0 failed=4 skipped=0 expected=4
- FAIL — hidden::test_login_upper_superuser_200 — failed
- FAIL — hidden::test_patch_me_case_variant_409 — failed
- FAIL — hidden::test_signup_case_variant_400 — failed
- FAIL — hidden::test_superuser_create_case_variant_400 — failed

**reference patch**: pass=True, 6.9 s, git status unchanged=True, restored=[]

- pass — existing tests (non-hidden) all pass, >= 58 — passed=58 failed=0 skipped=0 rc=0
- pass — hidden tests test_s1_fa09.py all pass — passed=4 failed=0 skipped=0 expected=4
- pass — hidden::test_login_upper_superuser_200 — passed
- pass — hidden::test_patch_me_case_variant_409 — passed
- pass — hidden::test_signup_case_variant_400 — passed
- pass — hidden::test_superuser_create_case_variant_400 — passed

### s1-fa-10

**pristine upstream**: pass=False, 0.2 s, git status unchanged=True, restored=[]

- FAIL — all 20 Settings names occur in a '|' line of backend/README.md — names=20 (from b1125d883948:config.py); missing=['API_V1_STR', 'SECRET_KEY', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'FRONTEND_HOST', 'FASTAPI_ENV', 'PROJECT_NAME', 'SEN
- FAIL — rows of the 5 required settings contain 'required' — without 'required': ['SECRET_KEY', 'PROJECT_NAME', 'DATABASE_URL', 'FIRST_SUPERUSER', 'FIRST_SUPERUSER_PASSWORD']
- FAIL — changed files vs base == [backend/README.md] — changed=[]

**reference patch**: pass=True, 0.1 s, git status unchanged=True, restored=[]

- pass — all 20 Settings names occur in a '|' line of backend/README.md — names=20 (from b1125d883948:config.py); missing=[]
- pass — rows of the 5 required settings contain 'required' — without 'required': []
- pass — changed files vs base == [backend/README.md] — changed=['backend/README.md']

### s1-nx-01

**pristine upstream**: pass=False, 9.8 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/users/101 /users/102 /users/104) — rc=0
- FAIL — /users/102 links: Previous->/users/101, Next->/users/103, Back to list->/users — missing=[('/users/101', 'Previous'), ('/users/103', 'Next'), ('/users', 'Back to list')]
- pass — /users/101 has no link text 'Previous'
- pass — /users/104 has no link text 'Next'
- pass — no page_errors — {'/users/101': [], '/users/102': [], '/users/104': []}
- null — visual screens/users/101 — Alice detail; Next -> Bob; Back to list; no Previous (users-101.png)
- null — visual screens/users/102 — Bob detail; Previous -> Alice, Next -> Caroline; Back to list (users-102.png)
- null — visual screens/users/104 — Dave detail; Previous -> Caroline; no Next (users-104.png)

**reference patch**: pass=True, 9.9 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/users/101 /users/102 /users/104) — rc=0
- pass — /users/102 links: Previous->/users/101, Next->/users/103, Back to list->/users — missing=[]
- pass — /users/101 has no link text 'Previous'
- pass — /users/104 has no link text 'Next'
- pass — no page_errors — {'/users/101': [], '/users/102': [], '/users/104': []}
- null — visual screens/users/101 — Alice detail; Next -> Bob; Back to list; no Previous (users-101.png)
- null — visual screens/users/102 — Bob detail; Previous -> Alice, Next -> Caroline; Back to list (users-102.png)
- null — visual screens/users/104 — Dave detail; Previous -> Caroline; no Next (users-104.png)

### s1-nx-02

**pristine upstream**: pass=False, 9.5 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/api/users/101 /api/users/999 /api/users/abc /api/users) — rc=0
- FAIL — /api/users/101: 200 and JSON == {"id":101,"name":"Alice"} — status=404 text='404\nThis page could not be found.'
- FAIL — /api/users/999: 404 and JSON body — status=404 text='404\nThis page could not be found.'
- FAIL — /api/users/abc: 400 and JSON body — status=404 text='404\nThis page could not be found.'
- pass — /api/users unchanged (200, same JSON as baseline) — status=200 text='[{"id":101,"name":"Alice"},{"id":102,"name":"Bob"},{"id":103,"name":"Caroline"},{"id":104,"name":"Dave"}]'

**reference patch**: pass=True, 9.6 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/api/users/101 /api/users/999 /api/users/abc /api/users) — rc=0
- pass — /api/users/101: 200 and JSON == {"id":101,"name":"Alice"} — status=200 text='{"id":101,"name":"Alice"}'
- pass — /api/users/999: 404 and JSON body — status=404 text='{"statusCode":404,"message":"No user with id 999"}'
- pass — /api/users/abc: 400 and JSON body — status=400 text='{"statusCode":400,"message":"id must be a number"}'
- pass — /api/users unchanged (200, same JSON as baseline) — status=200 text='[{"id":101,"name":"Alice"},{"id":102,"name":"Bob"},{"id":103,"name":"Caroline"},{"id":104,"name":"Dave"}]'

### s1-nx-03

**pristine upstream**: pass=False, 14.3 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/does-not-exist /users/999) — rc=0
- pass — /does-not-exist: status 404 — status=404
- FAIL — /does-not-exist: text has 페이지를 찾을 수 없습니다 / Users List / Footer — missing=['페이지를 찾을 수 없습니다', 'Users List', 'Footer']
- FAIL — /does-not-exist: a link with href '/'
- FAIL — /does-not-exist: not 'This page could not be found'
- pass — /users/999: status 404 — status=404
- FAIL — /users/999: text has 페이지를 찾을 수 없습니다 / Users List / Footer — missing=['페이지를 찾을 수 없습니다', 'Users List', 'Footer']
- FAIL — /users/999: a link with href '/'
- FAIL — /users/999: not 'This page could not be found'
- null — visual screens/does-not-exist — site nav, 페이지를 찾을 수 없습니다, link home, footer (does-not-exist.png)
- null — visual screens/users/999 — same custom 404 (users-999.png)

**reference patch**: pass=True, 18.9 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/does-not-exist /users/999) — rc=0
- pass — /does-not-exist: status 404 — status=404
- pass — /does-not-exist: text has 페이지를 찾을 수 없습니다 / Users List / Footer — missing=[]
- pass — /does-not-exist: a link with href '/'
- pass — /does-not-exist: not 'This page could not be found'
- pass — /users/999: status 404 — status=404
- pass — /users/999: text has 페이지를 찾을 수 없습니다 / Users List / Footer — missing=[]
- pass — /users/999: a link with href '/'
- pass — /users/999: not 'This page could not be found'
- null — visual screens/does-not-exist — site nav, 페이지를 찾을 수 없습니다, link home, footer (does-not-exist.png)
- null — visual screens/users/999 — same custom 404 (users-999.png)

### s1-nx-04

**pristine upstream**: pass=False, 11.6 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/about) — rc=0
- pass — screenshot.py screens-375 (/about) — rc=0
- FAIL — /about text contains Alice, Bob, Caroline, Dave, 101..104 — missing=['Alice', 'Bob', 'Caroline', 'Dave', '101', '102', '103', '104']
- FAIL — /about links include /users/101../users/104 — missing=['/users/101', '/users/102', '/users/103', '/users/104']
- null — visual screens/about — 4 cards in a grid at 1280px, each with ID and link (about.png)
- null — visual screens-375/about — 375x800: one card per row (about.png)

**reference patch**: pass=True, 11.9 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/about) — rc=0
- pass — screenshot.py screens-375 (/about) — rc=0
- pass — /about text contains Alice, Bob, Caroline, Dave, 101..104 — missing=[]
- pass — /about links include /users/101../users/104 — missing=[]
- null — visual screens/about — 4 cards in a grid at 1280px, each with ID and link (about.png)
- null — visual screens-375/about — 375x800: one card per row (about.png)

### s1-nx-05

**pristine upstream**: pass=False, 9.1 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /about /users) — rc=0
- FAIL — /: exactly one aria-current=page link, href / — aria-current hrefs=[]
- pass — /: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- FAIL — /about: exactly one aria-current=page link, href /about — aria-current hrefs=[]
- pass — /about: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /about: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- FAIL — /users: exactly one aria-current=page link, href /users — aria-current hrefs=[]
- pass — /users: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /users: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- null — diff review: nav links defined in one array — judged by reading the diff
- null — visual screens/ — nav as before; Home current (index.png)
- null — visual screens/about — About current (about.png)
- null — visual screens/users — Users List current (users.png)

**reference patch**: pass=True, 9.2 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /about /users) — rc=0
- pass — /: exactly one aria-current=page link, href / — aria-current hrefs=['/']
- pass — /: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- pass — /about: exactly one aria-current=page link, href /about — aria-current hrefs=['/about']
- pass — /about: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /about: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- pass — /users: exactly one aria-current=page link, href /users — aria-current hrefs=['/users']
- pass — /users: nav text line identical to baseline — 'Home \| About \| Users List \| Users API' vs 'Home \| About \| Users List \| Users API'
- pass — /users: nav links in baseline order — [('/', 'Home'), ('/about', 'About'), ('/users', 'Users List'), ('/api/users', 'Users API')]
- null — diff review: nav links defined in one array — judged by reading the diff
- null — visual screens/ — nav as before; Home current (index.png)
- null — visual screens/about — About current (about.png)
- null — visual screens/users — Users List current (users.png)

### s1-nx-06

**pristine upstream**: pass=False, 12.1 s, git status unchanged=True, restored=[]

- FAIL — grep -rl sampleUserData (*.ts, *.tsx) only utils/sample-data.ts and lib/users.ts — files=['pages/api/users/index.ts', 'pages/users/[id].tsx', 'pages/users/index.tsx', 'utils/sample-data.ts']
- FAIL — lib/users.ts exports getAllUsers and getUserById — lib/users.ts missing
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /users /users/101 /users/104 /api/users) — rc=0
- pass — / text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users/101 text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users/104 text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /api/users text+links unchanged vs baseline — status 200 (baseline 200)

**reference patch**: pass=True, 14.8 s, git status unchanged=True, restored=[]

- pass — grep -rl sampleUserData (*.ts, *.tsx) only utils/sample-data.ts and lib/users.ts — files=['lib/users.ts', 'utils/sample-data.ts']
- pass — lib/users.ts exports getAllUsers and getUserById — missing=[]
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /users /users/101 /users/104 /api/users) — rc=0
- pass — / text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users/101 text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /users/104 text+links unchanged vs baseline — status 200 (baseline 200)
- pass — /api/users text+links unchanged vs baseline — status 200 (baseline 200)

### s1-nx-07

**pristine upstream**: pass=False, 2.7 s, git status unchanged=True, restored=[]

- FAIL — npm test passes unmutated — rc=1 script='' npm error Missing script: "test" npm error npm error To see a list of scripts, run: npm error npm run npm error A complete log of this run can be
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- null — mutant M1 caught (components/ListDetail.tsx) — skipped: suite fails unmutated
- null — mutant M2 caught (components/Layout.tsx) — skipped: suite fails unmutated

**reference patch**: pass=True, 14.8 s, git status unchanged=True, restored=[]

- pass — npm test passes unmutated — rc=0 script='vitest run'
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — mutant M1 caught (components/ListDetail.tsx) — caught: rc=1 script='vitest run' ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯ Test Files 1 failed (1) Tests 1 failed \| 1 passed (2) Start at 17:02:43 Duration 834ms (transfor
- pass — mutant M2 caught (components/Layout.tsx) — caught: rc=1 script='vitest run' ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯ Test Files 1 failed (1) Tests 1 failed \| 1 passed (2) Start at 17:02:44 Duration 770ms (transfor

### s1-nx-08

**pristine upstream**: pass=False, 3.1 s, git status unchanged=True, restored=[]

- FAIL — npm test passes unmutated — rc=1 script='' npm error Missing script: "test" npm error npm error To see a list of scripts, run: npm error npm run npm error A complete log of this run can be
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- null — mutant M1 caught (pages/users/[id].tsx) — skipped: suite fails unmutated
- null — mutant M2 caught (pages/users/[id].tsx) — skipped: suite fails unmutated

**reference patch**: pass=True, 10.3 s, git status unchanged=True, restored=[]

- pass — npm test passes unmutated — rc=0 script='vitest run'
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — mutant M1 caught (pages/users/[id].tsx) — caught: rc=1 script='vitest run' ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯ Test Files 1 failed (1) Tests 1 failed \| 2 passed (3) Start at 17:03:02 Duration 449ms (transfor
- pass — mutant M2 caught (pages/users/[id].tsx) — caught: rc=1 script='vitest run' ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯ Test Files 1 failed (1) Tests 1 failed \| 2 passed (3) Start at 17:03:03 Duration 475ms (transfor

### s1-nx-09

**pristine upstream**: pass=False, 12.2 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /about /users /users/101 /does-not-exist) — rc=0
- FAIL — /: html_lang == 'en' — html_lang=None
- FAIL — /about: html_lang == 'en' — html_lang=None
- FAIL — /users: html_lang == 'en' — html_lang=None
- FAIL — /users/101: html_lang == 'en' — html_lang=None
- FAIL — /does-not-exist: html_lang == 'en' — html_lang=None
- pass — / text unchanged vs baseline — status 200 (baseline 200)
- pass — /about text unchanged vs baseline — status 200 (baseline 200)
- pass — /users text unchanged vs baseline — status 200 (baseline 200)
- pass — /users/101 text unchanged vs baseline — status 200 (baseline 200)

**reference patch**: pass=True, 13.5 s, git status unchanged=True, restored=[]

- pass — npm run type-check — rc=0
- pass — npx next build — rc=0
- pass — screenshot.py screens (/ /about /users /users/101 /does-not-exist) — rc=0
- pass — /: html_lang == 'en' — html_lang='en'
- pass — /about: html_lang == 'en' — html_lang='en'
- pass — /users: html_lang == 'en' — html_lang='en'
- pass — /users/101: html_lang == 'en' — html_lang='en'
- pass — /does-not-exist: html_lang == 'en' — html_lang='en'
- pass — / text unchanged vs baseline — status 200 (baseline 200)
- pass — /about text unchanged vs baseline — status 200 (baseline 200)
- pass — /users text unchanged vs baseline — status 200 (baseline 200)
- pass — /users/101 text unchanged vs baseline — status 200 (baseline 200)

### s1-nx-10

**pristine upstream**: pass=False, 3.6 s, git status unchanged=True, restored=[]

- FAIL — JSDoc on every component, Props member (or @param) and exported type — components/Layout.tsx: component Layout has no JSDoc block; components/Layout.tsx: prop children has no JSDoc and no matching @param; components/Layout.tsx: pro
- pass — comment-only change in components/ interfaces/ (non-comment +/- lines == 0) — count=0
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0

**reference patch**: pass=True, 3.1 s, git status unchanged=True, restored=[]

- pass — JSDoc on every component, Props member (or @param) and exported type — all documented
- pass — comment-only change in components/ interfaces/ (non-comment +/- lines == 0) — count=0
- pass — npm run type-check — rc=0
- pass — npx next build — rc=0


